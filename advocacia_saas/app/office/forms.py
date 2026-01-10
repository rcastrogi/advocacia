"""Forms para o módulo de Escritório"""
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    HiddenField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp


class CreateOfficeForm(FlaskForm):
    """Formulário para criar um novo escritório"""
    
    name = StringField(
        "Nome do Escritório",
        validators=[DataRequired(message="Nome é obrigatório"), Length(min=3, max=200)],
        render_kw={"placeholder": "Ex: Silva & Associados Advogados"},
    )
    
    cnpj = StringField(
        "CNPJ",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "00.000.000/0000-00", "data-mask": "cnpj"},
    )
    
    oab_number = StringField(
        "OAB do Escritório",
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "OAB/SP 12345 (se for sociedade)"},
    )
    
    phone = StringField(
        "Telefone",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "(11) 99999-9999", "data-mask": "phone"},
    )
    
    email = EmailField(
        "E-mail do Escritório",
        validators=[Optional(), Email(message="E-mail inválido")],
        render_kw={"placeholder": "contato@escritorio.com.br"},
    )
    
    website = StringField(
        "Website",
        validators=[Optional(), Length(max=200)],
        render_kw={"placeholder": "https://www.escritorio.com.br"},
    )
    
    submit = SubmitField("Criar Escritório")


class OfficeSettingsForm(FlaskForm):
    """Formulário para configurações do escritório"""
    
    name = StringField(
        "Nome do Escritório",
        validators=[DataRequired(message="Nome é obrigatório"), Length(min=3, max=200)],
    )
    
    cnpj = StringField(
        "CNPJ",
        validators=[Optional(), Length(max=20)],
        render_kw={"data-mask": "cnpj"},
    )
    
    oab_number = StringField(
        "OAB do Escritório",
        validators=[Optional(), Length(max=50)],
    )
    
    phone = StringField(
        "Telefone",
        validators=[Optional(), Length(max=20)],
        render_kw={"data-mask": "phone"},
    )
    
    email = EmailField(
        "E-mail do Escritório",
        validators=[Optional(), Email(message="E-mail inválido")],
    )
    
    website = StringField(
        "Website",
        validators=[Optional(), Length(max=200)],
    )
    
    # Endereço
    cep = StringField(
        "CEP",
        validators=[Optional(), Length(max=10)],
        render_kw={"data-mask": "cep"},
    )
    
    street = StringField(
        "Logradouro",
        validators=[Optional(), Length(max=200)],
    )
    
    number = StringField(
        "Número",
        validators=[Optional(), Length(max=20)],
    )
    
    complement = StringField(
        "Complemento",
        validators=[Optional(), Length(max=200)],
    )
    
    neighborhood = StringField(
        "Bairro",
        validators=[Optional(), Length(max=100)],
    )
    
    city = StringField(
        "Cidade",
        validators=[Optional(), Length(max=100)],
    )
    
    uf = SelectField(
        "Estado",
        choices=[
            ("", "Selecione..."),
            ("AC", "Acre"),
            ("AL", "Alagoas"),
            ("AP", "Amapá"),
            ("AM", "Amazonas"),
            ("BA", "Bahia"),
            ("CE", "Ceará"),
            ("DF", "Distrito Federal"),
            ("ES", "Espírito Santo"),
            ("GO", "Goiás"),
            ("MA", "Maranhão"),
            ("MT", "Mato Grosso"),
            ("MS", "Mato Grosso do Sul"),
            ("MG", "Minas Gerais"),
            ("PA", "Pará"),
            ("PB", "Paraíba"),
            ("PR", "Paraná"),
            ("PE", "Pernambuco"),
            ("PI", "Piauí"),
            ("RJ", "Rio de Janeiro"),
            ("RN", "Rio Grande do Norte"),
            ("RS", "Rio Grande do Sul"),
            ("RO", "Rondônia"),
            ("RR", "Roraima"),
            ("SC", "Santa Catarina"),
            ("SP", "São Paulo"),
            ("SE", "Sergipe"),
            ("TO", "Tocantins"),
        ],
        validators=[Optional()],
    )
    
    # Branding
    primary_color = StringField(
        "Cor Primária",
        validators=[Optional(), Regexp(r"^#[0-9A-Fa-f]{6}$", message="Cor inválida")],
        render_kw={"type": "color"},
    )
    
    submit = SubmitField("Salvar Alterações")


class InviteMemberForm(FlaskForm):
    """Formulário para convidar membro para o escritório"""
    
    email = EmailField(
        "E-mail",
        validators=[
            DataRequired(message="E-mail é obrigatório"),
            Email(message="E-mail inválido"),
        ],
        render_kw={"placeholder": "advogado@exemplo.com"},
    )
    
    role = SelectField(
        "Função",
        choices=[
            ("lawyer", "Advogado(a)"),
            ("secretary", "Secretário(a)"),
            ("intern", "Estagiário(a)"),
            ("admin", "Administrador(a)"),
        ],
        validators=[DataRequired(message="Função é obrigatória")],
    )
    
    submit = SubmitField("Enviar Convite")


class ChangeMemberRoleForm(FlaskForm):
    """Formulário para alterar função de membro"""
    
    member_id = HiddenField(validators=[DataRequired()])
    
    role = SelectField(
        "Nova Função",
        choices=[
            ("lawyer", "Advogado(a)"),
            ("secretary", "Secretário(a)"),
            ("intern", "Estagiário(a)"),
            ("admin", "Administrador(a)"),
        ],
        validators=[DataRequired(message="Função é obrigatória")],
    )
    
    submit = SubmitField("Alterar Função")


class TransferOwnershipForm(FlaskForm):
    """Formulário para transferir propriedade do escritório"""
    
    new_owner_id = SelectField(
        "Novo Proprietário",
        choices=[],
        coerce=int,
        validators=[DataRequired(message="Selecione o novo proprietário")],
    )
    
    confirm = BooleanField(
        "Confirmo que desejo transferir a propriedade do escritório",
        validators=[DataRequired(message="Você deve confirmar a transferência")],
    )
    
    submit = SubmitField("Transferir Propriedade")
