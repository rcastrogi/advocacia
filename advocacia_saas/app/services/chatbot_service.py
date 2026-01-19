"""
Serviço de ChatBot FAQ para o Portal do Cliente
Responde automaticamente perguntas comuns sem uso de IA paga
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple
from flask import url_for

from app import db
from app.models import (
    Client, Process, Deadline, Document, CalendarEvent, User, Message
)


class ChatBotService:
    """Bot FAQ para responder perguntas dos clientes automaticamente"""
    
    # Padrões de intenção (regex) mapeados para handlers
    INTENT_PATTERNS = {
        'greeting': [
            r'\b(oi|olá|ola|bom dia|boa tarde|boa noite|hey|hello|hi)\b',
        ],
        'next_deadline': [
            r'\b(próximo|proximo|quando|qual)\b.*\b(prazo|vencimento|data)\b',
            r'\bprazo\b.*\b(próximo|proximo)\b',
            r'\bmeu prazo\b',
        ],
        'all_deadlines': [
            r'\b(todos|todas|lista|listar|quais)\b.*\bprazos?\b',
            r'\bprazos\b.*\b(pendentes|abertos)\b',
        ],
        'process_status': [
            r'\b(status|situação|situacao|andamento|como está|como esta)\b.*\b(processo|caso)\b',
            r'\bmeu processo\b',
            r'\bprocesso\b.*\b(como|qual|está|esta)\b',
        ],
        'documents': [
            r'\b(documentos?|arquivos?)\b',
            r'\bquantos documentos\b',
            r'\bmeus documentos\b',
        ],
        'talk_to_lawyer': [
            r'\b(falar|conversar|agendar|marcar|reunião|reuniao)\b.*\b(advogado|doutor|doutora|dr\.?|dra\.?)\b',
            r'\badvogado\b.*\b(falar|conversar|disponível|disponivel)\b',
            r'\bpreciso falar\b',
            r'\bquero conversar\b',
            r'\bagendar.*conversa\b',
            r'\bmarcar.*horário\b',
        ],
        'lawyer_info': [
            r'\b(quem é|quem e|qual|nome)\b.*\b(meu advogado|advogado)\b',
            r'\bdados.*advogado\b',
            r'\bcontato.*advogado\b',
        ],
        'help': [
            r'\bajuda\b',
            r'\bo que (você|voce) (pode|consegue|faz)\b',
            r'\bcomandos?\b',
            r'\bopções\b',
        ],
        'thanks': [
            r'\b(obrigado|obrigada|valeu|thanks|vlw|grato|grata)\b',
        ],
    }
    
    def __init__(self, client: Client):
        """Inicializa o bot com o cliente"""
        self.client = client
        self.lawyer = User.query.get(client.lawyer_id) if client.lawyer_id else None
    
    def process_message(self, message: str) -> Tuple[str, Optional[Dict]]:
        """
        Processa a mensagem do cliente e retorna resposta do bot
        
        Returns:
            Tuple[str, Optional[Dict]]: (resposta_texto, dados_extras)
        """
        message_lower = message.lower().strip()
        
        # Detectar intenção
        intent = self._detect_intent(message_lower)
        
        # Executar handler apropriado
        handlers = {
            'greeting': self._handle_greeting,
            'next_deadline': self._handle_next_deadline,
            'all_deadlines': self._handle_all_deadlines,
            'process_status': self._handle_process_status,
            'documents': self._handle_documents,
            'talk_to_lawyer': self._handle_talk_to_lawyer,
            'lawyer_info': self._handle_lawyer_info,
            'help': self._handle_help,
            'thanks': self._handle_thanks,
        }
        
        handler = handlers.get(intent, self._handle_unknown)
        return handler()
    
    def _detect_intent(self, message: str) -> str:
        """Detecta a intenção da mensagem baseado em padrões regex"""
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return intent
        return 'unknown'
    
    def _handle_greeting(self) -> Tuple[str, None]:
        """Saudação inicial"""
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Bom dia"
        elif hour < 18:
            greeting = "Boa tarde"
        else:
            greeting = "Boa noite"
        
        response = f"""
{greeting}, {self.client.name.split()[0]}! 👋

