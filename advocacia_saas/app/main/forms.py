from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    SelectField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, Length, Optional


class TestimonialForm(FlaskForm):
    """Formulário para envio de depoimentos pelos usuários."""

    content = TextAreaField(
        "Seu depoimento",
        validators=[
            DataRequired(message="Por favor, escreva seu depoimento."),
            Length(
                min=50,
                max=1000,
                message="O depoimento deve ter entre 50 e 1000 caracteres.",
            ),
        ],
        render_kw={
            "placeholder": "Conte como o Petitio tem ajudado no seu dia a dia...",
            "rows": 5,
        },
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
        validators=[DataRequired()],
    )

    display_name = StringField(
        "Nome para exibição",
        validators=[
            DataRequired(message="Informe como deseja ser identificado."),
            Length(min=3, max=100),
        ],
        render_kw={"placeholder": "Ex: Dr. João Silva"},
    )

    display_role = StringField(
        "Cargo/Função (opcional)",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: Advogado Tributarista, Sócio do Escritório ABC"},
    )

    display_location = StringField(
        "Cidade/Estado (opcional)",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: São Paulo, SP"},
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
        validators=[DataRequired()],
    )

    rejection_reason = TextAreaField(
        "Motivo da rejeição (se aplicável)",
        validators=[Optional(), Length(max=500)],
        render_kw={"placeholder": "Explique o motivo da rejeição...", "rows": 3},
    )

    is_featured = SelectField(
        "Destaque",
        choices=[
            ("0", "Não destacar"),
            ("1", "Destacar na página inicial"),
        ],
        default="0",
    )


class NotificationPreferencesForm(FlaskForm):
    """Formulário para configuração de preferências de notificação."""

    # === Canais de Notificação ===
    email_enabled = BooleanField("Email", default=True)
    push_enabled = BooleanField("Push", default=True)
    in_app_enabled = BooleanField("No Sistema", default=True)

    # === Tipos por Canal - Prazos ===
    deadline_email = BooleanField("Prazos - Email", default=True)
    deadline_push = BooleanField("Prazos - Push", default=True)
    deadline_in_app = BooleanField("Prazos - Sistema", default=True)

    # === Tipos por Canal - Movimentações ===
    movement_email = BooleanField("Movimentações - Email", default=True)
    movement_push = BooleanField("Movimentações - Push", default=False)
    movement_in_app = BooleanField("Movimentações - Sistema", default=True)

    # === Tipos por Canal - Pagamentos ===
    payment_email = BooleanField("Pagamentos - Email", default=True)
    payment_push = BooleanField("Pagamentos - Push", default=True)
    payment_in_app = BooleanField("Pagamentos - Sistema", default=True)

    # === Tipos por Canal - Petições/IA ===
    petition_email = BooleanField("Petições - Email", default=True)
    petition_push = BooleanField("Petições - Push", default=False)
    petition_in_app = BooleanField("Petições - Sistema", default=True)

    # === Tipos por Canal - Sistema ===
    system_email = BooleanField("Sistema - Email", default=True)
    system_push = BooleanField("Sistema - Push", default=False)
    system_in_app = BooleanField("Sistema - Sistema", default=True)

    # === Horário de Silêncio ===
    quiet_hours_enabled = BooleanField("Ativar horário de silêncio", default=False)
    quiet_hours_start = TimeField("Início do silêncio", validators=[Optional()])
    quiet_hours_end = TimeField("Fim do silêncio", validators=[Optional()])
    quiet_hours_weekends = BooleanField("Silenciar finais de semana", default=True)

    # === Digest/Resumo ===
    digest_enabled = BooleanField("Ativar resumo consolidado", default=False)
    digest_frequency = SelectField(
        "Frequência do resumo",
        choices=[
            ("daily", "Diário"),
            ("weekly", "Semanal"),
        ],
        default="daily",
    )
    digest_time = TimeField("Horário de envio", validators=[Optional()])

    # === Prioridade Mínima ===
    min_priority_email = SelectField(
        "Prioridade mínima - Email",
        choices=[
            ("1", "Baixa (todas)"),
            ("2", "Média"),
            ("3", "Alta"),
            ("4", "Urgente"),
        ],
        default="1",
    )
    min_priority_push = SelectField(
        "Prioridade mínima - Push",
        choices=[
            ("1", "Baixa (todas)"),
            ("2", "Média"),
            ("3", "Alta"),
            ("4", "Urgente"),
        ],
        default="2",
    )
