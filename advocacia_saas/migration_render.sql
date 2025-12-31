-- Migration generated from schema_render.json
-- Execute this on Render PostgreSQL database

CREATE TABLE IF NOT EXISTS client (
    id INTEGER NOT NULL DEFAULT nextval('client_id_seq'::regclass) PRIMARY KEY,
    lawyer_id INTEGER NOT NULL,
    user_id INTEGER NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    full_name VARCHAR(200) NOT NULL,
    rg VARCHAR(20) NULL,
    cpf_cnpj VARCHAR(20) NOT NULL,
    civil_status VARCHAR(50) NULL,
    birth_date DATE NULL,
    profession VARCHAR(100) NULL,
    nationality VARCHAR(50) NULL,
    birth_place VARCHAR(100) NULL,
    mother_name VARCHAR(200) NULL,
    father_name VARCHAR(200) NULL,
    address_type VARCHAR(20) NULL,
    cep VARCHAR(10) NULL,
    street VARCHAR(200) NULL,
    number VARCHAR(20) NULL,
    uf VARCHAR(2) NULL,
    city VARCHAR(100) NULL,
    neighborhood VARCHAR(100) NULL,
    complement VARCHAR(200) NULL,
    landline_phone VARCHAR(20) NULL,
    email VARCHAR(120) NOT NULL,
    mobile_phone VARCHAR(20) NOT NULL,
    lgbt_declared BOOLEAN NULL,
    has_disability BOOLEAN NULL,
    disability_types VARCHAR(200) NULL,
    is_pregnant_postpartum BOOLEAN NULL,
    delivery_date DATE NULL
);