Sou o assistente virtual do escritório. Posso ajudar com:

📅 **Prazos** - "Qual meu próximo prazo?"
📋 **Processos** - "Status do meu processo"
📄 **Documentos** - "Meus documentos"
👨‍💼 **Advogado** - "Quero falar com meu advogado"
❓ **Ajuda** - "O que você pode fazer?"

Como posso ajudar?
        """.strip()
        
        return response, None
    
    def _handle_next_deadline(self) -> Tuple[str, Optional[Dict]]:
        """Retorna o próximo prazo do cliente"""
        now = datetime.now(timezone.utc)
        
        # Buscar próximo prazo
        next_deadline = Deadline.query.filter(
            Deadline.client_id == self.client.id,
            Deadline.deadline_date >= now,
            Deadline.status != 'completed'
        ).order_by(Deadline.deadline_date.asc()).first()
        
        if not next_deadline:
            return "✅ Você não tem prazos pendentes no momento. Que ótima notícia!", None
        
        days_until = (next_deadline.deadline_date.date() - now.date()).days
        
        if days_until == 0:
            urgency = "⚠️ **HOJE!**"
        elif days_until == 1:
            urgency = "⚠️ **Amanhã!**"
        elif days_until <= 3:
            urgency = f"🔴 Em **{days_until} dias**"
        elif days_until <= 7:
            urgency = f"🟡 Em **{days_until} dias**"
        else:
            urgency = f"🟢 Em **{days_until} dias**"
        
        response = f"""
📅 **Seu próximo prazo:**

📌 **{next_deadline.title}**
📆 Data: **{next_deadline.deadline_date.strftime('%d/%m/%Y às %H:%M')}**
⏰ {urgency}
{f'📝 {next_deadline.description}' if next_deadline.description else ''}

Quer ver todos os prazos? Pergunte "Quais são meus prazos?"
        """.strip()
        
        return response, {'deadline_id': next_deadline.id}
    
    def _handle_all_deadlines(self) -> Tuple[str, Optional[Dict]]:
        """Lista todos os prazos pendentes"""
        now = datetime.now(timezone.utc)
        
        deadlines = Deadline.query.filter(
            Deadline.client_id == self.client.id,
            Deadline.deadline_date >= now,
            Deadline.status != 'completed'
        ).order_by(Deadline.deadline_date.asc()).limit(5).all()
        
        if not deadlines:
            return "✅ Você não tem prazos pendentes no momento!", None
        
        lines = ["📅 **Seus próximos prazos:**\n"]
        
        for i, d in enumerate(deadlines, 1):
            days_until = (d.deadline_date.date() - now.date()).days
            if days_until <= 3:
                icon = "🔴"
            elif days_until <= 7:
                icon = "🟡"
            else:
                icon = "🟢"
            
            lines.append(f"{icon} **{i}.** {d.title}")
            lines.append(f"   📆 {d.deadline_date.strftime('%d/%m/%Y')} ({days_until} dias)")
        
        if len(deadlines) == 5:
            lines.append("\n_Mostrando os 5 mais próximos._")
        
        return "\n".join(lines), {'deadline_count': len(deadlines)}
    
    def _handle_process_status(self) -> Tuple[str, Optional[Dict]]:
        """Retorna status dos processos do cliente"""
        processes = Process.query.filter_by(client_id=self.client.id).all()
        
        if not processes:
            return "📋 Você ainda não tem processos cadastrados no sistema.", None
        
        lines = [f"📋 **Seus processos ({len(processes)}):**\n"]
        
        status_icons = {
            'em_andamento': '🔵',
            'aguardando': '🟡',
            'arquivado': '⚫',
            'concluido': '✅',
            'suspenso': '🔴',
        }
        
        for i, p in enumerate(processes, 1):
            icon = status_icons.get(p.status, '📌')
            status_display = p.status.replace('_', ' ').title() if p.status else 'N/A'
            lines.append(f"{icon} **{i}. {p.number or 'Sem número'}**")
            lines.append(f"   📁 {p.type or 'Tipo não informado'}")
            lines.append(f"   📊 Status: {status_display}")
            if p.court:
                lines.append(f"   🏛️ {p.court}")
            lines.append("")
        
        return "\n".join(lines), {'process_count': len(processes)}
    
    def _handle_documents(self) -> Tuple[str, Optional[Dict]]:
        """Retorna informações sobre documentos"""
        doc_count = Document.query.filter_by(client_id=self.client.id).count()
        
        recent_docs = Document.query.filter_by(
            client_id=self.client.id
        ).order_by(Document.created_at.desc()).limit(3).all()
        
        if doc_count == 0:
            return "📄 Você ainda não tem documentos no portal. Use a opção 'Enviar Documento' para adicionar.", None
        
        lines = [f"📄 **Seus documentos:**\n"]
        lines.append(f"📊 Total: **{doc_count} documento(s)**\n")
        
        if recent_docs:
            lines.append("📥 **Últimos adicionados:**")
            for doc in recent_docs:
                date_str = doc.created_at.strftime('%d/%m/%Y') if doc.created_at else 'N/A'
                lines.append(f"   • {doc.filename or doc.title or 'Documento'} ({date_str})")
        
        lines.append("\n💡 Acesse 'Documentos' no menu para ver todos.")
        
        return "\n".join(lines), {'doc_count': doc_count}
    
    def _handle_talk_to_lawyer(self) -> Tuple[str, Optional[Dict]]:
        """Sugere horários disponíveis para falar com o advogado"""
        if not self.lawyer:
            return "❌ Não foi possível identificar seu advogado. Entre em contato com o escritório.", None
        
        # Buscar próximos horários disponíveis (dias úteis, horário comercial)
        available_slots = self._get_available_slots()
        
        lawyer_name = self.lawyer.name or "seu advogado"
        
        if not available_slots:
            response = f"""
