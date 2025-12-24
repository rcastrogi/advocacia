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
from app.utils.validators import validate_strong_password


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
    specialties = MultiCheckboxField(
        "Áreas de atuação",
        choices=[
            ("civil", "Direito Civil"),
            ("familia", "Direito de Família"),
            ("trabalhista", "Direito do Trabalho"),
            ("criminal", "Direito Criminal"),
            ("previdenciario", "Direito Previdenciário"),
            ("tributario", "Direito Tributário"),
            ("consumidor", "Direito do Consumidor"),
            ("administrativo", "Direito Administrativo"),
            ("ambiental", "Direito Ambiental"),
            ("empresarial", "Direito Empresarial"),
        ],
        coerce=str,
    )
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=8)])
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

    def validate_password(self, password):
        """Valida força da senha"""
        is_valid, error_msg = validate_strong_password(password.data)
        if not is_valid:
            raise ValidationError(error_msg)


class ProfileForm(FlaskForm):
    full_name = StringField(
        "Nome completo", validators=[DataRequired(), Length(min=2, max=100)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    oab_number = StringField("Número da OAB")
    phone = StringField("Telefone")
    specialties = MultiCheckboxField(
        "Áreas de atuação",
        choices=[
            ("civil", "Direito Civil"),
            ("familia", "Direito de Família"),
            ("trabalhista", "Direito do Trabalho"),
            ("criminal", "Direito Criminal"),
            ("previdenciario", "Direito Previdenciário"),
            ("tributario", "Direito Tributário"),
            ("consumidor", "Direito do Consumidor"),
            ("administrativo", "Direito Administrativo"),
            ("ambiental", "Direito Ambiental"),
            ("empresarial", "Direito Empresarial"),
        ],
        coerce=str,
    )
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
        render_kw={
            "placeholder": "Mínimo 8 caracteres, maiúsculas, números e símbolos"
        },
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

    def validate_new_password(self, new_password):
        """Valida força da nova senha"""
        is_valid, error_msg = validate_strong_password(new_password.data)
        if not is_valid:
            raise ValidationError(error_msg)
