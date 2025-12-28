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


class FamilyPetitionForm(FlaskForm):
    template_id = SelectField(
        "Modelo",
        coerce=int,
        validators=[DataRequired()],
    )
    forum = StringField(
        "Fórum",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Ex: TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO"},
    )
    vara = StringField(
        "Vara",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Ex: 1ª Vara de Família e Sucessões"},
    )
    process_number = StringField(
        "Número do Processo", validators=[Optional(), Length(max=100)]
    )
    action_type = SelectField(
        "Tipo da ação",
        validators=[Optional()],
        choices=[
            ("", "Selecione o tipo de ação"),
            ("ACOES_FAMILIARES", "AÇÕES FAMILIARES"),
            ("DIVORCIO_LITIGIOSO", "AÇÃO DE DIVÓRCIO LITIGIOSO"),
            ("DIVORCIO_CONSENSUAL", "AÇÃO DE DIVÓRCIO CONSENSUAL"),
            ("GUARDA", "AÇÃO DE GUARDA"),
            ("ALIMENTOS", "AÇÃO DE ALIMENTOS"),
            ("REGULAMENTACAO_VISITAS", "AÇÃO DE REGULAMENTAÇÃO DE VISITAS"),
            ("INVASAO_POSSE", "AÇÃO DE INVASÃO DE POSSE"),
            ("USUCAPIAO", "AÇÃO DE USUCAPIÃO"),
            ("OBRIGACOES_CONTRATUAIS", "AÇÕES OBRIGAÇÕES CONTRATUAIS"),
            ("COBRANCA", "AÇÃO DE COBRANÇA"),
            ("EXECUCAO", "AÇÃO DE EXECUÇÃO"),
            ("MONITORIA", "AÇÃO MONITORIA"),
            ("RESCISAO_CONTRATUAL", "AÇÃO DE RESCISÃO CONTRATUAL"),
            ("INDENIZACAO_DANOS", "AÇÃO DE INDENIZAÇÃO POR DANOS"),
            ("RESPONSABILIDADE_CIVIL", "AÇÃO DE RESPONSABILIDADE CIVIL"),
            ("DIREITO_CONSUMIDOR", "AÇÕES DIREITO DO CONSUMIDOR"),
            ("ANULACAO_CONTRATO", "AÇÃO DE ANULAÇÃO DE CONTRATO"),
            ("RECONHECIMENTO_UNIAO_ESTAVEL", "AÇÃO DE RECONHECIMENTO DE UNIÃO ESTÁVEL"),
            ("PARTILHA_BENS", "AÇÃO DE PARTILHA DE BENS"),
            ("REVISIONAL_ALIMENTOS", "AÇÃO REVISIONAL DE ALIMENTOS"),
            ("EXONERACAO_ALIMENTOS", "AÇÃO DE EXONERAÇÃO DE ALIMENTOS"),
            ("OUTROS", "OUTROS"),
        ],
        render_kw={"class": "form-select"},
    )
    action_type_other = StringField(
        "Especificar tipo de ação",
        validators=[Optional(), Length(max=180)],
        render_kw={"placeholder": "Ex: AÇÃO DE DESPEJO, AÇÃO POSSESSÓRIA, etc."},
    )

    # Dados do casamento
    marriage_date = DateField("Data do casamento/união", validators=[Optional()])
    marriage_city = StringField(
        "Cidade do casamento", validators=[Optional(), Length(max=180)]
    )
    marriage_regime = SelectField(
        "Regime de bens",
        choices=[
            ("", "Selecione..."),
            ("comunhao_parcial", "Comunhão Parcial de Bens"),
            ("comunhao_universal", "Comunhão Universal de Bens"),
            ("separacao_total", "Separação Total de Bens"),
            ("participacao_final", "Participação Final nos Aquestos"),
        ],
        validators=[Optional()],
    )
    has_prenup = BooleanField("Existe pacto antenupcial?", default=False)
    prenup_details = TextAreaField(
        "Detalhes do pacto", validators=[Optional()], render_kw={"rows": 2}
    )

    # Data da separação de fato (específico para divórcio litigioso)
    separation_date = DateField("Data da separação de fato", validators=[Optional()])

    # Partes
    spouse_one_name = StringField(
        "Nome da Autora/Autor", validators=[DataRequired(), Length(max=255)]
    )
    spouse_one_qualification = TextAreaField(
        "Qualificação da Autora/Autor",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Ex: brasileira, casada, do lar, RG nº ..., CPF nº ..., residente e domiciliada na Rua ...",
        },
    )
    author_address = TextAreaField(
        "Endereço completo da Autora/Autor",
        validators=[Optional()],
        render_kw={"rows": 2, "placeholder": "Rua, nº, bairro, cidade/UF, CEP"},
    )
    author_cpf = StringField(
        "CPF da Autora/Autor", validators=[Optional(), Length(max=20)]
    )
    spouse_two_name = StringField(
        "Nome do Réu/Ré", validators=[DataRequired(), Length(max=255)]
    )
    spouse_two_qualification = TextAreaField(
        "Qualificação do Réu/Ré",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Ex: brasileiro, casado, motorista, RG nº ..., CPF nº ..., residente e domiciliado na Rua ...",
        },
    )
    defendant_address = TextAreaField(
        "Endereço completo do Réu/Ré",
        validators=[Optional()],
        render_kw={"rows": 2, "placeholder": "Rua, nº, bairro, cidade/UF, CEP"},
    )

    # Filhos
    children_info = TextAreaField(
        "Filhos e necessidades",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Nome, idade, RG, CPF e necessidades especiais de cada filho",
        },
    )
    children_names = StringField(
        "Nomes dos filhos menores (para citação na petição)",
        validators=[Optional(), Length(max=500)],
        render_kw={"placeholder": "Ex: MARIA, 13 anos, JOÃO, 8 anos e PEDRO, 5 anos"},
    )
    custody_plan = TextAreaField(
        "Proposta de guarda/convivência",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Descreva o regime de guarda pretendido e regulamentação de visitas",
        },
    )

    # Pensão alimentícia
    alimony_plan = TextAreaField(
        "Proposta de alimentos",
        validators=[Optional()],
        render_kw={
            "rows": 4,
            "placeholder": "Descreva as despesas dos filhos e a proposta de pensão",
        },
    )
    defendant_income = StringField(
        "Renda mensal do Réu",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: 6.800,00"},
    )
    alimony_amount = StringField(
        "Valor/percentual pleiteado de pensão",
        validators=[Optional(), Length(max=200)],
        render_kw={"placeholder": "Ex: 135% do salário mínimo ou R$ 2.059,00"},
    )

    # Plano de saúde
    health_plan_details = TextAreaField(
        "Detalhes do plano de saúde",
        validators=[Optional()],
        render_kw={
            "rows": 2,
            "placeholder": "Descreva a situação do plano de saúde dos filhos",
        },
    )

    # Bens e dívidas
    property_description = TextAreaField(
        "Relação de bens a partilhar",
        validators=[Optional()],
        render_kw={
            "rows": 4,
            "placeholder": "Descreva os bens adquiridos durante o casamento",
        },
    )
    debts_description = TextAreaField(
        "Relação de dívidas do casal",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Descreva as dívidas contraídas durante o casamento",
        },
    )

    # Violência doméstica / Medida protetiva
    has_domestic_violence = BooleanField("Houve violência doméstica?", default=False)
    domestic_violence_facts = TextAreaField(
        "Relato da violência doméstica",
        validators=[Optional()],
        render_kw={
            "rows": 4,
            "placeholder": "Descreva os fatos relacionados à violência doméstica",
        },
    )
    has_protective_order = BooleanField("Existe medida protetiva?", default=False)
    protective_order_details = TextAreaField(
        "Detalhes da medida protetiva",
        validators=[Optional()],
        render_kw={
            "rows": 2,
            "placeholder": "Nº do processo, prazo, restrições determinadas",
        },
    )
    moral_damages_amount = StringField(
        "Valor pleiteado de danos morais",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: R$ 6.800,00"},
    )

    # Alteração de nome
    name_change = StringField(
        "Nome de solteira (se deseja retornar)",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Nome completo de solteira"},
    )

    # Justiça gratuita
    request_free_justice = BooleanField("Requer justiça gratuita?", default=True)

    # Conteúdo da petição
    divorce_facts = TextAreaField(
        "Fatos do divórcio",
        validators=[Optional()],
        render_kw={
            "rows": 5,
            "placeholder": "Descreva os fatos que levaram ao pedido de divórcio",
        },
    )
    facts = TextAreaField(
        "Fatos gerais", validators=[DataRequired()], render_kw={"rows": 5}
    )
    fundamentos = TextAreaField(
        "Fundamentação jurídica", validators=[DataRequired()], render_kw={"rows": 5}
    )
    pedidos = TextAreaField(
        "Pedidos", validators=[DataRequired()], render_kw={"rows": 4}
    )
    valor_causa = DecimalField("Valor da Causa (R$)", validators=[Optional()], places=2)

    # Advogado e assinatura
    cidade = StringField(
        "Cidade",
        validators=[Optional(), Length(max=120)],
        render_kw={"placeholder": "Ex: São Paulo/SP"},
    )
    data_assinatura = DateField("Data", default=date.today, validators=[Optional()])
    advogado_nome = StringField(
        "Nome do advogado",
        validators=[Optional(), Length(max=255)],
        render_kw={"readonly": True, "class": "form-control-plaintext"},
    )
    advogado_oab = StringField(
        "OAB",
        validators=[Optional(), Length(max=50)],
        render_kw={"readonly": True, "class": "form-control-plaintext"},
    )
    lawyer_address = TextAreaField(
        "Endereço profissional do advogado",
        validators=[Optional()],
        render_kw={"rows": 2, "placeholder": "Rua, nº, bairro, cidade/UF, CEP"},
    )
    signature_author = BooleanField(
        "Incluir assinatura da parte autora?", default=False
    )

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