👨‍💼 **Agendar conversa com {lawyer_name}**

No momento não encontrei horários disponíveis na agenda.

📞 **Alternativas:**
• Deixe sua mensagem aqui que {lawyer_name} responderá assim que possível
• Entre em contato pelo telefone do escritório

Qual sua dúvida? Posso tentar ajudar!
            """.strip()
            return response, None
        
        lines = [f"👨‍💼 **Agendar conversa com {lawyer_name}**\n"]
        lines.append("Encontrei os seguintes horários disponíveis:\n")
        
        for i, slot in enumerate(available_slots[:3], 1):
            day_name = self._get_day_name(slot)
            lines.append(f"📅 **Opção {i}:** {day_name}, {slot.strftime('%d/%m/%Y às %H:%M')}")
        
        lines.append("\n💬 **Para agendar:**")
        lines.append("Responda com o número da opção desejada (1, 2 ou 3)")
        lines.append("\nOu digite sua mensagem que enviarei para o advogado.")
        
        return "\n".join(lines), {
            'available_slots': [s.isoformat() for s in available_slots[:3]],
            'action': 'schedule_meeting'
        }
    
    def _get_available_slots(self) -> List[datetime]:
        """Busca horários disponíveis na agenda do advogado"""
        if not self.lawyer:
            return []
        
        now = datetime.now(timezone.utc)
        slots = []
        
        # Buscar eventos existentes do advogado nos próximos 14 dias
        end_date = now + timedelta(days=14)
        
        existing_events = CalendarEvent.query.filter(
            CalendarEvent.user_id == self.lawyer.id,
            CalendarEvent.start_datetime >= now,
            CalendarEvent.start_datetime <= end_date,
            CalendarEvent.status != 'cancelled'
        ).all()
        
        # Criar set de horários ocupados
        busy_slots = set()
        for event in existing_events:
            # Marcar hora de início como ocupada
            busy_slots.add(event.start_datetime.replace(minute=0, second=0, microsecond=0))
        
        # Gerar slots disponíveis (dias úteis, 9h-17h)
        current = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if current < now:
            current += timedelta(days=1)
        
        days_checked = 0
        while len(slots) < 6 and days_checked < 14:
            # Pular fins de semana
            if current.weekday() < 5:  # Segunda a Sexta
                for hour in [9, 10, 11, 14, 15, 16]:
                    slot = current.replace(hour=hour)
                    if slot > now and slot not in busy_slots:
                        slots.append(slot)
                        if len(slots) >= 6:
                            break
            
            current += timedelta(days=1)
            days_checked += 1
        
        return slots
    
    def _get_day_name(self, dt: datetime) -> str:
        """Retorna nome do dia em português"""
        days = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        today = datetime.now(timezone.utc).date()
        
        if dt.date() == today:
            return "Hoje"
        elif dt.date() == today + timedelta(days=1):
            return "Amanhã"
        else:
            return days[dt.weekday()]
    
    def _handle_lawyer_info(self) -> Tuple[str, None]:
        """Retorna informações do advogado"""
        if not self.lawyer:
            return "❌ Não foi possível identificar seu advogado. Entre em contato com o escritório.", None
        
        response = f"""
