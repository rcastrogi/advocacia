from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional


class PetitionTypeForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField(
        "Descrição", validators=[Optional()], render_kw={"rows": 3}
    )
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
    is_billable = BooleanField("Conta como petição paga", default=True)
    base_price = DecimalField(
        "Valor por petição (R$)",
        places=2,
        rounding=None,
        default=Decimal("0.00"),
        validators=[Optional()],
    )
    active = BooleanField("Ativo", default=True)
    submit = SubmitField("Salvar tipo")


class BillingPlanForm(FlaskForm):
    name = StringField("Nome do plano", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField(
        "Descrição", validators=[Optional()], render_kw={"rows": 3}
    )
    plan_type = SelectField(
        "Tipo de cobrança",
        choices=[("per_usage", "Por petição"), ("flat_monthly", "Mensal ilimitado")],
        validators=[DataRequired()],
    )
    monthly_fee = DecimalField(
        "Mensalidade (R$)",
        places=2,
        default=Decimal("0.00"),
        validators=[Optional()],
    )
    usage_rate = DecimalField(
        "Valor por petição (R$)",
        places=2,
        default=Decimal("0.00"),
        validators=[Optional()],
    )
    active = BooleanField("Ativo", default=True)
    submit = SubmitField("Salvar plano")


class AssignPlanForm(FlaskForm):
    user_id = SelectField("Usuário", coerce=int, validators=[DataRequired()])
    plan_id = SelectField("Plano", coerce=int, validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[
            ("active", "Ativo"),
            ("trial", "Em teste"),
            ("delinquent", "Inadimplente"),
        ],
        default="active",
    )
    submit = SubmitField("Aplicar plano")