CREATE TABLE IF NOT EXISTS estados (
    id INTEGER NOT NULL DEFAULT nextval('estados_id_seq'::regclass) PRIMARY KEY,
    sigla VARCHAR(2) NOT NULL,
    nome VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS cidades (
    id INTEGER NOT NULL DEFAULT nextval('cidades_id_seq'::regclass) PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    estado_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_petition_types (
    plan_id INTEGER NOT NULL PRIMARY KEY,
    petition_type_id INTEGER NOT NULL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS billing_plans (
    id INTEGER NOT NULL DEFAULT nextval('billing_plans_id_seq'::regclass) PRIMARY KEY,
    slug VARCHAR(80) NOT NULL,
    name VARCHAR(120) NOT NULL,
    plan_type VARCHAR(20) NOT NULL,
    monthly_fee NUMERIC(10, 2) NULL,
    monthly_petition_limit INTEGER NULL,
    description TEXT NULL,
    active BOOLEAN NULL,
    created_at TIMESTAMP NULL,
    supported_periods VARCHAR(10) NULL DEFAULT '["1m", "3m", "6m", "1y", "2y", "3y"]'::json,
    discount_percentage NUMERIC(5, 2) NULL DEFAULT 0.00
);

CREATE TABLE IF NOT EXISTS petition_types (
    id INTEGER NOT NULL DEFAULT nextval('petition_types_id_seq'::regclass) PRIMARY KEY,
    slug VARCHAR(80) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    category VARCHAR(50) NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    is_implemented BOOLEAN NULL,
    is_billable BOOLEAN NULL,
    is_active BOOLEAN NULL,
    base_price NUMERIC(10, 2) NULL,
    active BOOLEAN NULL,
    use_dynamic_form BOOLEAN NULL,
    created_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS petition_templates (
    id INTEGER NOT NULL DEFAULT nextval('petition_templates_id_seq'::regclass) PRIMARY KEY,
    slug VARCHAR(120) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    category VARCHAR(50) NULL,
    content TEXT NOT NULL,
    default_values TEXT NULL,
    is_global BOOLEAN NULL,
    is_active BOOLEAN NULL,
    owner_id INTEGER NULL,
    petition_type_id INTEGER NOT NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS user_plans (
    id INTEGER NOT NULL DEFAULT nextval('user_plans_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    status VARCHAR(20) NULL,
    started_at TIMESTAMP NULL,
    renewal_date TIMESTAMP NULL,
    is_current BOOLEAN NULL
);

CREATE TABLE IF NOT EXISTS petition_usage (
    id INTEGER NOT NULL DEFAULT nextval('petition_usage_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    petition_type_id INTEGER NOT NULL,
    plan_id INTEGER NULL,
    generated_at TIMESTAMP NULL,
    billing_cycle VARCHAR(7) NULL,
    billable BOOLEAN NULL,
    amount NUMERIC(10, 2) NULL,
    extra_data JSON NULL
);

CREATE TABLE IF NOT EXISTS testimonials (
    id INTEGER NOT NULL DEFAULT nextval('testimonials_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    rating INTEGER NULL,
    display_name VARCHAR(200) NOT NULL,
    display_role VARCHAR(100) NULL,
    display_location VARCHAR(100) NULL,
    status VARCHAR(20) NULL,
    moderated_by INTEGER NULL,
    moderated_at TIMESTAMP NULL,
    rejection_reason TEXT NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    is_featured BOOLEAN NULL
);

CREATE TABLE IF NOT EXISTS petition_type_sections (
    id INTEGER NOT NULL DEFAULT nextval('petition_type_sections_id_seq'::regclass) PRIMARY KEY,
    petition_type_id INTEGER NOT NULL,
    section_id INTEGER NOT NULL,
    order INTEGER NULL,
    is_required BOOLEAN NULL,
    is_expanded BOOLEAN NULL,
    field_overrides JSON NULL
);

CREATE TABLE IF NOT EXISTS petition_sections (
    id INTEGER NOT NULL DEFAULT nextval('petition_sections_id_seq'::regclass) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    description VARCHAR(255) NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    order INTEGER NULL,
    is_active BOOLEAN NULL,
    fields_schema JSON NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS user_credits (
    id INTEGER NOT NULL DEFAULT nextval('user_credits_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    balance INTEGER NULL,
    total_purchased INTEGER NULL,
    total_used INTEGER NULL,
    total_bonus INTEGER NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS ai_generations (
    id INTEGER NOT NULL DEFAULT nextval('ai_generations_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    generation_type VARCHAR(50) NOT NULL,
    petition_type_slug VARCHAR(100) NULL,
    section_name VARCHAR(100) NULL,
    credits_used INTEGER NOT NULL,
    model_used VARCHAR(50) NULL,
    tokens_input INTEGER NULL,
    tokens_output INTEGER NULL,
    tokens_total INTEGER NULL,
    cost_usd NUMERIC(10, 6) NULL,
    prompt_summary VARCHAR(500) NULL,
    input_data TEXT NULL,
    output_content TEXT NULL,
    status VARCHAR(20) NULL,
    error_message TEXT NULL,
    user_rating INTEGER NULL,
    was_used BOOLEAN NULL,
    created_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    response_time_ms INTEGER NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER NOT NULL DEFAULT nextval('notifications_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    link VARCHAR(500) NULL,
    read BOOLEAN NULL,
    created_at TIMESTAMP NULL,
    read_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER NOT NULL DEFAULT nextval('subscriptions_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_type VARCHAR(50) NOT NULL,
    billing_period VARCHAR(20) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NULL,
    status VARCHAR(20) NULL,
    trial_ends_at TIMESTAMP NULL,
    current_period_start TIMESTAMP NULL,
    current_period_end TIMESTAMP NULL,
    cancel_at_period_end BOOLEAN NULL,
    canceled_at TIMESTAMP NULL,
    gateway VARCHAR(20) NULL,
    gateway_subscription_id VARCHAR(200) NULL,
    gateway_customer_id VARCHAR(200) NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    refund_policy VARCHAR(20) NULL DEFAULT 'no_refund'::character varying,
    refund_amount NUMERIC(10, 2) NULL,
    refund_processed_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER NOT NULL DEFAULT nextval('expenses_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    case_id INTEGER NULL,
    description VARCHAR(500) NOT NULL,
    category VARCHAR(100) NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NULL,
    expense_date DATE NULL,
    payment_method VARCHAR(50) NULL,
    reimbursable BOOLEAN NULL,
    reimbursed BOOLEAN NULL,
    reimbursed_date DATE NULL,
    receipt_filename VARCHAR(500) NULL,
    receipt_url VARCHAR(500) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS client_lawyers (
    client_id INTEGER NOT NULL PRIMARY KEY,
    lawyer_id INTEGER NOT NULL PRIMARY KEY,
    created_at TIMESTAMP NULL,
    specialty VARCHAR(100) NULL,
    is_primary BOOLEAN NULL
);

CREATE TABLE IF NOT EXISTS dependent (
    id INTEGER NOT NULL DEFAULT nextval('dependent_id_seq'::regclass) PRIMARY KEY,
    client_id INTEGER NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    relationship VARCHAR(50) NOT NULL,
    birth_date DATE NULL,
    cpf VARCHAR(14) NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER NOT NULL DEFAULT nextval('invoices_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    client_id INTEGER NULL,
    case_id INTEGER NULL,
    billing_cycle VARCHAR(7) NULL,
    amount_due NUMERIC(10, 2) NULL,
    amount_paid NUMERIC(10, 2) NULL,
    issued_at TIMESTAMP NULL,
    invoice_number VARCHAR(50) NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NULL,
    description TEXT NULL,
    notes TEXT NULL,
    issue_date DATE NULL,
    due_date TIMESTAMP NULL,
    paid_date DATE NULL,
    status VARCHAR(20) NULL,
    is_recurring BOOLEAN NULL,
    recurrence_interval VARCHAR(20) NULL,
    next_invoice_date DATE NULL,
    payment_method VARCHAR(50) NULL,
    boleto_url VARCHAR(500) NULL,
    pix_code TEXT NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS petition_attachments (
    id INTEGER NOT NULL DEFAULT nextval('petition_attachments_id_seq'::regclass) PRIMARY KEY,
    saved_petition_id INTEGER NOT NULL,
    filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(100) NULL,
    file_size INTEGER NULL,
    category VARCHAR(50) NULL,
    description VARCHAR(500) NULL,
    uploaded_at TIMESTAMP NULL,
    uploaded_by_id INTEGER NULL
);

CREATE TABLE IF NOT EXISTS credit_transactions (
    id INTEGER NOT NULL DEFAULT nextval('credit_transactions_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description VARCHAR(255) NULL,
    package_id INTEGER NULL,
    generation_id INTEGER NULL,
    created_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS credit_packages (
    id INTEGER NOT NULL DEFAULT nextval('credit_packages_id_seq'::regclass) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) NOT NULL,
    credits INTEGER NOT NULL,
    bonus_credits INTEGER NULL,
    price NUMERIC(10, 2) NOT NULL,
    original_price NUMERIC(10, 2) NULL,
    currency VARCHAR(3) NULL,
    description TEXT NULL,
    is_active BOOLEAN NULL,
    is_featured BOOLEAN NULL,
    sort_order INTEGER NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS deadlines (
    id INTEGER NOT NULL DEFAULT nextval('deadlines_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    case_id INTEGER NULL,
    client_id INTEGER NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    deadline_type VARCHAR(50) NULL,
    deadline_date TIMESTAMP NOT NULL,
    alert_days_before INTEGER NULL,
    alert_sent BOOLEAN NULL,
    alert_sent_at TIMESTAMP NULL,
    status VARCHAR(20) NULL,
    completed_at TIMESTAMP NULL,
    completion_notes TEXT NULL,
    is_recurring BOOLEAN NULL,
    recurrence_pattern VARCHAR(50) NULL,
    recurrence_end_date DATE NULL,
    count_business_days BOOLEAN NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER NOT NULL DEFAULT nextval('messages_id_seq'::regclass) PRIMARY KEY,
    sender_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    client_id INTEGER NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(20) NULL,
    attachment_filename VARCHAR(500) NULL,
    attachment_path VARCHAR(500) NULL,
    attachment_size INTEGER NULL,
    attachment_type VARCHAR(100) NULL,
    is_read BOOLEAN NULL,
    read_at TIMESTAMP NULL,
    is_deleted_by_sender BOOLEAN NULL,
    is_deleted_by_recipient BOOLEAN NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS chat_rooms (
    id INTEGER NOT NULL DEFAULT nextval('chat_rooms_id_seq'::regclass) PRIMARY KEY,
    lawyer_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    title VARCHAR(200) NULL,
    is_active BOOLEAN NULL,
    last_message_at TIMESTAMP NULL,
    last_message_preview VARCHAR(200) NULL,
    unread_count_lawyer INTEGER NULL,
    unread_count_client INTEGER NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER NOT NULL DEFAULT nextval('documents_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    document_type VARCHAR(50) NULL,
    category VARCHAR(100) NULL,
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NULL,
    file_type VARCHAR(100) NULL,
    file_extension VARCHAR(10) NULL,
    version INTEGER NULL,
    parent_document_id INTEGER NULL,
    is_latest_version BOOLEAN NULL,
    is_visible_to_client BOOLEAN NULL,
    is_confidential BOOLEAN NULL,
    status VARCHAR(20) NULL,
    tags VARCHAR(500) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    last_accessed_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER NOT NULL DEFAULT nextval('payments_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    invoice_id INTEGER NULL,
    subscription_id INTEGER NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NULL,
    payment_type VARCHAR(20) NOT NULL,
    payment_method VARCHAR(50) NULL,
    method VARCHAR(30) NULL,
    reference VARCHAR(120) NULL,
    description VARCHAR(500) NULL,
    status VARCHAR(20) NULL,
    payment_status VARCHAR(30) NULL,
    paid_at TIMESTAMP NULL,
    failed_at TIMESTAMP NULL,
    refunded_at TIMESTAMP NULL,
    webhook_received_at TIMESTAMP NULL,
    gateway VARCHAR(20) NULL,
    gateway_payment_id VARCHAR(200) NULL,
    gateway_charge_id VARCHAR(200) NULL,
    pix_code TEXT NULL,
    pix_qr_code TEXT NULL,
    pix_expires_at TIMESTAMP NULL,
    extra_data TEXT NULL,
    extra_metadata JSON NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS roadmap_categories (
    id INTEGER NOT NULL DEFAULT nextval('roadmap_categories_id_seq'::regclass) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) NOT NULL,
    description TEXT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    order INTEGER NULL,
    is_active BOOLEAN NULL,
    created_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS roadmap_items (
    id INTEGER NOT NULL DEFAULT nextval('roadmap_items_id_seq'::regclass) PRIMARY KEY,
    category_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    detailed_description TEXT NULL,
    status VARCHAR(20) NULL,
    priority VARCHAR(20) NULL,
    estimated_effort VARCHAR(20) NULL,
    visible_to_users BOOLEAN NULL,
    internal_only BOOLEAN NULL,
    planned_start_date DATE NULL,
    planned_completion_date DATE NULL,
    actual_start_date DATE NULL,
    actual_completion_date DATE NULL,
    business_value TEXT NULL,
    technical_complexity VARCHAR(20) NULL,
    user_impact VARCHAR(20) NULL,
    dependencies TEXT NULL,
    blockers TEXT NULL,
    tags VARCHAR(500) NULL,
    notes TEXT NULL,
    created_by INTEGER NULL,
    assigned_to INTEGER NULL,
    last_updated_by INTEGER NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    implemented_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS roadmap_feedback (
    id INTEGER NOT NULL PRIMARY KEY,
    roadmap_item_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    rating_category VARCHAR(50) NULL,
    title VARCHAR(200) NULL,
    comment TEXT NULL,
    pros TEXT NULL,
    cons TEXT NULL,
    suggestions TEXT NULL,
    usage_frequency VARCHAR(20) NULL,
    ease_of_use VARCHAR(20) NULL,
    user_agent VARCHAR(500) NULL,
    ip_address VARCHAR(45) NULL,
    session_id VARCHAR(100) NULL,
    is_anonymous BOOLEAN NULL DEFAULT false,
    is_featured BOOLEAN NULL DEFAULT false,
    status VARCHAR(20) NULL DEFAULT 'pending'::character varying,
    admin_response TEXT NULL,
    responded_by INTEGER NULL,
    responded_at TIMESTAMP NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS anonymization_requests (
    id INTEGER NOT NULL DEFAULT nextval('anonymization_requests_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    status VARCHAR(20) NULL,
    request_reason TEXT NOT NULL,
    data_categories TEXT NULL,
    anonymization_method VARCHAR(50) NULL,
    requested_at TIMESTAMP NULL,
    processed_at TIMESTAMP NULL,
    processed_by INTEGER NULL,
    anonymized_data TEXT NULL,
    notes TEXT NULL
);

CREATE TABLE IF NOT EXISTS data_consents (
    id INTEGER NOT NULL DEFAULT nextval('data_consents_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    consent_purpose TEXT NOT NULL,
    consented BOOLEAN NULL,
    consent_version VARCHAR(20) NULL,
    consented_at TIMESTAMP NULL,
    withdrawn_at TIMESTAMP NULL,
    expires_at TIMESTAMP NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    consent_method VARCHAR(50) NULL
);

CREATE TABLE IF NOT EXISTS deletion_requests (
    id INTEGER NOT NULL DEFAULT nextval('deletion_requests_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    status VARCHAR(20) NULL,
    request_reason TEXT NOT NULL,
    deletion_scope TEXT NULL,
    retention_reason TEXT NULL,
    legal_basis TEXT NULL,
    appeal_deadline TIMESTAMP NULL,
    requested_at TIMESTAMP NULL,
    processed_at TIMESTAMP NULL,
    processed_by INTEGER NULL,
    deletion_summary TEXT NULL,
    rejection_reason TEXT NULL,
    notes TEXT NULL
);

CREATE TABLE IF NOT EXISTS data_processing_logs (
    id INTEGER NOT NULL DEFAULT nextval('data_processing_logs_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,
    data_category VARCHAR(100) NOT NULL,
    data_fields TEXT NULL,
    purpose TEXT NOT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    endpoint VARCHAR(200) NULL,
    request_id VARCHAR(100) NULL,
    legal_basis VARCHAR(100) NULL,
    consent_id INTEGER NULL,
    processed_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS user (
    id INTEGER NOT NULL DEFAULT nextval('user_id_seq'::regclass) PRIMARY KEY,
    username VARCHAR(80) NOT NULL,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    user_type VARCHAR(20) NOT NULL,
    is_active BOOLEAN NULL,
    created_at TIMESTAMP NULL,
    full_name VARCHAR(200) NULL,
    oab_number VARCHAR(50) NULL,
    phone VARCHAR(20) NULL,
    nationality VARCHAR(50) NULL,
    cep VARCHAR(10) NULL,
    street VARCHAR(200) NULL,
    number VARCHAR(20) NULL,
    uf VARCHAR(2) NULL,
    city VARCHAR(100) NULL,
    neighborhood VARCHAR(100) NULL,
    complement VARCHAR(200) NULL,
    logo_filename VARCHAR(200) NULL,
    billing_status VARCHAR(20) NULL,
    quick_actions TEXT NULL,
    password_changed_at TIMESTAMP NULL,
    password_expires_at TIMESTAMP NULL,
    password_history TEXT NULL,
    force_password_change BOOLEAN NULL,
    specialties TEXT NULL,
    trial_start_date TIMESTAMP NULL,
    trial_days INTEGER NULL,
    trial_active BOOLEAN NULL,
    timezone VARCHAR(50) NULL,
    two_factor_enabled BOOLEAN NULL,
    two_factor_method VARCHAR(20) NULL,
    totp_secret VARCHAR(32) NULL,
    two_factor_backup_codes TEXT NULL,
    two_factor_last_used TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS petition_models (
    id INTEGER NOT NULL DEFAULT nextval('petition_models_id_seq'::regclass) PRIMARY KEY,
    name VARCHAR(180) NOT NULL,
    slug VARCHAR(80) NOT NULL,
    description TEXT NULL,
    petition_type_id INTEGER NOT NULL,
    is_active BOOLEAN NULL DEFAULT true,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    use_dynamic_form BOOLEAN NULL DEFAULT true,
    default_template_id INTEGER NULL,
    created_by INTEGER NULL,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    template_content TEXT NULL
);

CREATE TABLE IF NOT EXISTS petition_model_sections (
    id INTEGER NOT NULL DEFAULT nextval('petition_model_sections_id_seq'::regclass) PRIMARY KEY,
    petition_model_id INTEGER NOT NULL,
    section_id INTEGER NOT NULL,
    order INTEGER NULL DEFAULT 0,
    is_required BOOLEAN NULL DEFAULT false,
    is_expanded BOOLEAN NULL DEFAULT true,
    field_overrides JSON NULL DEFAULT '{}'::json
);

CREATE TABLE IF NOT EXISTS saved_petitions (
    id INTEGER NOT NULL DEFAULT nextval('saved_petitions_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    petition_type_id INTEGER NOT NULL,
    title VARCHAR(300) NULL,
    process_number VARCHAR(30) NULL,
    status VARCHAR(20) NULL,
    form_data JSON NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    cancelled_at TIMESTAMP NULL,
    petition_model_id INTEGER NULL
);

CREATE TABLE IF NOT EXISTS processes (
    id INTEGER NOT NULL DEFAULT nextval('processes_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    process_number VARCHAR(30) NULL,
    title VARCHAR(300) NOT NULL,
    court VARCHAR(100) NULL,
    court_instance VARCHAR(100) NULL,
    jurisdiction VARCHAR(100) NULL,
    district VARCHAR(100) NULL,
    judge VARCHAR(200) NULL,
    plaintiff VARCHAR(300) NULL,
    defendant VARCHAR(300) NULL,
    status VARCHAR(50) NULL,
    distribution_date DATE NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    client_id INTEGER NULL,
    next_deadline DATE NULL,
    deadline_description VARCHAR(300) NULL,
    priority VARCHAR(20) NULL
);

CREATE TABLE IF NOT EXISTS process_notifications (
    id INTEGER NOT NULL DEFAULT nextval('process_notifications_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    process_id INTEGER NULL,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN NULL,
    read_at TIMESTAMP NULL,
    created_at TIMESTAMP NULL,
    sent_at TIMESTAMP NULL,
    extra_data JSON NULL
);

CREATE TABLE IF NOT EXISTS process_petitions (
    process_id INTEGER NOT NULL PRIMARY KEY,
    petition_id INTEGER NOT NULL PRIMARY KEY,
    created_at TIMESTAMP NULL,
    relation_type VARCHAR(50) NULL
);

CREATE TABLE IF NOT EXISTS process_movements (
    id INTEGER NOT NULL DEFAULT nextval('process_movements_id_seq'::regclass) PRIMARY KEY,
    process_id INTEGER NOT NULL,
    movement_date TIMESTAMP NOT NULL,
    description TEXT NOT NULL,
    movement_type VARCHAR(100) NULL,
    court_decision TEXT NULL,
    deadline_extension DATE NULL,
    responsible_party VARCHAR(200) NULL,
    document_url VARCHAR(500) NULL,
    internal_notes TEXT NULL,
    is_important BOOLEAN NULL,
    requires_action BOOLEAN NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS process_costs (
    id INTEGER NOT NULL DEFAULT nextval('process_costs_id_seq'::regclass) PRIMARY KEY,
    process_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    cost_type VARCHAR(50) NOT NULL,
    description VARCHAR(300) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NULL,
    payment_status VARCHAR(20) NULL,
    due_date DATE NULL,
    payment_date DATE NULL,
    court_fee_type VARCHAR(100) NULL,
    attorney_fee_type VARCHAR(100) NULL,
    receipt_url VARCHAR(500) NULL,
    invoice_number VARCHAR(100) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS process_attachments (
    id INTEGER NOT NULL DEFAULT nextval('process_attachments_id_seq'::regclass) PRIMARY KEY,
    process_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NULL,
    file_type VARCHAR(100) NULL,
    file_extension VARCHAR(10) NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT NULL,
    document_type VARCHAR(100) NULL,
    movement_id INTEGER NULL,
    version INTEGER NULL,
    parent_attachment_id INTEGER NULL,
    is_latest_version BOOLEAN NULL,
    is_confidential BOOLEAN NULL,
    is_visible_to_client BOOLEAN NULL,
    status VARCHAR(20) NULL,
    tags VARCHAR(500) NULL,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    last_accessed_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER NOT NULL DEFAULT nextval('calendar_events_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT NULL,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NOT NULL,
    all_day BOOLEAN NULL DEFAULT false,
    location VARCHAR(300) NULL,
    virtual_link VARCHAR(500) NULL,
    event_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NULL DEFAULT 'normal'::character varying,
    process_id INTEGER NULL,
    client_id INTEGER NULL,
    status VARCHAR(20) NULL DEFAULT 'scheduled'::character varying,
    reminder_sent BOOLEAN NULL DEFAULT false,
    reminder_minutes_before INTEGER NULL DEFAULT 60,
    is_recurring BOOLEAN NULL DEFAULT false,
    recurrence_rule VARCHAR(200) NULL,
    recurrence_end_date DATE NULL,
    participants TEXT NULL,
    attendees TEXT NULL,
    notes TEXT NULL,
    outcome TEXT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS process_automations (
    id INTEGER NOT NULL DEFAULT nextval('process_automations_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NULL DEFAULT true,
    trigger_type VARCHAR(50) NOT NULL,
    trigger_condition JSON NULL DEFAULT '{}'::json,
    action_type VARCHAR(50) NOT NULL,
    action_config JSON NULL DEFAULT '{}'::json,
    applies_to_all_processes BOOLEAN NULL DEFAULT false,
    specific_processes TEXT NULL,
    process_types TEXT NULL,
    execution_count INTEGER NULL DEFAULT 0,
    last_executed_at TIMESTAMP NULL,
    success_count INTEGER NULL DEFAULT 0,
    failure_count INTEGER NULL DEFAULT 0,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS process_reports (
    id INTEGER NOT NULL DEFAULT nextval('process_reports_id_seq'::regclass) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    filters JSON NULL DEFAULT '{}'::json,
    report_data JSON NULL DEFAULT '{}'::json,
    total_processes INTEGER NULL DEFAULT 0,
    active_processes INTEGER NULL DEFAULT 0,
    completed_processes INTEGER NULL DEFAULT 0,
    total_costs NUMERIC(12, 2) NULL DEFAULT 0.00,
    average_resolution_time INTEGER NULL,
    status VARCHAR(20) NULL DEFAULT 'generating'::character varying,
    error_message TEXT NULL,
    file_path VARCHAR(500) NULL,
    file_size INTEGER NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER NOT NULL DEFAULT nextval('audit_log_id_seq'::regclass) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    user_id INTEGER NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_values TEXT NULL,
    new_values TEXT NULL,
    changed_fields TEXT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    session_id VARCHAR(255) NULL,
    description TEXT NULL,
    additional_metadata TEXT NULL
);

