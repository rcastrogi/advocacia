"""
Marshmallow schemas para validação de dados
"""

from datetime import datetime

from marshmallow import EXCLUDE, Schema, ValidationError, fields, post_load, pre_load, validate, validates_schema
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

# ============================================================================
# USER SCHEMAS
# ============================================================================


class UserSchema(Schema):
    """Validação de usuários"""

    id = fields.Int(dump_only=True)
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=255),
        error_messages={"required": "Username é obrigatório"},
    )
    email = fields.Email(
        required=True,
        error_messages={"required": "Email é obrigatório", "invalid": "Email inválido"},
    )
    full_name = fields.Str(validate=validate.Length(min=3, max=255), allow_none=True)
    password = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=255),
        load_only=True,
        error_messages={
            "required": "Senha é obrigatória",
            "validate": "Senha deve ter no mínimo 6 caracteres",
        },
    )
    password_confirm = fields.Str(
        required=True,
        load_only=True,
        error_messages={"required": "Confirmação de senha é obrigatória"},
    )
    user_type = fields.Str(
        validate=validate.OneOf(["advogado", "escritorio", "master"]),
        error_messages={"validate": "Tipo de usuário inválido"},
    )
    oab_number = fields.Str(allow_none=True, validate=validate.Length(max=50))
    cpf = fields.Str(allow_none=True, validate=validate.Length(min=11, max=14))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @pre_load
    def validate_passwords_match(self, data, **kwargs):
        """Valida se as senhas correspondem"""
        if data.get("password") and data.get("password_confirm"):
            if data["password"] != data["password_confirm"]:
                raise fields.ValidationError(
                    "Senhas não correspondem", field_name="password_confirm"
                )
        return data


class UserUpdateSchema(Schema):
    """Validação para atualização de usuários (sem senha)"""

    full_name = fields.Str(validate=validate.Length(min=3, max=255), allow_none=True)
    email = fields.Email(allow_none=False)
    oab_number = fields.Str(allow_none=True, validate=validate.Length(max=50))
    cpf = fields.Str(allow_none=True, validate=validate.Length(min=11, max=14))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=20))


class UserLoginSchema(Schema):
    """Validação para login"""

    username = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)


# ============================================================================
# PLAN SCHEMAS
# ============================================================================


