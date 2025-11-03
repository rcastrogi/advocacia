from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.models import User


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
    submit = SubmitField("Atualizar perfil")

    def __init__(self, original_email, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError("Email já cadastrado. Use outro email.")
