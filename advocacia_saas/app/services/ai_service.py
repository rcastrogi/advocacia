"""
Serviço de Integração com OpenAI para geração de petições jurídicas.
Suporta modelos híbridos: GPT-4o-mini (rápido/barato) e GPT-4o (premium).
"""

import os
import time
from typing import Any, Dict, Tuple

from openai import OpenAI

# Configuração de custos LEGADO (usado como fallback)
# Os valores reais são lidos do banco via AICreditConfig
CREDIT_COSTS = {
    "section": 1,  # Gerar uma seção individual
    "improve": 1,  # Melhorar texto existente
    "summarize": 1,  # Resumir texto
    "full_petition": 5,  # Petição completa (usa GPT-4o)
    "analyze": 3,  # Análise jurídica (usa GPT-4o)
    "fundamentos": 3,  # Fundamentação jurídica (usa GPT-4o)
    "analyze_document": 4,  # Análise de documento PDF (usa GPT-4o)
    "analyze_risk": 3,  # Análise de riscos e chances (usa GPT-4o)
}

# Operações que usam modelo premium (GPT-4o) por padrão (LEGADO)
PREMIUM_OPERATIONS = {"full_petition", "analyze", "fundamentos", "analyze_document", "analyze_risk"}


def get_credit_cost(operation_key: str) -> int:
    """Obtém custo de créditos do banco ou fallback para constantes"""
    try:
        from app.models import AICreditConfig
        return AICreditConfig.get_cost(operation_key)
    except Exception:
        return CREDIT_COSTS.get(operation_key, 1)


def is_premium_operation(operation_key: str) -> bool:
    """Verifica se operação usa modelo premium via banco ou fallback"""
    try:
        from app.models import AICreditConfig
        return AICreditConfig.is_premium_operation(operation_key)
    except Exception:
        return operation_key in PREMIUM_OPERATIONS


# Modelos disponíveis
MODELS = {
    "fast": "gpt-4o-mini",  # Rápido e barato - tarefas simples
    "premium": "gpt-4o",  # Melhor qualidade - tarefas complexas
}

