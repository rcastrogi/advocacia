from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    ValidationError,
)
from wtforms.validators import DataRequired, Length, Optional
import json


def validate_json(form, field):
    """Valida se o campo contém JSON válido"""
    try:
        json.loads(field.data)
    except (json.JSONDecodeError, TypeError):
        raise ValidationError('JSON inválido. Use o formato: {"1m": 0.0, "3m": 5.0, ...}')


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
    supported_periods = SelectField(
        "Períodos suportados",
        choices=[
            ("1m", "1 mês"),
            ("3m", "3 meses"),
            ("6m", "6 meses"),
            ("1y", "1 ano"),
            ("2y", "2 anos"),
            ("3y", "3 anos"),
        ],
        default=["1m", "3m", "6m", "1y", "2y", "3y"],
    )
    discount_percentage = DecimalField(
        "Desconto (%)",
        places=1,
        default=Decimal("0.0"),
        validators=[Optional()],
    )
    period_discounts = TextAreaField(
        "Descontos por período (JSON)",
        validators=[Optional(), validate_json],
        render_kw={"rows": 4, "placeholder": '{"1m": 0.0, "3m": 5.0, "6m": 7.0, "1y": 9.0, "2y": 13.0, "3y": 20.0}'},
        default='{"1m": 0.0, "3m": 5.0, "6m": 7.0, "1y": 9.0, "2y": 13.0, "3y": 20.0}'
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
