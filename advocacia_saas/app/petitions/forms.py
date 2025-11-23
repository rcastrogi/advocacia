from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    MultipleFileField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional


class CivilPetitionForm(FlaskForm):
    template_id = SelectField(
        "Modelo",
        coerce=int,
        validators=[DataRequired()],
    )
    forum = StringField("Fórum", validators=[DataRequired(), Length(max=255)])
    vara = StringField("Vara", validators=[DataRequired(), Length(max=255)])
    process_number = StringField(
        "Número do Processo", validators=[Optional(), Length(max=100)]
    )
    author_name = StringField(
        "Nome do Autor", validators=[DataRequired(), Length(max=255)]
    )
    author_qualification = TextAreaField(
        "Qualificação do Autor",
        validators=[DataRequired()],
        render_kw={"rows": 3},
    )
    defendant_name = StringField(
        "Nome do Réu", validators=[DataRequired(), Length(max=255)]
    )
    defendant_qualification = TextAreaField(
        "Qualificação do Réu",
        validators=[DataRequired()],
        render_kw={"rows": 3},
    )
    facts = TextAreaField("Fatos", validators=[DataRequired()], render_kw={"rows": 5})
    fundamentos = TextAreaField(
        "Fundamentação Jurídica", validators=[DataRequired()], render_kw={"rows": 5}
    )
    pedidos = TextAreaField(
        "Pedidos", validators=[DataRequired()], render_kw={"rows": 4}
    )
    valor_causa = DecimalField("Valor da Causa (R$)", validators=[Optional()], places=2)
    cidade = StringField("Cidade", validators=[DataRequired(), Length(max=120)])
    data_assinatura = DateField("Data", default=date.today, validators=[DataRequired()])
    advogado_nome = StringField(
        "Nome do Advogado", validators=[DataRequired(), Length(max=255)]
    )
    advogado_oab = StringField("OAB", validators=[DataRequired(), Length(max=50)])
    submit = SubmitField("Gerar PDF")


class PetitionTemplateForm(FlaskForm):
    name = StringField("Nome do modelo", validators=[DataRequired(), Length(max=180)])
    category = SelectField(
        "Categoria",
        choices=[
            ("civel", "Cível"),
            ("trabalhista", "Trabalhista"),
            ("familia", "Família"),
            ("criminal", "Criminal"),
            ("tributario", "Tributário"),
            ("outros", "Outros"),
        ],
        default="civel",
    )
    petition_type_id = SelectField(
        "Tipo de petição",
        coerce=int,
        validators=[DataRequired()],
    )
    description = TextAreaField(
        "Descrição",
        validators=[Optional()],
        render_kw={"rows": 3},
    )
    content = TextAreaField(
        "Conteúdo (variáveis Jinja)",
        validators=[DataRequired(), Length(min=50)],
        render_kw={"rows": 18, "class": "font-monospace"},
    )
    is_active = BooleanField("Ativo", default=True)
    submit = SubmitField("Salvar modelo")


class FamilyPetitionForm(FlaskForm):
    template_id = SelectField(
        "Modelo",
        coerce=int,
        validators=[DataRequired()],
    )
    forum = StringField("Fórum", validators=[DataRequired(), Length(max=255)])
    vara = StringField("Vara", validators=[DataRequired(), Length(max=255)])
    process_number = StringField(
        "Número do Processo", validators=[Optional(), Length(max=100)]
    )
    action_type = StringField(
        "Tipo da ação", validators=[DataRequired(), Length(max=180)]
    )
    marriage_date = DateField("Data do casamento/união", validators=[Optional()])
    marriage_city = StringField(
        "Cidade do casamento", validators=[Optional(), Length(max=180)]
    )
    marriage_regime = StringField(
        "Regime de bens", validators=[Optional(), Length(max=120)]
    )
    has_prenup = BooleanField("Existe pacto antenupcial?", default=False)
    prenup_details = TextAreaField(
        "Detalhes do pacto", validators=[Optional()], render_kw={"rows": 2}
    )
    spouse_one_name = StringField(
        "Parte 1", validators=[DataRequired(), Length(max=255)]
    )
    spouse_one_qualification = TextAreaField(
        "Qualificação da Parte 1", validators=[DataRequired()], render_kw={"rows": 3}
    )
    spouse_two_name = StringField(
        "Parte 2", validators=[DataRequired(), Length(max=255)]
    )
    spouse_two_qualification = TextAreaField(
        "Qualificação da Parte 2", validators=[DataRequired()], render_kw={"rows": 3}
    )
    children_info = TextAreaField(
        "Filhos e necessidades", validators=[Optional()], render_kw={"rows": 3}
    )
    custody_plan = TextAreaField(
        "Proposta de guarda/convivência", validators=[Optional()], render_kw={"rows": 3}
    )
    alimony_plan = TextAreaField(
        "Proposta de alimentos", validators=[Optional()], render_kw={"rows": 3}
    )
    property_description = TextAreaField(
        "Relação de bens", validators=[Optional()], render_kw={"rows": 4}
    )
    facts = TextAreaField("Fatos", validators=[DataRequired()], render_kw={"rows": 5})
    fundamentos = TextAreaField(
        "Fundamentação jurídica", validators=[DataRequired()], render_kw={"rows": 5}
    )
    pedidos = TextAreaField(
        "Pedidos", validators=[DataRequired()], render_kw={"rows": 4}
    )
    cidade = StringField("Cidade", validators=[DataRequired(), Length(max=120)])
    data_assinatura = DateField("Data", default=date.today, validators=[DataRequired()])
    advogado_nome = StringField(
        "Nome do advogado", validators=[DataRequired(), Length(max=255)]
    )
    advogado_oab = StringField("OAB", validators=[DataRequired(), Length(max=50)])
    documents = MultipleFileField(
        "Documentos anexos (opcional)",
        validators=[
            Optional(),
            FileAllowed(
                ["pdf", "doc", "docx", "png", "jpg", "jpeg"],
                "Formatos permitidos: pdf, doc, docx, png, jpg.",
            ),
        ],
        render_kw={"multiple": True},
    )
    submit = SubmitField("Gerar PDF")
