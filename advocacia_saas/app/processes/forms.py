"""
Formulários para o módulo de Processos.
"""

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, Optional, Regexp


class ProcessForm(FlaskForm):
    """Formulário para criar/editar processo judicial."""

    # Identificação
    process_number = StringField(
        "Número do Processo",
        validators=[
            Optional(),
            Length(max=30, message="Máximo 30 caracteres"),
            Regexp(
                r"^[\d\.\-\/]*$",
                message="Use apenas números, pontos, hífens e barras",
            ),
        ],
        render_kw={"placeholder": "0000000-00.0000.0.00.0000"},
    )

    title = StringField(
        "Título/Descrição",
        validators=[
            DataRequired(message="Título é obrigatório"),
            Length(min=5, max=300, message="Título deve ter entre 5 e 300 caracteres"),
        ],
        render_kw={"placeholder": "Ex: Ação de Cobrança - João vs Empresa XYZ"},
    )

    # Partes
    plaintiff = StringField(
        "Autor/Requerente",
        validators=[Optional(), Length(max=300)],
        render_kw={"placeholder": "Nome do autor ou requerente"},
    )

    defendant = StringField(
        "Réu/Requerido",
        validators=[Optional(), Length(max=300)],
        render_kw={"placeholder": "Nome do réu ou requerido"},
    )

    # Cliente vinculado
    client_id = SelectField(
        "Cliente Vinculado",
        coerce=lambda x: int(x) if x else None,
        validators=[Optional()],
    )

    # Informações do tribunal
    court = SelectField(
        "Justiça/Tribunal",
        choices=[
            ("", "Selecione..."),
            ("Justiça Estadual", "Justiça Estadual"),
            ("Justiça Federal", "Justiça Federal"),
            ("Justiça do Trabalho", "Justiça do Trabalho"),
            ("Justiça Militar", "Justiça Militar"),
            ("Justiça Eleitoral", "Justiça Eleitoral"),
            ("STF", "Supremo Tribunal Federal"),
            ("STJ", "Superior Tribunal de Justiça"),
            ("TST", "Tribunal Superior do Trabalho"),
            ("Juizado Especial Cível", "Juizado Especial Cível"),
            ("Juizado Especial Criminal", "Juizado Especial Criminal"),
            ("Outro", "Outro"),
        ],
        validators=[Optional()],
    )

    court_instance = SelectField(
        "Instância",
        choices=[
            ("", "Selecione..."),
            ("1ª Instância", "1ª Instância"),
            ("2ª Instância", "2ª Instância"),
            ("Instância Superior", "Instância Superior"),
            ("Instância Especial", "Instância Especial"),
        ],
        validators=[Optional()],
    )

    jurisdiction = StringField(
        "Vara/Órgão Julgador",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: 1ª Vara Cível, 2ª Turma Recursal"},
    )

    district = StringField(
        "Comarca/Foro",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: São Paulo, Rio de Janeiro"},
    )

    judge = StringField(
        "Juiz/Relator",
        validators=[Optional(), Length(max=200)],
        render_kw={"placeholder": "Nome do juiz ou relator"},
    )

    # Status e datas
    status = SelectField(
        "Status",
        choices=[
            ("pending_distribution", "Aguardando Distribuição"),
            ("distributed", "Distribuído"),
            ("ongoing", "Em Andamento"),
            ("suspended", "Suspenso"),
            ("archived", "Arquivado"),
            ("finished", "Finalizado"),
        ],
        validators=[DataRequired()],
    )

    distribution_date = DateField(
        "Data de Distribuição",
        validators=[Optional()],
        render_kw={"type": "date"},
    )

    # Controle de prazos
    next_deadline = DateField(
        "Próximo Prazo",
        validators=[Optional()],
        render_kw={"type": "date"},
    )

    deadline_description = StringField(
        "Descrição do Prazo",
        validators=[Optional(), Length(max=300)],
        render_kw={"placeholder": "Ex: Prazo para contestação"},
    )

    priority = SelectField(
        "Prioridade",
        choices=[
            ("low", "🟢 Baixa"),
            ("normal", "🔵 Normal"),
            ("high", "🟡 Alta"),
            ("urgent", "🔴 Urgente"),
        ],
        validators=[DataRequired()],
    )

    submit = SubmitField("Salvar Processo")

    def __init__(self, *args, **kwargs):
        """Inicializa o formulário com lista de clientes."""
        super().__init__(*args, **kwargs)
        # Lista de clientes será preenchida na view


class ProcessFilterForm(FlaskForm):
    """Formulário para filtrar processos na listagem."""

    search = StringField(
        "Buscar",
        validators=[Optional()],
        render_kw={"placeholder": "Número, título, partes..."},
    )

    status = SelectField(
        "Status",
        choices=[
            ("", "Todos os Status"),
            ("pending_distribution", "Aguardando Distribuição"),
            ("distributed", "Distribuído"),
            ("ongoing", "Em Andamento"),
            ("suspended", "Suspenso"),
            ("archived", "Arquivado"),
            ("finished", "Finalizado"),
        ],
        validators=[Optional()],
    )

    priority = SelectField(
        "Prioridade",
        choices=[
            ("", "Todas as Prioridades"),
            ("low", "Baixa"),
            ("normal", "Normal"),
            ("high", "Alta"),
            ("urgent", "Urgente"),
        ],
        validators=[Optional()],
    )

    client_id = SelectField(
        "Cliente",
        coerce=lambda x: int(x) if x else None,
        validators=[Optional()],
    )

    submit = SubmitField("Filtrar")
