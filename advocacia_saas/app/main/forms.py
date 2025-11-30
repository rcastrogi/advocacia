from flask_wtf import FlaskForm
from wtforms import (
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional


class TestimonialForm(FlaskForm):
    """Formulário para envio de depoimentos pelos usuários."""
    
    content = TextAreaField(
        "Seu depoimento",
        validators=[
            DataRequired(message="Por favor, escreva seu depoimento."),
            Length(min=50, max=1000, message="O depoimento deve ter entre 50 e 1000 caracteres.")
        ],
        render_kw={"placeholder": "Conte como o Petitio tem ajudado no seu dia a dia...", "rows": 5}
    )
    
    rating = SelectField(
        "Avaliação",
        choices=[
            ("5", "⭐⭐⭐⭐⭐ Excelente"),
            ("4", "⭐⭐⭐⭐ Muito bom"),
            ("3", "⭐⭐⭐ Bom"),
            ("2", "⭐⭐ Regular"),
            ("1", "⭐ Ruim"),
        ],
        default="5",
        validators=[DataRequired()]
    )
    
    display_name = StringField(
        "Nome para exibição",
        validators=[
            DataRequired(message="Informe como deseja ser identificado."),
            Length(min=3, max=100)
        ],
        render_kw={"placeholder": "Ex: Dr. João Silva"}
    )
    
    display_role = StringField(
        "Cargo/Função (opcional)",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: Advogado Tributarista, Sócio do Escritório ABC"}
    )
    
    display_location = StringField(
        "Cidade/Estado (opcional)",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: São Paulo, SP"}
    )


class TestimonialModerationForm(FlaskForm):
    """Formulário para moderação de depoimentos (admin)."""
    
    status = SelectField(
        "Status",
        choices=[
            ("pending", "Pendente"),
            ("approved", "Aprovado"),
            ("rejected", "Rejeitado"),
        ],
        validators=[DataRequired()]
    )
    
    rejection_reason = TextAreaField(
        "Motivo da rejeição (se aplicável)",
        validators=[Optional(), Length(max=500)],
        render_kw={"placeholder": "Explique o motivo da rejeição...", "rows": 3}
    )
    
    is_featured = SelectField(
        "Destaque",
        choices=[
            ("0", "Não destacar"),
            ("1", "Destacar na página inicial"),
        ],
        default="0"
    )