class BillingPlanSchema(Schema):
    """Validação de planos de cobrança"""

    id = fields.Int(dump_only=True)
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100),
        error_messages={"required": "Nome do plano é obrigatório"},
    )
    plan_type = fields.Str(
        required=True,
        validate=validate.OneOf(["trial", "basic", "professional", "enterprise"]),
        error_messages={"validate": "Tipo de plano inválido"},
    )
    price = fields.Decimal(
        required=True,
        validate=validate.Range(min=0),
        error_messages={
            "required": "Preço é obrigatório",
            "validate": "Preço deve ser >= 0",
        },
    )
    billing_cycle = fields.Str(
        validate=validate.OneOf(["monthly", "yearly", "trial"]), allow_none=True
    )
    max_petitions_month = fields.Int(validate=validate.Range(min=0), allow_none=True)
    max_petitions_concurrent = fields.Int(
        validate=validate.Range(min=0), allow_none=True
    )
    max_clients = fields.Int(validate=validate.Range(min=0), allow_none=True)
    ai_credits_month = fields.Int(validate=validate.Range(min=0), allow_none=True)
    is_active = fields.Bool(dump_default=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


# ============================================================================
# PETITION SCHEMAS
# ============================================================================


class PetitionTypeSchema(Schema):
    """Validação de tipos de petição"""

    class Meta:
        unknown = EXCLUDE  # Ignora campos extras

    id = fields.Int(dump_only=True)
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=500),
        error_messages={"required": "Nome do tipo é obrigatório"},
    )
    # Slug é gerado automaticamente a partir do nome, não é obrigatório na entrada
    slug = fields.Str(
        load_default=None,
        validate=validate.Length(max=120),
    )
    description = fields.Str(allow_none=True)
    category = fields.Str(
        load_default="civel",
        validate=validate.Length(max=50),
    )
    icon = fields.Str(
        load_default="fa-file-alt",
        validate=validate.Length(max=50),
    )
    color = fields.Str(
        load_default="primary",
        validate=validate.Length(max=20),
    )
    base_price = fields.Decimal(load_default=0, allow_none=True)
    is_billable = fields.Bool(load_default=True)
    is_implemented = fields.Bool(load_default=False)
    is_active = fields.Bool(load_default=True)
    use_dynamic_form = fields.Bool(load_default=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @pre_load
    def process_checkboxes(self, data, **kwargs):
        """Converte valores de checkbox HTML para booleanos"""
        for field in ["is_active", "is_billable", "is_implemented", "use_dynamic_form"]:
            if field in data:
                value = data[field]
                if value in ["on", "true", "1", True, 1]:
                    data[field] = True
                elif value in ["off", "false", "0", False, 0, "", None]:
                    data[field] = False
            else:
                # Checkbox não marcado não envia nada, então é False
                data[field] = False
        return data


class PetitionModelSchema(Schema):
    """Validação de modelos de petição"""

    class Meta:
        unknown = EXCLUDE  # Ignora campos extras como section_order, etc.

    id = fields.Int(dump_only=True)
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255),
        error_messages={"required": "Nome do modelo é obrigatório"},
    )
    petition_type_id = fields.Int(
        required=True, error_messages={"required": "Tipo de petição é obrigatório"}
    )
    description = fields.Str(allow_none=True)
    template_content = fields.Str(
        required=False,  # Não obrigatório - pode ser gerado depois
        allow_none=True,
        load_default="",
    )
    is_active = fields.Bool(load_default=False)
    use_dynamic_form = fields.Bool(load_default=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @pre_load
    def process_checkboxes(self, data, **kwargs):
        """Converte valores de checkbox HTML para booleanos"""
        # Checkboxes HTML enviam "on" quando marcados ou não enviam nada
        for field in ["is_active", "use_dynamic_form"]:
            if field in data:
                value = data[field]
                if value in ["on", "true", "1", True]:
                    data[field] = True
                else:
                    data[field] = False
            else:
                # Se não enviou, checkbox não está marcado
                data[field] = False
        return data


class PetitionSchema(Schema):
    """Validação de petições (rascunhos)"""

    id = fields.Int(dump_only=True)
    title = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255),
        error_messages={"required": "Título é obrigatório"},
    )
    petition_type_id = fields.Int(
        required=True, error_messages={"required": "Tipo de petição é obrigatório"}
    )
    petition_model_id = fields.Int(
        required=True, error_messages={"required": "Modelo de petição é obrigatório"}
    )
    process_number = fields.Str(allow_none=True, validate=validate.Length(max=30))
    author_name = fields.Str(allow_none=True)
    defendant_name = fields.Str(allow_none=True)
    content = fields.Str(allow_none=True)
    status = fields.Str(
        validate=validate.OneOf(["draft", "completed", "cancelled"]),
        dump_default="draft",
    )
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class PetitionSectionSchema(Schema):
    """Validação de seções de petição"""

    id = fields.Int(dump_only=True)
    title = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255),
        error_messages={"required": "Título da seção é obrigatório"},
    )
    slug = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100),
        error_messages={"required": "Slug é obrigatório"},
    )
    description = fields.Str(allow_none=True)
    order = fields.Int(validate=validate.Range(min=0))
    is_active = fields.Bool(dump_default=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


# ============================================================================
# PROCESS SCHEMAS
# ============================================================================


class ProcessSchema(Schema):
    """Validação de processos"""

    id = fields.Int(dump_only=True)
    process_number = fields.Str(
        required=True,
        validate=validate.Length(min=5, max=30),
        error_messages={"required": "Número do processo é obrigatório"},
    )
    title = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255),
        error_messages={"required": "Título é obrigatório"},
    )
    court = fields.Str(allow_none=True)
    plaintiff = fields.Str(allow_none=True)
    defendant = fields.Str(allow_none=True)
    status = fields.Str(
        validate=validate.OneOf(
            [
                "pending_distribution",
                "distributed",
                "ongoing",
                "suspended",
                "archived",
                "finished",
            ]
        ),
        dump_default="pending_distribution",
    )
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


