"""
Script para criar as seções e campos padrão do sistema de petições dinâmicas.

Este script define:
1. Seções reutilizáveis (cabeçalho, autor, réu, fatos, pedidos, etc.)
2. Campos de cada seção com tipos, tamanhos e validações
3. Relacionamento entre tipos de petição e suas seções
"""

from app import create_app, db
from app.models import PetitionSection, PetitionType, PetitionTypeSection

app = create_app()

# ============================================================================
# DEFINIÇÃO DAS SEÇÕES PADRÃO DO SISTEMA
# ============================================================================

SECTIONS = [
    {
        "name": "Cabeçalho / Endereçamento",
        "slug": "cabecalho",
        "description": "Fórum, Vara e número do processo",
        "icon": "fa-landmark",
        "color": "primary",
        "order": 1,
        "fields_schema": [
            {
                "name": "forum",
                "label": "Fórum / Tribunal",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Ex: EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA VARA DE FAMÍLIA E SUCESSÕES DA COMARCA DE SÃO PAULO/SP",
            },
            {
                "name": "processo_numero",
                "label": "Número do Processo",
                "type": "text",
                "required": False,
                "size": "col-md-6",
                "placeholder": "0000000-00.0000.0.00.0000",
            },
            {
                "name": "tipo_acao",
                "label": "Tipo de Ação (para referência)",
                "type": "text",
                "required": False,
                "size": "col-md-6",
                "placeholder": "Ex: AÇÃO DE DIVÓRCIO LITIGIOSO",
            },
        ],
    },
    {
        "name": "Autor / Requerente",
        "slug": "autor",
        "description": "Dados e qualificação do autor da ação",
        "icon": "fa-user",
        "color": "success",
        "order": 2,
        "fields_schema": [
            {
                "name": "autor_nome",
                "label": "Nome Completo",
                "type": "text",
                "required": True,
                "size": "col-md-6",
                "placeholder": "Nome completo do autor",
            },
            {
                "name": "autor_nacionalidade",
                "label": "Nacionalidade",
                "type": "text",
                "required": False,
                "size": "col-md-3",
                "placeholder": "Brasileiro(a)",
            },
            {
                "name": "autor_estado_civil",
                "label": "Estado Civil",
                "type": "select",
                "required": False,
                "size": "col-md-3",
                "options": [
                    "Solteiro(a)",
                    "Casado(a)",
                    "Divorciado(a)",
                    "Viúvo(a)",
                    "União Estável",
                    "Separado(a)",
                ],
            },
            {
                "name": "autor_profissao",
                "label": "Profissão",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "Ex: Advogado",
            },
            {
                "name": "autor_cpf",
                "label": "CPF",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "000.000.000-00",
                "mask": "cpf",
            },
            {
                "name": "autor_rg",
                "label": "RG",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "00.000.000-0",
            },
            {
                "name": "autor_endereco",
                "label": "Endereço Completo",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Rua, número, bairro, cidade/UF, CEP",
            },
            {
                "name": "autor_email",
                "label": "E-mail",
                "type": "email",
                "required": False,
                "size": "col-md-6",
                "placeholder": "email@exemplo.com",
            },
            {
                "name": "autor_telefone",
                "label": "Telefone",
                "type": "text",
                "required": False,
                "size": "col-md-6",
                "placeholder": "(00) 00000-0000",
                "mask": "phone",
            },
        ],
    },
    {
        "name": "Réu / Requerido",
        "slug": "reu",
        "description": "Dados e qualificação do réu",
        "icon": "fa-user-tie",
        "color": "danger",
        "order": 3,
        "fields_schema": [
            {
                "name": "reu_nome",
                "label": "Nome Completo",
                "type": "text",
                "required": True,
                "size": "col-md-6",
                "placeholder": "Nome completo do réu",
            },
            {
                "name": "reu_nacionalidade",
                "label": "Nacionalidade",
                "type": "text",
                "required": False,
                "size": "col-md-3",
                "placeholder": "Brasileiro(a)",
            },
            {
                "name": "reu_estado_civil",
                "label": "Estado Civil",
                "type": "select",
                "required": False,
                "size": "col-md-3",
                "options": [
                    "Solteiro(a)",
                    "Casado(a)",
                    "Divorciado(a)",
                    "Viúvo(a)",
                    "União Estável",
                    "Separado(a)",
                ],
            },
            {
                "name": "reu_profissao",
                "label": "Profissão",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "Ex: Empresário",
            },
            {
                "name": "reu_cpf",
                "label": "CPF",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "000.000.000-00",
                "mask": "cpf",
            },
            {
                "name": "reu_rg",
                "label": "RG",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "00.000.000-0",
            },
            {
                "name": "reu_endereco",
                "label": "Endereço Completo",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Rua, número, bairro, cidade/UF, CEP",
            },
        ],
    },
    {
        "name": "Primeiro Cônjuge / Requerente",
        "slug": "conjuge1",
        "description": "Dados do primeiro cônjuge (para ações de família)",
        "icon": "fa-user-circle",
        "color": "info",
        "order": 2,
        "fields_schema": [
            {
                "name": "conjuge1_nome",
                "label": "Nome Completo",
                "type": "text",
                "required": True,
                "size": "col-md-6",
                "placeholder": "Nome completo",
            },
            {
                "name": "conjuge1_nacionalidade",
                "label": "Nacionalidade",
                "type": "text",
                "required": False,
                "size": "col-md-3",
                "placeholder": "Brasileiro(a)",
            },
            {
                "name": "conjuge1_estado_civil",
                "label": "Estado Civil Atual",
                "type": "select",
                "required": False,
                "size": "col-md-3",
                "options": ["Casado(a)", "Separado(a) de fato"],
            },
            {
                "name": "conjuge1_profissao",
                "label": "Profissão",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "Ex: Arquiteta",
            },
            {
                "name": "conjuge1_cpf",
                "label": "CPF",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "000.000.000-00",
                "mask": "cpf",
            },
            {
                "name": "conjuge1_rg",
                "label": "RG",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "00.000.000-0",
            },
            {
                "name": "conjuge1_endereco",
                "label": "Endereço Completo",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Rua, número, bairro, cidade/UF, CEP",
            },
        ],
    },
    {
        "name": "Segundo Cônjuge / Requerido",
        "slug": "conjuge2",
        "description": "Dados do segundo cônjuge (para ações de família)",
        "icon": "fa-user-circle",
        "color": "warning",
        "order": 3,
        "fields_schema": [
            {
                "name": "conjuge2_nome",
                "label": "Nome Completo",
                "type": "text",
                "required": True,
                "size": "col-md-6",
                "placeholder": "Nome completo",
            },
            {
                "name": "conjuge2_nacionalidade",
                "label": "Nacionalidade",
                "type": "text",
                "required": False,
                "size": "col-md-3",
                "placeholder": "Brasileiro(a)",
            },
            {
                "name": "conjuge2_estado_civil",
                "label": "Estado Civil Atual",
                "type": "select",
                "required": False,
                "size": "col-md-3",
                "options": ["Casado(a)", "Separado(a) de fato"],
            },
            {
                "name": "conjuge2_profissao",
                "label": "Profissão",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "Ex: Engenheiro",
            },
            {
                "name": "conjuge2_cpf",
                "label": "CPF",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "000.000.000-00",
                "mask": "cpf",
            },
            {
                "name": "conjuge2_rg",
                "label": "RG",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "00.000.000-0",
            },
            {
                "name": "conjuge2_endereco",
                "label": "Endereço Completo",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Rua, número, bairro, cidade/UF, CEP",
            },
        ],
    },
    {
        "name": "Dados do Casamento",
        "slug": "casamento",
        "description": "Informações sobre o casamento",
        "icon": "fa-ring",
        "color": "secondary",
        "order": 4,
        "fields_schema": [
            {
                "name": "casamento_data",
                "label": "Data do Casamento",
                "type": "date",
                "required": False,
                "size": "col-md-4",
            },
            {
                "name": "casamento_local",
                "label": "Local do Casamento",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "Cidade/UF",
            },
            {
                "name": "casamento_regime",
                "label": "Regime de Bens",
                "type": "select",
                "required": False,
                "size": "col-md-4",
                "options": [
                    "Comunhão Parcial de Bens",
                    "Comunhão Universal de Bens",
                    "Separação Total de Bens",
                    "Participação Final nos Aquestos",
                ],
            },
            {
                "name": "separacao_fato_data",
                "label": "Data da Separação de Fato",
                "type": "date",
                "required": False,
                "size": "col-md-4",
            },
            {
                "name": "certidao_casamento",
                "label": "Certidão de Casamento",
                "type": "text",
                "required": False,
                "size": "col-md-8",
                "placeholder": "Livro, folha, termo, cartório",
            },
        ],
    },
    {
        "name": "Filhos",
        "slug": "filhos",
        "description": "Informações sobre filhos menores ou incapazes",
        "icon": "fa-children",
        "color": "success",
        "order": 5,
        "fields_schema": [
            {
                "name": "tem_filhos_menores",
                "label": "Possui filhos menores ou incapazes?",
                "type": "radio",
                "required": False,
                "size": "col-12",
                "options": ["Sim", "Não"],
                "inline": True,
            },
            {
                "name": "filhos_quantidade",
                "label": "Quantidade de Filhos",
                "type": "number",
                "required": False,
                "size": "col-md-3",
                "show_if": "tem_filhos_menores=Sim",
            },
            {
                "name": "filhos_info",
                "label": "Dados dos Filhos",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 4,
                "placeholder": "Nome completo, data de nascimento e filiação de cada filho menor ou incapaz",
                "show_if": "tem_filhos_menores=Sim",
            },
            {
                "name": "guarda_tipo",
                "label": "Tipo de Guarda Pretendida",
                "type": "select",
                "required": False,
                "size": "col-md-6",
                "options": [
                    "Guarda Compartilhada",
                    "Guarda Unilateral - Mãe",
                    "Guarda Unilateral - Pai",
                    "Guarda Alternada",
                ],
                "show_if": "tem_filhos_menores=Sim",
            },
            {
                "name": "convivencia_regime",
                "label": "Regime de Convivência",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 3,
                "placeholder": "Descreva o regime de visitas e convivência proposto",
                "show_if": "tem_filhos_menores=Sim",
            },
        ],
    },
    {
        "name": "Pensão Alimentícia",
        "slug": "pensao",
        "description": "Informações sobre alimentos",
        "icon": "fa-hand-holding-dollar",
        "color": "warning",
        "order": 6,
        "fields_schema": [
            {
                "name": "tem_pensao",
                "label": "Haverá pensão alimentícia?",
                "type": "radio",
                "required": False,
                "size": "col-12",
                "options": ["Sim", "Não", "Dispensa mútua"],
                "inline": True,
            },
            {
                "name": "pensao_devedor",
                "label": "Quem pagará a pensão?",
                "type": "select",
                "required": False,
                "size": "col-md-4",
                "options": [
                    "Primeiro Cônjuge",
                    "Segundo Cônjuge",
                    "Ambos (proporcional)",
                ],
                "show_if": "tem_pensao=Sim",
            },
            {
                "name": "pensao_valor",
                "label": "Valor/Percentual",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "R$ 0,00 ou 30% dos rendimentos",
                "show_if": "tem_pensao=Sim",
            },
            {
                "name": "pensao_beneficiarios",
                "label": "Beneficiários",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "Nome dos beneficiários",
                "show_if": "tem_pensao=Sim",
            },
            {
                "name": "pensao_detalhes",
                "label": "Detalhes da Pensão",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 3,
                "placeholder": "Inclui plano de saúde, escola, extras? Descreva os detalhes.",
                "show_if": "tem_pensao=Sim",
            },
        ],
    },
    {
        "name": "Patrimônio / Partilha de Bens",
        "slug": "patrimonio",
        "description": "Bens a serem partilhados",
        "icon": "fa-building",
        "color": "secondary",
        "order": 7,
        "fields_schema": [
            {
                "name": "tem_bens",
                "label": "Há bens a partilhar?",
                "type": "radio",
                "required": False,
                "size": "col-12",
                "options": ["Sim", "Não"],
                "inline": True,
            },
            {
                "name": "bens_imoveis",
                "label": "Bens Imóveis",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 3,
                "placeholder": "Descreva os imóveis (endereço, matrícula, valor estimado)",
                "show_if": "tem_bens=Sim",
            },
            {
                "name": "bens_moveis",
                "label": "Bens Móveis",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 3,
                "placeholder": "Veículos, móveis, eletrodomésticos, etc.",
                "show_if": "tem_bens=Sim",
            },
            {
                "name": "bens_financeiros",
                "label": "Bens Financeiros",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Contas bancárias, investimentos, aplicações",
                "show_if": "tem_bens=Sim",
            },
            {
                "name": "partilha_proposta",
                "label": "Proposta de Partilha",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 3,
                "placeholder": "Como será feita a divisão dos bens",
                "show_if": "tem_bens=Sim",
            },
        ],
    },
    {
        "name": "Dívidas",
        "slug": "dividas",
        "description": "Dívidas do casal a serem divididas",
        "icon": "fa-credit-card",
        "color": "danger",
        "order": 8,
        "fields_schema": [
            {
                "name": "tem_dividas",
                "label": "Há dívidas a partilhar?",
                "type": "radio",
                "required": False,
                "size": "col-12",
                "options": ["Sim", "Não"],
                "inline": True,
            },
            {
                "name": "dividas_descricao",
                "label": "Descrição das Dívidas",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 3,
                "placeholder": "Descreva as dívidas existentes e seus valores",
                "show_if": "tem_dividas=Sim",
            },
            {
                "name": "dividas_responsabilidade",
                "label": "Responsabilidade pelas Dívidas",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Como será dividida a responsabilidade",
                "show_if": "tem_dividas=Sim",
            },
        ],
    },
    {
        "name": "Uso do Nome",
        "slug": "nome",
        "description": "Alteração de nome após divórcio",
        "icon": "fa-signature",
        "color": "info",
        "order": 9,
        "fields_schema": [
            {
                "name": "alterar_nome",
                "label": "Haverá alteração de nome?",
                "type": "radio",
                "required": False,
                "size": "col-12",
                "options": [
                    "Sim, retornar ao nome de solteiro(a)",
                    "Não, manter o nome atual",
                ],
                "inline": False,
            },
            {
                "name": "nome_solteiro",
                "label": "Nome de Solteiro(a) a Retornar",
                "type": "text",
                "required": False,
                "size": "col-12",
                "placeholder": "Nome completo de solteiro(a)",
                "show_if": "alterar_nome=Sim, retornar ao nome de solteiro(a)",
            },
        ],
    },
    {
        "name": "Dos Fatos",
        "slug": "fatos",
        "description": "Narrativa dos fatos que fundamentam a ação",
        "icon": "fa-book-open",
        "color": "primary",
        "order": 10,
        "fields_schema": [
            {
                "name": "fatos",
                "label": "Dos Fatos",
                "type": "editor",
                "required": True,
                "size": "col-12",
                "placeholder": "Descreva os fatos que fundamentam a ação...",
                "rows": 10,
            },
        ],
    },
    {
        "name": "Do Direito / Fundamentação",
        "slug": "direito",
        "description": "Fundamentação jurídica",
        "icon": "fa-scale-balanced",
        "color": "info",
        "order": 11,
        "fields_schema": [
            {
                "name": "fundamentos",
                "label": "Do Direito",
                "type": "editor",
                "required": True,
                "size": "col-12",
                "placeholder": "Fundamente juridicamente o pedido...",
                "rows": 10,
            },
        ],
    },
    {
        "name": "Dos Pedidos",
        "slug": "pedidos",
        "description": "Pedidos finais da petição",
        "icon": "fa-list-check",
        "color": "success",
        "order": 12,
        "fields_schema": [
            {
                "name": "pedidos",
                "label": "Dos Pedidos",
                "type": "editor",
                "required": True,
                "size": "col-12",
                "placeholder": "Liste os pedidos...",
                "rows": 8,
            },
        ],
    },
    {
        "name": "Valor da Causa",
        "slug": "valor-causa",
        "description": "Valor atribuído à causa",
        "icon": "fa-dollar-sign",
        "color": "success",
        "order": 13,
        "fields_schema": [
            {
                "name": "valor_causa",
                "label": "Valor da Causa (R$)",
                "type": "currency",
                "required": False,
                "size": "col-md-6",
                "placeholder": "0,00",
            },
        ],
    },
    {
        "name": "Provas",
        "slug": "provas",
        "description": "Provas a serem produzidas",
        "icon": "fa-folder-open",
        "color": "secondary",
        "order": 14,
        "fields_schema": [
            {
                "name": "provas_documentais",
                "label": "Provas Documentais (rol de documentos)",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 3,
                "placeholder": "Liste os documentos anexados",
            },
            {
                "name": "provas_testemunhais",
                "label": "Provas Testemunhais",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Rol de testemunhas (nome, endereço)",
            },
            {
                "name": "provas_outras",
                "label": "Outras Provas",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Perícias, depoimento pessoal, etc.",
            },
        ],
    },
    {
        "name": "Justiça Gratuita",
        "slug": "justica-gratuita",
        "description": "Requerimento de gratuidade de justiça",
        "icon": "fa-hand-holding-heart",
        "color": "info",
        "order": 15,
        "fields_schema": [
            {
                "name": "requer_justica_gratuita",
                "label": "Requer os benefícios da Justiça Gratuita?",
                "type": "radio",
                "required": False,
                "size": "col-12",
                "options": ["Sim", "Não"],
                "inline": True,
            },
            {
                "name": "justica_gratuita_justificativa",
                "label": "Justificativa",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Justifique o pedido de gratuidade",
                "show_if": "requer_justica_gratuita=Sim",
            },
        ],
    },
    {
        "name": "Local e Data",
        "slug": "assinatura",
        "description": "Local, data e identificação para assinatura",
        "icon": "fa-pen-fancy",
        "color": "dark",
        "order": 99,
        "fields_schema": [
            {
                "name": "cidade",
                "label": "Cidade",
                "type": "text",
                "required": False,
                "size": "col-md-6",
                "placeholder": "São Paulo/SP",
            },
            {
                "name": "data_peticao",
                "label": "Data",
                "type": "date",
                "required": False,
                "size": "col-md-6",
            },
        ],
    },
    # ========== SEÇÕES PARA PETIÇÕES INTERMEDIÁRIAS ==========
    {
        "name": "Dados do Processo",
        "slug": "processo-existente",
        "description": "Para petições em processos já existentes",
        "icon": "fa-file-lines",
        "color": "secondary",
        "order": 1,
        "fields_schema": [
            {
                "name": "processo_numero",
                "label": "Número do Processo",
                "type": "text",
                "required": True,
                "size": "col-md-6",
                "placeholder": "0000000-00.0000.0.00.0000",
            },
            {
                "name": "vara_processo",
                "label": "Vara/Juízo",
                "type": "text",
                "required": False,
                "size": "col-md-6",
                "placeholder": "Ex: 1ª Vara Cível",
            },
            {
                "name": "tipo_acao_original",
                "label": "Tipo de Ação",
                "type": "text",
                "required": False,
                "size": "col-md-6",
                "placeholder": "Ex: Execução de Título Extrajudicial",
            },
            {
                "name": "autor_execucao",
                "label": "Exequente/Autor",
                "type": "text",
                "required": True,
                "size": "col-md-6",
                "placeholder": "Nome do exequente",
            },
            {
                "name": "reu_execucao",
                "label": "Executado/Réu",
                "type": "text",
                "required": True,
                "size": "col-12",
                "placeholder": "Nome do executado",
            },
        ],
    },
    {
        "name": "Levantamento de Valores (MLE)",
        "slug": "mle",
        "description": "Dados para mandado de levantamento eletrônico",
        "icon": "fa-money-bill-transfer",
        "color": "success",
        "order": 10,
        "fields_schema": [
            {
                "name": "mle_valor",
                "label": "Valor a Levantar",
                "type": "currency",
                "required": True,
                "size": "col-md-4",
                "placeholder": "0,00",
            },
            {
                "name": "mle_referencia",
                "label": "Referência nos Autos",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "Ex: fl. 222",
            },
            {
                "name": "mle_origem",
                "label": "Origem do Depósito",
                "type": "text",
                "required": False,
                "size": "col-md-4",
                "placeholder": "Ex: Penhora online",
            },
            {
                "name": "mle_tipo_pagamento",
                "label": "Forma de Recebimento",
                "type": "select",
                "required": True,
                "size": "col-md-4",
                "options": ["PIX", "Transferência Bancária", "Alvará"],
            },
            {
                "name": "mle_chave_pix",
                "label": "Chave PIX",
                "type": "text",
                "required": False,
                "size": "col-md-8",
                "placeholder": "CPF, e-mail, telefone ou chave aleatória",
                "show_if": "mle_tipo_pagamento=PIX",
            },
            {
                "name": "mle_banco",
                "label": "Banco",
                "type": "text",
                "required": False,
                "size": "col-md-3",
                "show_if": "mle_tipo_pagamento=Transferência Bancária",
            },
            {
                "name": "mle_agencia",
                "label": "Agência",
                "type": "text",
                "required": False,
                "size": "col-md-3",
                "show_if": "mle_tipo_pagamento=Transferência Bancária",
            },
            {
                "name": "mle_conta",
                "label": "Conta",
                "type": "text",
                "required": False,
                "size": "col-md-3",
                "show_if": "mle_tipo_pagamento=Transferência Bancária",
            },
            {
                "name": "mle_titular",
                "label": "Titular",
                "type": "text",
                "required": False,
                "size": "col-md-3",
                "show_if": "mle_tipo_pagamento=Transferência Bancária",
            },
            {
                "name": "mle_cpf_titular",
                "label": "CPF do Titular",
                "type": "text",
                "required": False,
                "size": "col-md-6",
            },
        ],
    },
    {
        "name": "Penhora de Benefício INSS",
        "slug": "penhora-inss",
        "description": "Dados para penhora de benefício previdenciário",
        "icon": "fa-hand-holding-dollar",
        "color": "warning",
        "order": 10,
        "fields_schema": [
            {
                "name": "inss_beneficio_valor",
                "label": "Valor do Benefício INSS",
                "type": "currency",
                "required": True,
                "size": "col-md-4",
                "placeholder": "0,00",
            },
            {
                "name": "inss_penhora_percentual",
                "label": "Percentual a Penhorar (%)",
                "type": "number",
                "required": True,
                "size": "col-md-4",
                "placeholder": "30",
            },
            {
                "name": "inss_penhora_valor",
                "label": "Valor Mensal da Penhora",
                "type": "currency",
                "required": False,
                "size": "col-md-4",
                "placeholder": "0,00",
            },
            {
                "name": "inss_debito_total",
                "label": "Débito Total Atualizado",
                "type": "currency",
                "required": True,
                "size": "col-md-6",
                "placeholder": "0,00",
            },
            {
                "name": "inss_tempo_inadimplencia",
                "label": "Tempo de Inadimplência",
                "type": "text",
                "required": False,
                "size": "col-md-6",
                "placeholder": "Ex: 9 anos",
            },
            {
                "name": "inss_tentativas_anteriores",
                "label": "Tentativas Anteriores de Satisfação",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 3,
                "placeholder": "Descreva tentativas frustradas de penhora (bens, veículos, contas, etc.)",
            },
            {
                "name": "inss_justificativa",
                "label": "Justificativa para Penhora do Benefício",
                "type": "editor",
                "required": False,
                "size": "col-12",
                "rows": 6,
                "placeholder": "Justifique a excepcionalidade da medida...",
            },
        ],
    },
    {
        "name": "Juntada Simples",
        "slug": "juntada",
        "description": "Para petição de juntada de documentos",
        "icon": "fa-paperclip",
        "color": "primary",
        "order": 10,
        "fields_schema": [
            {
                "name": "juntada_descricao",
                "label": "Documentos a Juntar",
                "type": "textarea",
                "required": True,
                "size": "col-12",
                "rows": 4,
                "placeholder": "Descreva os documentos que serão juntados aos autos",
            },
            {
                "name": "juntada_motivo",
                "label": "Motivo da Juntada",
                "type": "textarea",
                "required": False,
                "size": "col-12",
                "rows": 2,
                "placeholder": "Razão pela qual os documentos estão sendo juntados",
            },
        ],
    },
]