class SimplePetitionForm(FlaskForm):
    """Formulário para petições simples (juntada de documentos, MLE, etc.)"""

    template_id = SelectField(
        "Modelo",
        coerce=int,
        validators=[DataRequired()],
    )

    # Dados do processo
    forum = StringField(
        "Fórum/Tribunal",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Ex: TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO"},
    )
    vara = StringField(
        "Vara",
        validators=[Optional(), Length(max=255)],
        render_kw={
            "placeholder": "Ex: 1ª Vara do Juizado Especial Cível de Santo Amaro"
        },
    )
    process_number = StringField(
        "Número do Processo",
        validators=[DataRequired(), Length(max=100)],
        render_kw={"placeholder": "Ex: 1234567-89.2024.8.26.0002"},
    )
    action_type = SelectField(
        "Tipo da ação original",
        validators=[Optional()],
        choices=[
            ("", "Selecione o tipo de ação"),
            ("ACOES_FAMILIARES", "AÇÕES FAMILIARES"),
            ("DIVORCIO_LITIGIOSO", "AÇÃO DE DIVÓRCIO LITIGIOSO"),
            ("DIVORCIO_CONSENSUAL", "AÇÃO DE DIVÓRCIO CONSENSUAL"),
            ("GUARDA", "AÇÃO DE GUARDA"),
            ("ALIMENTOS", "AÇÃO DE ALIMENTOS"),
            ("REGULAMENTACAO_VISITAS", "AÇÃO DE REGULAMENTAÇÃO DE VISITAS"),
            ("INVASAO_POSSE", "AÇÃO DE INVASÃO DE POSSE"),
            ("USUCAPIAO", "AÇÃO DE USUCAPIÃO"),
            ("OBRIGACOES_CONTRATUAIS", "AÇÕES OBRIGAÇÕES CONTRATUAIS"),
            ("COBRANCA", "AÇÃO DE COBRANÇA"),
            ("EXECUCAO", "AÇÃO DE EXECUÇÃO"),
            ("MONITORIA", "AÇÃO MONITORIA"),
            ("RESCISAO_CONTRATUAL", "AÇÃO DE RESCISÃO CONTRATUAL"),
            ("INDENIZACAO_DANOS", "AÇÃO DE INDENIZAÇÃO POR DANOS"),
            ("RESPONSABILIDADE_CIVIL", "AÇÃO DE RESPONSABILIDADE CIVIL"),
            ("DIREITO_CONSUMIDOR", "AÇÕES DIREITO DO CONSUMIDOR"),
            ("ANULACAO_CONTRATO", "AÇÃO DE ANULAÇÃO DE CONTRATO"),
            ("RECONHECIMENTO_UNIAO_ESTAVEL", "AÇÃO DE RECONHECIMENTO DE UNIÃO ESTÁVEL"),
            ("PARTILHA_BENS", "AÇÃO DE PARTILHA DE BENS"),
            ("REVISIONAL_ALIMENTOS", "AÇÃO REVISIONAL DE ALIMENTOS"),
            ("EXONERACAO_ALIMENTOS", "AÇÃO DE EXONERAÇÃO DE ALIMENTOS"),
            ("OUTROS", "OUTROS"),
        ],
        render_kw={"class": "form-select"},
    )
    action_type_other = StringField(
        "Especificar tipo de ação original",
        validators=[Optional(), Length(max=180)],
        render_kw={"placeholder": "Ex: AÇÃO DE DESPEJO, AÇÃO POSSESSÓRIA, etc."},
    )

    # Partes
    author_name = StringField(
        "Nome do Autor/Requerente",
        validators=[DataRequired(), Length(max=255)],
    )
    defendant_name = StringField(
        "Nome do Réu/Requerido",
        validators=[Optional(), Length(max=255)],
    )

    # Dados do levantamento (MLE)
    valor_levantamento = StringField(
        "Valor a levantar",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: 854,60"},
    )
    valor_extenso = StringField(
        "Valor por extenso",
        validators=[Optional(), Length(max=255)],
        render_kw={
            "placeholder": "Ex: oitocentos e cinquenta e quatro reais e sessenta centavos"
        },
    )
    folhas_referencia = StringField(
        "Folhas de referência",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: 222 e 223"},
    )

    # Dados bancários
    pix_chave = StringField(
        "Chave PIX",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Ex: CPF, e-mail ou telefone"},
    )
    banco_dados = StringField(
        "Dados bancários (alternativo ao PIX)",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Ex: Banco Itaú, Ag. 1234, C/C 56789-0"},
    )
    titular_conta = StringField(
        "Titular da conta",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Nome do advogado ou da parte"},
    )
    procuracao_folha = StringField(
        "Procuração (folha)",
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "Ex: 50"},
    )

    # Dados da Penhora INSS
    valor_beneficio_inss = StringField(
        "Valor do benefício INSS",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: 1.212,00"},
    )
    valor_beneficio_extenso = StringField(
        "Valor por extenso",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Ex: um mil duzentos e doze reais"},
    )
    percentual_penhora = StringField(
        "Percentual de penhora",
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "Ex: 30%"},
    )
    valor_penhora = StringField(
        "Valor mensal a penhorar",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: 363,60"},
    )
    valor_penhora_extenso = StringField(
        "Valor da penhora por extenso",
        validators=[Optional(), Length(max=255)],
        render_kw={
            "placeholder": "Ex: trezentos e sessenta e três reais e sessenta centavos"
        },
    )
    debito_atualizado = StringField(
        "Débito atualizado total",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: 10.369,41"},
    )
    debito_extenso = StringField(
        "Débito por extenso",
        validators=[Optional(), Length(max=255)],
        render_kw={
            "placeholder": "Ex: dez mil, trezentos e sessenta e nove reais e quarenta e um centavos"
        },
    )
    qtd_parcelas = StringField(
        "Quantidade de parcelas estimadas",
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "Ex: 30"},
    )
    tempo_inadimplencia = StringField(
        "Tempo de inadimplência",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Ex: 9 (nove) anos"},
    )

    # Conteúdo
    facts = TextAreaField(
        "Justificativa/Fatos",
        validators=[Optional()],
        render_kw={"rows": 4, "placeholder": "Descreva o motivo do requerimento..."},
    )
    pedidos = TextAreaField(
        "Pedidos",
        validators=[Optional()],
        render_kw={"rows": 4},
    )

    # Assinatura
    cidade = StringField(
        "Cidade",
        validators=[Optional(), Length(max=120)],
        render_kw={"placeholder": "Ex: São Paulo"},
    )
    data_assinatura = DateField("Data", default=date.today, validators=[Optional()])
    advogado_nome = StringField(
        "Nome do advogado",
        validators=[Optional(), Length(max=255)],
        render_kw={"readonly": True},
    )
    advogado_oab = StringField(
        "OAB",
        validators=[Optional(), Length(max=50)],
        render_kw={"readonly": True},
    )

    # Anexos
    documents = MultipleFileField(
        "Documentos anexos (MLE, comprovantes, etc.)",
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
