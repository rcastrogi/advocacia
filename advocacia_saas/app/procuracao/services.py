"""
Serviços para geração de procurações
"""

import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.models import Client

logger = logging.getLogger(__name__)


@dataclass
class ProcuracaoData:
    """Dados para geração de procuração."""

    client_id: int
    client_name: str
    client_cpf: str
    client_nationality: str
    client_civil_status: str
    client_profession: str
    client_address: str
    lawyer_name: str
    lawyer_oab: str
    lawyer_oab_uf: str
    powers: List[str]
    purpose: str


class ProcuracaoService:
    """Serviço para geração de procurações em PDF."""

    # Poderes padrão disponíveis
    AVAILABLE_POWERS = [
        {"id": "geral", "name": "Poderes Gerais", "text": "poderes gerais para o foro"},
        {
            "id": "especial",
            "name": "Poderes Especiais",
            "text": "poderes especiais para transigir, desistir, renunciar, receber e dar quitação",
        },
        {
            "id": "criminal",
            "name": "Poderes Criminais",
            "text": "poderes para representação criminal, inclusive para oferecer queixa-crime",
        },
        {
            "id": "trabalhista",
            "name": "Poderes Trabalhistas",
            "text": "poderes específicos para reclamatória trabalhista",
        },
        {
            "id": "familia",
            "name": "Poderes de Família",
            "text": "poderes para ações de família, divórcio, guarda e alimentos",
        },
    ]

    @staticmethod
    def get_available_powers() -> List[Dict[str, str]]:
        """Retorna lista de poderes disponíveis."""
        return ProcuracaoService.AVAILABLE_POWERS

    @staticmethod
    def build_client_address(client: Client) -> str:
        """Constrói endereço completo do cliente."""
        parts = []

        if client.street:
            parts.append(client.street)
        if client.number:
            parts.append(f"nº {client.number}")
        if client.complement:
            parts.append(client.complement)
        if client.neighborhood:
            parts.append(client.neighborhood)
        if client.city:
            parts.append(client.city)
        if client.uf:
            parts.append(f"- {client.uf}")
        if client.cep:
            parts.append(f"CEP: {client.cep}")

        return ", ".join(parts) if parts else "Endereço não informado"

    @staticmethod
    def generate_pdf(data: ProcuracaoData) -> io.BytesIO:
        """Gera PDF da procuração."""
        buffer = io.BytesIO()

        # Configurar documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        # Estilos
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "Title",
            parent=styles["Title"],
            fontSize=16,
            spaceAfter=30,
            alignment=1,  # Center
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=12,
            leading=18,
            alignment=4,  # Justify
            spaceAfter=12,
        )

        signature_style = ParagraphStyle(
            "Signature",
            parent=styles["Normal"],
            fontSize=12,
            alignment=1,  # Center
            spaceAfter=6,
        )

        # Construir conteúdo
        elements = []

        # Título
        elements.append(Paragraph("PROCURAÇÃO AD JUDICIA", title_style))
        elements.append(Spacer(1, 20))

        # Texto de qualificação do outorgante
        outorgante_text = (
            f"<b>OUTORGANTE:</b> {data.client_name}, {data.client_nationality}, "
            f"{data.client_civil_status}, {data.client_profession}, "
            f"inscrito(a) no CPF sob nº {data.client_cpf}, "
            f"residente e domiciliado(a) em {data.client_address}."
        )
        elements.append(Paragraph(outorgante_text, body_style))
        elements.append(Spacer(1, 12))

        # Texto de qualificação do outorgado
        outorgado_text = (
            f"<b>OUTORGADO:</b> {data.lawyer_name}, advogado(a) inscrito(a) na "
            f"OAB/{data.lawyer_oab_uf} sob nº {data.lawyer_oab}."
        )
        elements.append(Paragraph(outorgado_text, body_style))
        elements.append(Spacer(1, 12))

        # Poderes concedidos
        powers_text = ", ".join(data.powers)
        poderes_text = (
            f"<b>PODERES:</b> O outorgante nomeia e constitui seu bastante procurador "
            f"o advogado acima qualificado, a quem confere amplos poderes para o foro "
            f"em geral, com as seguintes prerrogativas: {powers_text}."
        )
        elements.append(Paragraph(poderes_text, body_style))
        elements.append(Spacer(1, 12))

        # Finalidade
        if data.purpose:
            finalidade_text = f"<b>FINALIDADE:</b> {data.purpose}"
            elements.append(Paragraph(finalidade_text, body_style))
            elements.append(Spacer(1, 12))

        # Cláusula de ratificação
        ratificacao_text = (
            "Fica desde já ratificado tudo quanto for praticado pelo outorgado "
            "no exercício do presente mandato."
        )
        elements.append(Paragraph(ratificacao_text, body_style))
        elements.append(Spacer(1, 30))

        # Data e local
        now = datetime.now(timezone.utc)
        data_text = now.strftime("___________, %d de %B de %Y.")
        elements.append(Paragraph(data_text, signature_style))
        elements.append(Spacer(1, 50))

        # Assinatura
        elements.append(Paragraph("_" * 50, signature_style))
        elements.append(Paragraph(data.client_name, signature_style))
        elements.append(Paragraph(f"CPF: {data.client_cpf}", signature_style))

        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)

        return buffer

    @staticmethod
    def generate_from_client(
        client: Client,
        lawyer_name: str,
        lawyer_oab: str,
        lawyer_oab_uf: str,
        powers: List[str],
        purpose: str = "",
    ) -> io.BytesIO:
        """Gera procuração a partir de um cliente."""
        # Construir dados
        data = ProcuracaoData(
            client_id=client.id,
            client_name=client.full_name or "Nome não informado",
            client_cpf=client.cpf_cnpj or "CPF não informado",
            client_nationality=client.nationality or "brasileiro(a)",
            client_civil_status=client.civil_status or "solteiro(a)",
            client_profession=client.profession or "profissão não informada",
            client_address=ProcuracaoService.build_client_address(client),
            lawyer_name=lawyer_name,
            lawyer_oab=lawyer_oab,
            lawyer_oab_uf=lawyer_oab_uf,
            powers=powers,
            purpose=purpose,
        )

        return ProcuracaoService.generate_pdf(data)