# ============================================================================
# MAPEAMENTO DE TIPOS DE PETIÇÃO PARA SUAS SEÇÕES
# ============================================================================

PETITION_TYPE_SECTIONS = {
    # Petição Cível Genérica
    "peticao-inicial-civel": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "reu", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "valor-causa", "required": False, "expanded": False},
        {"slug": "provas", "required": False, "expanded": False},
        {"slug": "justica-gratuita", "required": False, "expanded": False},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Ação de Cobrança
    "acao-de-cobranca": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "reu", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "valor-causa", "required": True, "expanded": True},
        {"slug": "provas", "required": False, "expanded": False},
        {"slug": "justica-gratuita", "required": False, "expanded": False},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Ação de Alimentos
    "acao-de-alimentos": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "reu", "required": True, "expanded": True},
        {"slug": "pensao", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "valor-causa", "required": False, "expanded": False},
        {"slug": "justica-gratuita", "required": False, "expanded": False},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Guarda e Regulamentação de Visitas
    "guarda-e-regulacao-de-visitas": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "reu", "required": True, "expanded": True},
        {"slug": "filhos", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "valor-causa", "required": False, "expanded": False},
        {"slug": "justica-gratuita", "required": False, "expanded": False},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Divórcio Litigioso
    "divorcio-litigioso": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "conjuge1", "required": True, "expanded": True},
        {"slug": "conjuge2", "required": True, "expanded": True},
        {"slug": "casamento", "required": True, "expanded": True},
        {"slug": "filhos", "required": False, "expanded": False},
        {"slug": "pensao", "required": False, "expanded": False},
        {"slug": "patrimonio", "required": False, "expanded": False},
        {"slug": "dividas", "required": False, "expanded": False},
        {"slug": "nome", "required": False, "expanded": False},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": False},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "valor-causa", "required": False, "expanded": False},
        {"slug": "provas", "required": False, "expanded": False},
        {"slug": "justica-gratuita", "required": False, "expanded": False},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Divórcio Consensual
    "divorcio-consensual": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "conjuge1", "required": True, "expanded": True},
        {"slug": "conjuge2", "required": True, "expanded": True},
        {"slug": "casamento", "required": True, "expanded": True},
        {"slug": "filhos", "required": False, "expanded": False},
        {"slug": "pensao", "required": False, "expanded": False},
        {"slug": "patrimonio", "required": False, "expanded": False},
        {"slug": "nome", "required": False, "expanded": False},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": False, "expanded": False},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Petição de Juntada de MLE
    "peticao-juntada-mle": [
        {"slug": "processo-existente", "required": True, "expanded": True},
        {"slug": "mle", "required": True, "expanded": True},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Petição de Penhora INSS
    "peticao-simples-penhora-inss": [
        {"slug": "processo-existente", "required": True, "expanded": True},
        {"slug": "penhora-inss", "required": True, "expanded": True},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Contestação Cível
    "contestacao-civel": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "processo-existente", "required": True, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "reu", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "provas", "required": False, "expanded": False},
        {"slug": "justica-gratuita", "required": False, "expanded": False},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Mandado de Segurança
    "mandado-de-seguranca": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "reu", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "provas", "required": True, "expanded": True},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Reclamação Trabalhista
    "reclamacao-trabalhista": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "reu", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "valor-causa", "required": True, "expanded": True},
        {"slug": "justica-gratuita", "required": False, "expanded": False},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Defesa Trabalhista
    "defesa-trabalhista": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "processo-existente", "required": True, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "reu", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "provas", "required": False, "expanded": False},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Habeas Corpus
    "pedido-de-habeas-corpus": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Defesa Criminal
    "defesa-criminal": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "processo-existente", "required": True, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "provas", "required": False, "expanded": False},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
    # Execução Fiscal
    "execucao-fiscal": [
        {"slug": "cabecalho", "required": False, "expanded": True},
        {"slug": "processo-existente", "required": True, "expanded": True},
        {"slug": "autor", "required": True, "expanded": True},
        {"slug": "fatos", "required": True, "expanded": True},
        {"slug": "direito", "required": True, "expanded": True},
        {"slug": "pedidos", "required": True, "expanded": True},
        {"slug": "valor-causa", "required": True, "expanded": True},
        {"slug": "assinatura", "required": False, "expanded": True},
    ],
}