# Prompts do sistema para diferentes contextos
SYSTEM_PROMPTS = {
    "default": """Você é um advogado brasileiro altamente qualificado e experiente, especializado na redação de petições jurídicas.

REGRAS IMPORTANTES:
1. Use linguagem jurídica formal e técnica apropriada
2. Cite artigos de lei quando relevante (CF, CPC, CC, CLT, etc.)
3. Seja preciso e objetivo
4. Mantenha a estrutura profissional de documentos jurídicos
5. Use formatação adequada com parágrafos bem estruturados
6. Responda APENAS com o conteúdo solicitado, sem explicações adicionais
7. NÃO inclua saudações ou despedidas
8. Use português brasileiro formal""",
    "section_fatos": """Você é um advogado brasileiro especialista em redação de petições.
Sua tarefa é redigir a seção "DOS FATOS" de uma petição.

INSTRUÇÕES:
1. Narre os fatos de forma cronológica e clara
2. Seja objetivo e preciso
3. Inclua datas, locais e circunstâncias relevantes
4. Use linguagem jurídica formal
5. Estruture em parágrafos bem organizados
6. Não inclua argumentos jurídicos (isso vai na fundamentação)
7. Responda APENAS com o texto dos fatos, sem títulos ou explicações""",
    "section_direito": """Você é um advogado brasileiro especialista em fundamentação jurídica.
Sua tarefa é redigir a seção "DO DIREITO" ou "DOS FUNDAMENTOS JURÍDICOS" de uma petição.

INSTRUÇÕES:
1. Fundamente juridicamente os pedidos
2. Cite artigos de lei relevantes (CF, CPC, CC, CLT, CDC, etc.)
3. Mencione jurisprudência quando apropriado
4. Use doutrina se necessário
5. Conecte os fatos ao direito aplicável
6. Estruture em tópicos se houver múltiplos fundamentos
7. Responda APENAS com a fundamentação, sem títulos ou explicações""",
    "section_pedidos": """Você é um advogado brasileiro especialista em redação de petições.
Sua tarefa é redigir a seção "DOS PEDIDOS" de uma petição.

INSTRUÇÕES:
1. Liste os pedidos de forma clara e específica
2. Use numeração para cada pedido
3. Seja preciso nos valores e condições quando aplicável
4. Inclua pedido de citação, condenação em custas e honorários
5. Use "requer" ou "pede" de forma formal
6. Responda APENAS com os pedidos, sem títulos ou explicações""",
    "improve": """Você é um revisor jurídico especializado.
Sua tarefa é melhorar o texto fornecido mantendo o sentido original.

INSTRUÇÕES:
1. Melhore a clareza e precisão do texto
2. Corrija erros gramaticais e de concordância
3. Aprimore a linguagem jurídica
4. Mantenha o sentido e intenção originais
5. Responda APENAS com o texto melhorado""",
    "full_petition": """Você é um advogado brasileiro altamente qualificado.
Sua tarefa é redigir uma petição jurídica completa e profissional.

ESTRUTURA OBRIGATÓRIA:
1. ENDEREÇAMENTO (juízo competente)
2. QUALIFICAÇÃO DAS PARTES
3. DOS FATOS
4. DO DIREITO (fundamentação jurídica com citação de leis)
5. DOS PEDIDOS (numerados)
6. VALOR DA CAUSA
7. ENCERRAMENTO

INSTRUÇÕES:
1. Use linguagem jurídica formal e técnica
2. Cite artigos de lei relevantes
3. Seja preciso e objetivo
4. Estruture de forma profissional
5. Inclua todos os elementos necessários""",
    "analyze_document": """Você é um advogado brasileiro altamente qualificado especializado em análise documental.
Sua tarefa é analisar o documento fornecido e extrair informações jurídicas relevantes.

ANÁLISE OBRIGATÓRIA:
1. TIPO DE DOCUMENTO: Identifique o tipo (contrato, procuração, notificação, etc.)
2. PARTES ENVOLVIDAS: Liste todas as partes mencionadas
3. OBJETO: Descreva o objeto principal do documento
4. CLÁUSULAS RELEVANTES: Identifique cláusulas importantes
5. DATAS E PRAZOS: Liste datas e prazos mencionados
6. VALORES: Identifique valores monetários
7. PONTOS DE ATENÇÃO: Destaque possíveis problemas ou irregularidades
8. LEGISLAÇÃO APLICÁVEL: Cite leis que se aplicam ao caso

INSTRUÇÕES:
1. Seja objetivo e preciso
2. Use linguagem jurídica formal
3. Organize as informações de forma clara
4. Destaque pontos que podem ser usados em fundamentação jurídica""",
    "fundamentos_com_documento": """Você é um advogado brasileiro especialista em fundamentação jurídica.
Sua tarefa é redigir uma fundamentação jurídica BASEADA no documento analisado.

ESTRUTURA DA FUNDAMENTAÇÃO:
1. Apresente o contexto fático extraído do documento
2. Identifique as questões jurídicas envolvidas
3. Cite a legislação aplicável (artigos específicos)
4. Apresente jurisprudência relevante quando apropriado
5. Conecte os fatos do documento ao direito aplicável
6. Conclua com a tese jurídica sustentada

INSTRUÇÕES:
1. Baseie-se EXCLUSIVAMENTE nas informações do documento
2. Cite artigos de lei de forma precisa (CF, CC, CPC, CDC, CLT, etc.)
3. Use linguagem jurídica formal e técnica
4. Estruture em parágrafos bem organizados
5. Seja persuasivo mas tecnicamente correto""",
    "analyze_risk": """Você é um advogado brasileiro sênior com vasta experiência em litígios.
Sua tarefa é analisar uma petição e fornecer uma avaliação detalhada de riscos e chances de êxito.

ESTRUTURA OBRIGATÓRIA DA ANÁLISE (use EXATAMENTE este formato JSON):
{
    "chance_exito": {
        "percentual": 0-100,
        "classificacao": "MUITO BAIXA" | "BAIXA" | "MÉDIA" | "MÉDIA-ALTA" | "ALTA" | "MUITO ALTA"
    },
    "pontos_fortes": [
        "Ponto forte 1",
        "Ponto forte 2"
    ],
    "riscos": [
        {
            "descricao": "Descrição do risco",
            "gravidade": "BAIXA" | "MÉDIA" | "ALTA",
            "mitigacao": "Como mitigar este risco"
        }
    ],
    "recomendacoes": [
        "Recomendação 1",
        "Recomendação 2"
    ],
    "jurisprudencia_relevante": [
        "Menção a jurisprudência favorável ou desfavorável"
    ],
    "observacoes": "Observações gerais sobre o caso"
}

CRITÉRIOS DE AVALIAÇÃO:
1. Consistência entre fatos narrados e pedidos formulados
2. Fundamentação jurídica adequada (leis, artigos, jurisprudência)
3. Prescrição e decadência
4. Legitimidade das partes
5. Competência do juízo
6. Documentação comprobatória mencionada
7. Viabilidade dos pedidos
8. Precedentes judiciais sobre o tema

INSTRUÇÕES:
1. Responda APENAS com o JSON, sem texto adicional
2. Seja realista e objetivo na avaliação
3. Considere a jurisprudência majoritária dos tribunais brasileiros
4. Identifique TODOS os pontos fracos que podem ser explorados pela parte adversa
5. Forneça recomendações práticas e específicas""",
}


