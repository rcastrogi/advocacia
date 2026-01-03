from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    FieldList,
    FormField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Email, Length, Optional
from wtforms.widgets import CheckboxInput, ListWidget


class MultiCheckboxField(SelectField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class DependentForm(FlaskForm):
    full_name = StringField("Nome completo", validators=[DataRequired(), Length(min=2, max=200)])
    relationship = SelectField(
        "Parentesco",
        choices=[
            ("filho", "Filho(a)"),
            ("conjuge", "Cônjuge"),
            ("pai", "Pai"),
            ("mae", "Mãe"),
            ("irmao", "Irmão(ã)"),
            ("outro", "Outro"),
        ],
        validators=[DataRequired()],
    )
    birth_date = DateField("Data de nascimento", validators=[Optional()])
    cpf = StringField("CPF", validators=[Optional(), Length(max=14)])


class ClientForm(FlaskForm):
    # Personal Information
    full_name = StringField("Nome completo *", validators=[DataRequired(), Length(min=2, max=200)])
    rg = StringField("RG", validators=[Optional(), Length(max=20)])
    cpf_cnpj = StringField("CPF/CNPJ *", validators=[DataRequired(), Length(max=20)])
    civil_status = SelectField(
        "Estado civil",
        choices=[
            ("", "Selecione..."),
            ("solteiro", "Solteiro(a)"),
            ("casado", "Casado(a)"),
            ("divorciado", "Divorciado(a)"),
            ("viuvo", "Viúvo(a)"),
            ("uniao_estavel", "União estável"),
        ],
        validators=[Optional()],
    )
    birth_date = DateField("Data de nascimento", validators=[Optional()])
    profession = StringField("Profissão", validators=[Optional(), Length(max=100)])
    nationality = StringField("Nacionalidade", validators=[Optional(), Length(max=50)])
    birth_place = StringField("Naturalidade", validators=[Optional(), Length(max=100)])
    mother_name = StringField("Nome da mãe", validators=[Optional(), Length(max=200)])
    father_name = StringField("Nome do pai", validators=[Optional(), Length(max=200)])

    # Address
    address_type = SelectField(
        "Tipo de endereço",
        choices=[("residencial", "Residencial"), ("comercial", "Comercial")],
        default="residencial",
    )
    cep = StringField("CEP", validators=[Optional(), Length(max=10)])
    street = StringField("Logradouro", validators=[Optional(), Length(max=200)])
    number = StringField("Número", validators=[Optional(), Length(max=20)])
    complement = StringField("Complemento", validators=[Optional(), Length(max=200)])
    neighborhood = StringField("Bairro", validators=[Optional(), Length(max=100)])
    city = StringField("Cidade", validators=[Optional(), Length(max=100)])
    uf = SelectField("UF", choices=[("", "Selecione...")], validators=[Optional()])

    # Contacts
    landline_phone = StringField("Telefone fixo", validators=[Optional(), Length(max=20)])
    email = StringField("E-mail *", validators=[DataRequired(), Email(), Length(max=120)])
    mobile_phone = StringField("Celular *", validators=[DataRequired(), Length(max=20)])

    # Personal Conditions
    lgbt_declared = BooleanField("Autodeclarado LGBT?")
    has_disability = BooleanField("Pessoa com deficiência?")
    disability_types = MultiCheckboxField(
        "Tipo de deficiência",
        choices=[
            ("auditiva", "Auditiva"),
            ("fisica", "Física"),
            ("intelectual", "Intelectual"),
            ("mental", "Mental"),
            ("visual", "Visual"),
        ],
        validators=[Optional()],
    )

    # Pregnancy/Maternity
    is_pregnant_postpartum = BooleanField("Gestante/Puérpera/Lactante?")
    delivery_date = DateField("Data do parto", validators=[Optional()])

    # Dependents
    dependents = FieldList(FormField(DependentForm), min_entries=0)

    submit = SubmitField("Salvar cliente")

    def validate(self, extra_validators=None):
        initial_validation = super(ClientForm, self).validate(extra_validators)
        if not initial_validation:
            return False

        # Custom validation for disability types
        if self.has_disability.data and not self.disability_types.data:
            self.disability_types.errors.append("Selecione pelo menos um tipo de deficiência.")
            return False

        # Custom validation for delivery date
        if self.is_pregnant_postpartum.data and not self.delivery_date.data:
            self.delivery_date.errors.append("Data do parto é obrigatória.")
            return False

        return True