def setup_sections():
    """Cria as seções padrão no banco de dados."""
    with app.app_context():
        print("=" * 70)
        print("🔧 CONFIGURANDO SISTEMA DINÂMICO DE PETIÇÕES")
        print("=" * 70)

        # ========== CRIAR SEÇÕES ==========
        print("\n📦 Criando seções de petição...")

        created_count = 0
        updated_count = 0

        for section_data in SECTIONS:
            slug = section_data["slug"]
            section = PetitionSection.query.filter_by(slug=slug).first()

            if section:
                # Atualizar existente
                for key, value in section_data.items():
                    setattr(section, key, value)
                print(f"  ✓ Atualizada: {section_data['name']}")
                updated_count += 1
            else:
                # Criar novo
                section = PetitionSection(**section_data)
                db.session.add(section)
                print(f"  + Criada: {section_data['name']}")
                created_count += 1

            # Commit após cada seção para evitar timeout
            db.session.commit()

        print(f"\n  Total: {created_count} criadas, {updated_count} atualizadas")

        # ========== VINCULAR SEÇÕES AOS TIPOS DE PETIÇÃO ==========
        print("\n🔗 Vinculando seções aos tipos de petição...")

        # Recarregar seções do banco como dicionário {slug: id}
        all_sections = PetitionSection.query.all()
        section_map = {s.slug: s.id for s in all_sections}

        configured_count = 0

        for type_slug, sections_config in PETITION_TYPE_SECTIONS.items():
            petition_type = PetitionType.query.filter_by(slug=type_slug).first()

            if not petition_type:
                print(f"  ⚠️ Tipo não encontrado: {type_slug}")
                continue

            # Ativar formulário dinâmico para este tipo
            petition_type.use_dynamic_form = True
            db.session.commit()

            # Remover vínculos antigos
            PetitionTypeSection.query.filter_by(
                petition_type_id=petition_type.id
            ).delete()
            db.session.commit()

            # Criar novos vínculos
            links_created = 0
            for order, section_config in enumerate(sections_config):
                section_id = section_map.get(section_config["slug"])
                if not section_id:
                    print(f"    ⚠️ Seção não encontrada: {section_config['slug']}")
                    continue

                link = PetitionTypeSection(
                    petition_type_id=petition_type.id,
                    section_id=section_id,
                    order=order,
                    is_required=section_config.get("required", False),
                    is_expanded=section_config.get("expanded", True),
                    field_overrides=section_config.get("field_overrides", {}),
                )
                db.session.add(link)
                links_created += 1

            # Commit após cada tipo de petição
            db.session.commit()
            print(f"  ✓ {petition_type.name}: {links_created} seções")
            configured_count += 1

        # ========== RESUMO ==========
        print("\n" + "=" * 70)
        print("✅ CONFIGURAÇÃO CONCLUÍDA!")
        print("=" * 70)
        print(f"\n📊 Resumo:")
        print(f"   • {len(section_map)} seções no sistema")
        print(f"   • {configured_count} tipos de petição configurados")
        print("\n💡 Próximos passos:")
        print("   1. Acesse o sistema e teste os formulários dinâmicos")
        print("   2. Use o painel admin para ajustar seções se necessário")


if __name__ == "__main__":
    setup_sections()