# ============================================================================
# ROADMAP SCHEMAS
# ============================================================================


class RoadmapItemSchema(Schema):
    """Validação de itens de roadmap"""

    id = fields.Int(dump_only=True)
    title = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255),
        error_messages={"required": "Título do item é obrigatório"},
    )
    slug = fields.Str(allow_none=True, validate=validate.Length(max=255))
    description = fields.Str(allow_none=True)
    detailed_description = fields.Str(allow_none=True)
    category_id = fields.Int(
        required=True, error_messages={"required": "Categoria é obrigatória"}
    )
    priority = fields.Str(
        validate=validate.OneOf(["low", "medium", "high", "critical"]),
        dump_default="medium",
        allow_none=True,
    )
    status = fields.Str(
        validate=validate.OneOf(
            ["planned", "in_progress", "completed", "cancelled", "on_hold"]
        ),
        dump_default="planned",
        allow_none=True,
    )
    estimated_effort = fields.Str(
        validate=validate.OneOf(["small", "medium", "large", "xlarge"]),
        dump_default="medium",
        allow_none=True,
    )
    visible_to_users = fields.Bool(dump_default=False)
    internal_only = fields.Bool(dump_default=False)
    show_new_badge = fields.Bool(dump_default=False)
    planned_start_date = fields.Date(allow_none=True)
    planned_completion_date = fields.Date(allow_none=True)
    actual_start_date = fields.Date(dump_only=True, allow_none=True)
    actual_completion_date = fields.Date(dump_only=True, allow_none=True)
    business_value = fields.Str(allow_none=True)
    technical_complexity = fields.Str(
        validate=validate.OneOf(["low", "medium", "high"]),
        dump_default="medium",
        allow_none=True,
    )
    user_impact = fields.Str(
        validate=validate.OneOf(["low", "medium", "high"]),
        dump_default="medium",
        allow_none=True,
    )
    dependencies = fields.Str(allow_none=True)
    blockers = fields.Str(allow_none=True)
    tags = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)
    assigned_to = fields.Int(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @pre_load
    def process_input(self, data, **kwargs):
        """Pré-processar dados do form (converte strings para tipos corretos)"""
        # Converter campos booleanos (form envia "on" ou não envia nada)
        for bool_field in ["visible_to_users", "internal_only", "show_new_badge"]:
            if bool_field in data:
                data[bool_field] = data[bool_field] in ["on", "true", True, "1", 1]

        # Converter campos vazios para None
        for key in data:
            if data[key] == "":
                data[key] = None

        return data


class RoadmapCategorySchema(Schema):
    """Validação de categorias de roadmap"""

    id = fields.Int(dump_only=True)
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100),
        error_messages={"required": "Nome da categoria é obrigatório"},
    )
    slug = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100),
        error_messages={"required": "Slug é obrigatório"},
    )
    description = fields.Str(allow_none=True)
    icon = fields.Str(dump_default="fa-lightbulb")
    color = fields.Str(allow_none=True)
    order = fields.Int(dump_default=0)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


# ============================================================================
# FORM FIELD SCHEMAS (PARA VALIDAÇÃO DE CAMPOS DINÂMICOS)
# ============================================================================


class FormFieldSchema(Schema):
    """Validação de campos de formulário dinâmicos"""

    id = fields.Int(dump_only=True)
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100),
        error_messages={"required": "Nome do campo é obrigatório"},
    )
    label = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255),
        error_messages={"required": "Rótulo é obrigatório"},
    )
    field_type = fields.Str(
        required=True,
        validate=validate.OneOf(
            [
                "text",
                "textarea",
                "email",
                "date",
                "select",
                "checkbox",
                "radio",
                "number",
                "tel",
                "url",
            ]
        ),
        error_messages={"validate": "Tipo de campo inválido"},
    )
    required = fields.Bool(dump_default=False)
    order = fields.Int(validate=validate.Range(min=0))
    options = fields.List(fields.Str(), allow_none=True)
    validation_regex = fields.Str(allow_none=True)
    placeholder = fields.Str(allow_none=True)


