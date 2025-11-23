from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    widgets,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.models import User
from app.quick_actions import build_quick_action_choices


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired()])
    remember_me = BooleanField("Lembrar de mim")
    submit = SubmitField("Entrar")


class RegistrationForm(FlaskForm):
    username = StringField(
        "Nome de usuário", validators=[DataRequired(), Length(min=4, max=20)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    full_name = StringField(
        "Nome completo", validators=[DataRequired(), Length(min=2, max=100)]
    )
    oab_number = StringField("Número da OAB")
    phone = StringField("Telefone")
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        "Confirmar senha", validators=[DataRequired(), EqualTo("password")]
    )
    user_type = SelectField(
        "Tipo de usuário",
        choices=[("advogado", "Advogado"), ("escritorio", "Escritório")],
        default="advogado",
    )
    submit = SubmitField("Cadastrar")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Nome de usuário já existe. Escolha outro.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Email já cadastrado. Use outro email.")


class ProfileForm(FlaskForm):
    full_name = StringField(
        "Nome completo", validators=[DataRequired(), Length(min=2, max=100)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    oab_number = StringField("Número da OAB")
    phone = StringField("Telefone")
    quick_actions = MultiCheckboxField(
        "Ações rápidas no dashboard",
        coerce=str,
        validators=[Length(min=1, message="Selecione pelo menos uma ação rápida.")],
    )
    submit = SubmitField("Atualizar perfil")

    def __init__(self, original_email, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email
        self.quick_actions.choices = build_quick_action_choices()

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError("Email já cadastrado. Use outro email.")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Senha atual",
        validators=[DataRequired()],
        render_kw={"placeholder": "Digite sua senha atual"},
    )
    new_password = PasswordField(
        "Nova senha",
        validators=[
            DataRequired(),
            Length(min=8, message="A senha deve ter no mínimo 8 caracteres"),
        ],
        render_kw={"placeholder": "Mínimo 8 caracteres"},
    )
    confirm_password = PasswordField(
        "Confirmar nova senha",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="As senhas devem ser iguais"),
        ],
        render_kw={"placeholder": "Digite a nova senha novamente"},
    )
    submit = SubmitField("Alterar senha")