class AIService:
    """Serviço para geração de conteúdo jurídico com IA"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def is_configured(self) -> bool:
        """Verifica se a API está configurada"""
        return self.client is not None

    def get_credit_cost(self, generation_type: str) -> int:
        """Retorna o custo em créditos para um tipo de geração (do banco)"""
        return get_credit_cost(generation_type)

    def _call_openai(
        self,
        messages: list,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Faz a chamada à API da OpenAI.

        Returns:
            Tuple[str, Dict]: (conteúdo gerado, metadados com tokens e tempo)
        """
        if not self.client:
            raise Exception("API OpenAI não configurada. Configure OPENAI_API_KEY no .env")

        start_time = time.time()

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        content = response.choices[0].message.content

        metadata = {
            "model": model,
            "tokens_input": response.usage.prompt_tokens,
            "tokens_output": response.usage.completion_tokens,
            "tokens_total": response.usage.total_tokens,
            "response_time_ms": elapsed_ms,
            "finish_reason": response.choices[0].finish_reason,
        }

        return content, metadata

    def generate_section(
        self,
        section_type: str,
        context: Dict[str, Any],
        existing_content: str = None,
        premium: bool = False,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Gera uma seção específica de uma petição.

        Args:
            section_type: Tipo da seção ('fatos', 'direito', 'pedidos', etc.)
            context: Dados do contexto (tipo petição, dados do autor, réu, etc.)
            existing_content: Conteúdo existente para referência
            premium: Se True, usa GPT-4o (melhor qualidade)

        Returns:
            Tuple[str, Dict]: (conteúdo gerado, metadados)
        """
        # Seleciona o prompt do sistema adequado
        system_prompt_key = f"section_{section_type.lower()}"
        system_prompt = SYSTEM_PROMPTS.get(system_prompt_key, SYSTEM_PROMPTS["default"])

        # Monta o prompt do usuário com o contexto
        user_prompt = self._build_section_prompt(section_type, context, existing_content)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        model = MODELS["premium"] if premium else MODELS["fast"]

        return self._call_openai(messages, model=model)

    def _build_section_prompt(
        self, section_type: str, context: Dict[str, Any], existing_content: str = None
    ) -> str:
        """Constrói o prompt do usuário para geração de seção"""

        prompt_parts = []

        # Tipo de petição
        if context.get("petition_type"):
            prompt_parts.append(f"TIPO DE PETIÇÃO: {context['petition_type']}")

        # Dados do autor
        if context.get("autor"):
            autor = context["autor"]
            autor_info = f"AUTOR: {autor.get('nome', 'Não informado')}"
            if autor.get("cpf"):
                autor_info += f", CPF: {autor['cpf']}"
            if autor.get("profissao"):
                autor_info += f", Profissão: {autor['profissao']}"
            prompt_parts.append(autor_info)

        # Dados do réu
        if context.get("reu"):
            reu = context["reu"]
            reu_info = f"RÉU: {reu.get('nome', 'Não informado')}"
            if reu.get("cpf"):
                reu_info += f", CPF: {reu['cpf']}"
            prompt_parts.append(reu_info)

        # Contexto específico da seção
        if context.get("fatos_resumo"):
            prompt_parts.append(f"RESUMO DOS FATOS: {context['fatos_resumo']}")

        if context.get("valor_causa"):
            prompt_parts.append(f"VALOR DA CAUSA: R$ {context['valor_causa']}")

        if context.get("pedidos_resumo"):
            prompt_parts.append(f"PEDIDOS PRETENDIDOS: {context['pedidos_resumo']}")

        # Instruções específicas do usuário
        if context.get("instrucoes"):
            prompt_parts.append(f"INSTRUÇÕES ESPECÍFICAS: {context['instrucoes']}")

        # Conteúdo existente para referência
        if existing_content:
            prompt_parts.append(f"CONTEÚDO ATUAL (para referência): {existing_content[:500]}...")

        # Instrução final
        prompt_parts.append(
            f"\nRedija a seção '{section_type.upper()}' com base nas informações acima."
        )

        return "\n\n".join(prompt_parts)

    def generate_full_petition(
        self,
        petition_type: str,
        context: Dict[str, Any],
        premium: bool = True,  # Petição completa sempre usa premium por padrão
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Gera uma petição completa.

        Args:
            petition_type: Tipo da petição
            context: Dados completos do contexto
            premium: Se True, usa GPT-4o

        Returns:
            Tuple[str, Dict]: (petição completa, metadados)
        """
        system_prompt = SYSTEM_PROMPTS["full_petition"]

        user_prompt = self._build_full_petition_prompt(petition_type, context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        model = MODELS["premium"] if premium else MODELS["fast"]

        return self._call_openai(messages, model=model, max_tokens=4000)

    def _build_full_petition_prompt(self, petition_type: str, context: Dict[str, Any]) -> str:
        """Constrói o prompt para petição completa"""

        prompt_parts = [f"TIPO DE PETIÇÃO: {petition_type}"]

        # Dados do autor
        if context.get("autor"):
            autor = context["autor"]
            prompt_parts.append(
                f"""
DADOS DO AUTOR:
- Nome: {autor.get("nome", "Não informado")}
- CPF: {autor.get("cpf", "Não informado")}
- RG: {autor.get("rg", "Não informado")}
- Estado Civil: {autor.get("estado_civil", "Não informado")}
- Profissão: {autor.get("profissao", "Não informado")}
- Endereço: {autor.get("endereco", "Não informado")}
- Cidade/UF: {autor.get("cidade", "")}/{autor.get("estado", "")}"""
            )

        # Dados do réu
        if context.get("reu"):
            reu = context["reu"]
            prompt_parts.append(
                f"""
DADOS DO RÉU:
- Nome: {reu.get("nome", "Não informado")}
- CPF/CNPJ: {reu.get("cpf", reu.get("cnpj", "Não informado"))}
- Endereço: {reu.get("endereco", "Não informado")}
- Cidade/UF: {reu.get("cidade", "")}/{reu.get("estado", "")}"""
            )

        # Fatos
        if context.get("fatos"):
            prompt_parts.append(f"FATOS DO CASO:\n{context['fatos']}")

        # Pedidos
        if context.get("pedidos"):
            prompt_parts.append(f"PEDIDOS:\n{context['pedidos']}")

        # Valor da causa
        if context.get("valor_causa"):
            prompt_parts.append(f"VALOR DA CAUSA: R$ {context['valor_causa']}")

        # Comarca/Foro
        if context.get("comarca"):
            prompt_parts.append(f"COMARCA: {context['comarca']}")

        # Instruções adicionais
        if context.get("instrucoes"):
            prompt_parts.append(f"INSTRUÇÕES ADICIONAIS:\n{context['instrucoes']}")

        prompt_parts.append("\nRedija a petição completa com todos os elementos obrigatórios.")

        return "\n\n".join(prompt_parts)

    def improve_text(
        self, text: str, context: str = None, premium: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Melhora um texto jurídico existente.

        Args:
            text: Texto a ser melhorado
            context: Contexto adicional (tipo de documento, seção, etc.)
            premium: Se True, usa GPT-4o

        Returns:
            Tuple[str, Dict]: (texto melhorado, metadados)
        """
        system_prompt = SYSTEM_PROMPTS["improve"]

        user_prompt = f"Melhore o seguinte texto jurídico:\n\n{text}"
        if context:
            user_prompt = f"CONTEXTO: {context}\n\n{user_prompt}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        model = MODELS["premium"] if premium else MODELS["fast"]

        return self._call_openai(messages, model=model)

    def analyze_case(
        self, facts: str, question: str = None, premium: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analisa um caso jurídico e fornece orientações.

        Args:
            facts: Descrição dos fatos do caso
            question: Pergunta específica (opcional)
            premium: Se True, usa GPT-4o

        Returns:
            Tuple[str, Dict]: (análise, metadados)
        """
        system_prompt = """Você é um advogado brasileiro experiente.
Analise o caso apresentado e forneça:
1. Qualificação jurídica dos fatos
2. Legislação aplicável
3. Possíveis teses jurídicas
4. Riscos e chances de êxito
5. Recomendações estratégicas

Seja objetivo e fundamentado."""

        user_prompt = f"FATOS DO CASO:\n{facts}"
        if question:
            user_prompt += f"\n\nPERGUNTA ESPECÍFICA: {question}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        model = MODELS["premium"] if premium else MODELS["fast"]

        return self._call_openai(messages, model=model, max_tokens=2500)

    def generate_petition_content(
        self,
        prompt: str,
        context: str = "",
        premium: bool = False,
    ) -> str:
        """
        Gera conteúdo de petição baseado em um prompt específico.

        Args:
            prompt: Prompt do usuário descrevendo o que gerar
            context: Contexto adicional (tipo de petição, dados do modelo, etc.)
            premium: Se True, usa GPT-4o

        Returns:
            str: Conteúdo gerado
        """
        system_prompt = """Você é um advogado brasileiro altamente qualificado e experiente, especializado na redação de petições jurídicas.

INSTRUÇÕES IMPORTANTES:
1. Use linguagem jurídica formal e técnica apropriada
2. Cite artigos de lei quando relevante (CF, CPC, CC, CLT, etc.)
3. Seja preciso e objetivo
4. Mantenha a estrutura profissional de documentos jurídicos
5. Use formatação adequada com parágrafos bem estruturados
6. Responda APENAS com o conteúdo solicitado, sem explicações adicionais
7. NÃO inclua saudações ou despedidas
8. Use português brasileiro formal
9. Adapte o conteúdo ao contexto fornecido quando disponível"""

        user_prompt = prompt
        if context:
            user_prompt = f"CONTEXTO:\n{context}\n\nSOLICITAÇÃO:\n{prompt}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        model = MODELS["premium"] if premium else MODELS["fast"]

        content, _ = self._call_openai(messages, model=model, max_tokens=2000)
        return content

    def analyze_document(
        self, document_text: str, document_name: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analisa um documento (PDF/DOCX extraído) e extrai informações jurídicas.

        Args:
            document_text: Texto extraído do documento
            document_name: Nome do arquivo (opcional)

        Returns:
            Tuple[str, Dict]: (análise do documento, metadados)
        """
        system_prompt = SYSTEM_PROMPTS["analyze_document"]

        user_prompt = f"DOCUMENTO PARA ANÁLISE"
        if document_name:
            user_prompt += f" ({document_name})"
        user_prompt += f":\n\n{document_text[:15000]}"  # Limitar a 15k chars

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Sempre usa modelo premium para análise de documentos
        return self._call_openai(messages, model=MODELS["premium"], max_tokens=3000)

    def generate_fundamentos_from_document(
        self,
        document_text: str,
        document_analysis: str = None,
        petition_type: str = None,
        additional_context: str = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Gera fundamentação jurídica baseada em documento analisado.

        Args:
            document_text: Texto do documento
            document_analysis: Análise prévia do documento (opcional)
            petition_type: Tipo de petição sendo elaborada
            additional_context: Contexto adicional do usuário

        Returns:
            Tuple[str, Dict]: (fundamentação jurídica, metadados)
        """
        system_prompt = SYSTEM_PROMPTS["fundamentos_com_documento"]

        user_prompt_parts = []

        if petition_type:
            user_prompt_parts.append(f"TIPO DE PETIÇÃO: {petition_type}")

        if document_analysis:
            user_prompt_parts.append(f"ANÁLISE DO DOCUMENTO:\n{document_analysis}")
        else:
            user_prompt_parts.append(
                f"CONTEÚDO DO DOCUMENTO:\n{document_text[:12000]}"
            )

        if additional_context:
            user_prompt_parts.append(f"CONTEXTO ADICIONAL:\n{additional_context}")

        user_prompt_parts.append(
            "\nCom base nas informações acima, elabore uma fundamentação jurídica completa e bem estruturada."
        )

        user_prompt = "\n\n".join(user_prompt_parts)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Sempre usa modelo premium para fundamentação
        return self._call_openai(messages, model=MODELS["premium"], max_tokens=4000)

    def should_use_premium(self, generation_type: str) -> bool:
        """
        Verifica se uma operação deve usar o modelo premium por padrão.

        Args:
            generation_type: Tipo de geração (analyze, fundamentos, etc.)

        Returns:
            bool: True se deve usar GPT-4o
        """
        return is_premium_operation(generation_type)

    def analyze_risk(
        self,
        petition_content: str,
        petition_type: str = None,
        fatos: str = None,
        pedidos: str = None,
        fundamentacao: str = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analisa riscos e chances de êxito de uma petição.

        Args:
            petition_content: Conteúdo completo da petição
            petition_type: Tipo da petição (ex: "Ação de Cobrança")
            fatos: Seção de fatos (se separada)
            pedidos: Seção de pedidos (se separada)
            fundamentacao: Seção de fundamentação (se separada)

        Returns:
            Tuple[str, Dict]: (JSON da análise, metadados)
        """
        system_prompt = SYSTEM_PROMPTS["analyze_risk"]

        # Montar o prompt do usuário
        user_prompt_parts = []

        if petition_type:
            user_prompt_parts.append(f"TIPO DE PETIÇÃO: {petition_type}")

        if petition_content:
            # Limitar tamanho para não exceder contexto
            content = petition_content[:15000]
            user_prompt_parts.append(f"PETIÇÃO COMPLETA:\n{content}")
        else:
            # Usar seções separadas
            if fatos:
                user_prompt_parts.append(f"DOS FATOS:\n{fatos[:5000]}")
            if fundamentacao:
                user_prompt_parts.append(f"DO DIREITO:\n{fundamentacao[:5000]}")
            if pedidos:
                user_prompt_parts.append(f"DOS PEDIDOS:\n{pedidos[:2000]}")

        user_prompt_parts.append(
            "\nAnalise esta petição e forneça a avaliação de riscos e chances de êxito no formato JSON especificado."
        )

        user_prompt = "\n\n".join(user_prompt_parts)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Sempre usa modelo premium para análise de riscos
        return self._call_openai(messages, model=MODELS["premium"], max_tokens=3000)


# Instância global do serviço
ai_service = AIService()