👨‍💼 **Seu Advogado:**

📛 **Nome:** {self.lawyer.name}
📧 **Email:** {self.lawyer.email}
{f'📱 **OAB:** {self.lawyer.oab_number}' if hasattr(self.lawyer, 'oab_number') and self.lawyer.oab_number else ''}

💬 Suas mensagens neste chat são enviadas diretamente para {self.lawyer.name.split()[0]}.
        """.strip()
        
        return response, None
    
    def _handle_help(self) -> Tuple[str, None]:
        """Lista comandos disponíveis"""
        response = """
❓ **Central de Ajuda - O que posso fazer:**

📅 **Prazos:**
• "Qual meu próximo prazo?"
• "Quais são meus prazos?"

📋 **Processos:**
• "Status do meu processo"
• "Como está meu caso?"

📄 **Documentos:**
• "Meus documentos"
• "Quantos documentos tenho?"

👨‍💼 **Advogado:**
• "Quero falar com meu advogado"
• "Agendar reunião"
• "Quem é meu advogado?"

💡 **Dica:** Digite sua pergunta naturalmente que tentarei entender!
        """.strip()
        
        return response, None
    
    def _handle_thanks(self) -> Tuple[str, None]:
        """Responde agradecimentos"""
        return "😊 Por nada! Estou aqui para ajudar. Precisa de mais alguma coisa?", None
    
    def _handle_unknown(self) -> Tuple[str, None]:
        """Resposta padrão para mensagens não reconhecidas"""
        lawyer_name = self.lawyer.name.split()[0] if self.lawyer else 'seu advogado'
        response = f"""
🤔 Não entendi sua pergunta, mas posso ajudar com:

• **Prazos** - "Qual meu próximo prazo?"
• **Processos** - "Status do meu processo"
• **Documentos** - "Meus documentos"
• **Advogado** - "Quero falar com meu advogado"

📨 **Sua mensagem foi enviada para {lawyer_name}**, que responderá assim que possível.
        """.strip()
        
        return response, None
    
    def create_bot_message(self, content: str) -> Message:
        """Cria uma mensagem do bot no banco de dados"""
        # Bot envia como se fosse do advogado (sistema)
        message = Message(
            sender_id=self.lawyer.id if self.lawyer else self.client.lawyer_id,
            recipient_id=self.client.user_id,
            client_id=self.client.id,
            content=content,
            message_type="bot",  # Tipo especial para identificar mensagens do bot
            is_read=True,  # Bot messages são auto-lidas
        )
        db.session.add(message)
        return message


def process_client_message(client: Client, message_text: str) -> Tuple[str, Optional[Dict]]:
    """
    Função de conveniência para processar mensagem do cliente
    
    Args:
        client: Cliente que enviou a mensagem
        message_text: Texto da mensagem
    
    Returns:
        Tuple com resposta e dados extras
    """
    bot = ChatBotService(client)
    return bot.process_message(message_text)