# ============================================================================
# BULK SCHEMAS (PARA OPERAÇÕES EM LOTE)
# ============================================================================


class BulkActionSchema(Schema):
    """Validação para ações em lote"""

    action = fields.Str(
        required=True,
        validate=validate.OneOf(["activate", "deactivate", "delete", "export"]),
        error_messages={"required": "Ação é obrigatória", "validate": "Ação inválida"},
    )
    ids = fields.List(
        fields.Int(),
        required=True,
        validate=validate.Length(min=1),
        error_messages={
            "required": "IDs são obrigatórios",
            "validate": "Pelo menos 1 ID é necessário",
        },
    )
    reason = fields.Str(allow_none=True)


# ============================================================================
# PAYMENT SCHEMAS
# ============================================================================


class PaymentSchema(Schema):
    """Validação de pagamentos PIX"""

    amount = fields.Decimal(
        required=True,
        places=2,
        validate=validate.Range(min=0.01),
        error_messages={
            "required": "Valor é obrigatório",
            "validate": "Valor deve ser maior que 0",
        },
    )
    description = fields.Str(allow_none=True, validate=validate.Length(max=500))
    plan_id = fields.Int(allow_none=True)
    subscription_id = fields.Int(allow_none=True)


class SubscriptionSchema(Schema):
    """Validação de subscrições Mercado Pago"""

    plan_id = fields.Int(
        required=True, error_messages={"required": "Plano é obrigatório"}
    )
    card_token = fields.Str(
        required=True,
        validate=validate.Length(min=10),
        error_messages={"required": "Token do cartão é obrigatório"},
    )
    auto_recurring = fields.Bool(dump_default=True)
    trial_period = fields.Int(allow_none=True, validate=validate.Range(min=0))


class WebhookSchema(Schema):
    """Validação de webhooks de pagamento"""

    id = fields.Str(required=True)
    type = fields.Str(required=True)
    data = fields.Dict(allow_none=True)
    action = fields.Str(allow_none=True)


# ============================================================================
# PETITION SCHEMAS (EXTENDED)
# ============================================================================


class PetitionSaveSchema(Schema):
    """Validação para salvar petição"""

    petition_type_id = fields.Int(
        required=True, error_messages={"required": "Tipo de petição é obrigatório"}
    )
    petition_model_id = fields.Int(allow_none=True)
    data = fields.Dict(required=True)
    title = fields.Str(allow_none=True, validate=validate.Length(min=3, max=255))
    notes = fields.Str(allow_none=True)


class GenerateDynamicSchema(Schema):
    """Validação para gerar petição dinâmica"""

    petition_type_id = fields.Int(
        required=True, error_messages={"required": "Tipo de petição é obrigatório"}
    )
    form_data = fields.Dict(required=True)
    with_ai = fields.Bool(dump_default=False)


class GenerateModelSchema(Schema):
    """Validação para gerar modelo de petição"""

    petition_model_id = fields.Int(
        required=True, error_messages={"required": "Modelo é obrigatório"}
    )
    form_data = fields.Dict(required=True)


class AttachmentUploadSchema(Schema):
    """Validação para upload de anexos"""

    file_name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    file_size = fields.Int(
        validate=validate.Range(min=1, max=52428800)  # 50MB max
    )
    mime_type = fields.Str(
        required=True,
        validate=validate.OneOf(
            [
                "application/pdf",
                "image/png",
                "image/jpeg",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ]
        ),
    )


# ============================================================================
# PORTAL API SCHEMAS
# ============================================================================


class ChatMessageSchema(Schema):
    """Validação de mensagens de chat"""

    message = fields.Str(
        required=False,
        validate=validate.Length(min=1, max=2000),
        error_messages={
            "validate": "Mensagem deve ter entre 1 e 2000 caracteres",
        },
    )
    content = fields.Str(
        required=False,
        validate=validate.Length(min=1, max=2000),
        error_messages={
            "validate": "Mensagem deve ter entre 1 e 2000 caracteres",
        },
    )
    conversation_id = fields.Int(allow_none=True)
    ai_mode = fields.Bool(dump_default=False)
    use_bot = fields.Bool(dump_default=True)
    message_type = fields.Str(
        validate=validate.OneOf(["text", "file"]),
        dump_default="text"
    )

    @validates_schema
    def validate_message_or_content(self, data, **kwargs):
        """Validar que pelo menos message ou content foi fornecido"""
        if not data.get("message") and not data.get("content"):
            raise ValidationError({"message": ["Mensagem é obrigatória"]})


class UserPreferencesSchema(Schema):
    """Validação de preferências do usuário"""

    theme = fields.Str(
        validate=validate.OneOf(["light", "dark", "auto"]), dump_default="auto"
    )
    language = fields.Str(
        validate=validate.OneOf(["pt-BR", "en-US", "es-ES"]), dump_default="pt-BR"
    )
    notifications_enabled = fields.Bool(dump_default=True)
    email_digest = fields.Str(
        validate=validate.OneOf(["daily", "weekly", "monthly", "never"]),
        dump_default="weekly",
    )
    two_factor_enabled = fields.Bool(dump_default=False)


class PushSubscriptionSchema(Schema):
    """Validação de inscrição push"""

    endpoint = fields.Url(
        required=True, error_messages={"required": "Endpoint é obrigatório"}
    )
    auth_key = fields.Str(required=True)
    p256dh_key = fields.Str(required=True)


# ============================================================================
# USER CONTENT SCHEMAS
# ============================================================================


class TestimonialSchema(Schema):
    """Validação de depoimentos"""

    title = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=200),
        error_messages={"required": "Título é obrigatório"},
    )
    content = fields.Str(
        required=True,
        validate=validate.Length(min=10, max=2000),
        error_messages={"required": "Conteúdo é obrigatório"},
    )
    rating = fields.Int(validate=validate.Range(min=1, max=5), dump_default=5)
    author_name = fields.Str(allow_none=True, validate=validate.Length(max=100))
    is_public = fields.Bool(dump_default=False)


class RoadmapFeedbackSchema(Schema):
    """Validação de feedback de roadmap"""

    roadmap_item_id = fields.Int(
        required=True, error_messages={"required": "Item é obrigatório"}
    )
    feedback_type = fields.Str(
        required=True,
        validate=validate.OneOf(["upvote", "comment", "request"]),
        error_messages={"required": "Tipo de feedback é obrigatório"},
    )
    message = fields.Str(allow_none=True, validate=validate.Length(min=5, max=1000))


class OABValidationSchema(Schema):
    """Validação de consulta OAB"""

    oab_number = fields.Str(
        required=True,
        validate=validate.Regexp(r"^\d{4,7}$"),
        error_messages={
            "required": "Número OAB é obrigatório",
            "validate": "OAB deve conter 4-7 dígitos",
        },
    )
    state = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=2),
        error_messages={"required": "Estado é obrigatório"},
    )
    name = fields.Str(allow_none=True, validate=validate.Length(max=200))


# ============================================================================
# ERROR RESPONSE SCHEMA (PARA PADRONIZAR RESPOSTAS DE ERRO)
# ============================================================================


class ErrorResponseSchema(Schema):
    """Estrutura de resposta de erro padronizada"""

    success = fields.Bool(dump_default=False)
    error = fields.Str(required=True)
    message = fields.Str(allow_none=True)
    errors = fields.Dict(
        keys=fields.Str(), values=fields.List(fields.Str()), allow_none=True
    )
    status_code = fields.Int(dump_default=400)
    timestamp = fields.DateTime(dump_default=datetime.utcnow)


class SuccessResponseSchema(Schema):
    """Estrutura de resposta de sucesso padronizada"""

    success = fields.Bool(dump_default=True)
    message = fields.Str(allow_none=True)
    data = fields.Dict(allow_none=True)
    status_code = fields.Int(dump_default=200)
    timestamp = fields.DateTime(dump_default=datetime.utcnow)
