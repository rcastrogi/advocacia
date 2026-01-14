"""baseline_20260114 - Estado atual do banco Render

Revision ID: baseline_20260114
Revises: 
Create Date: 2026-01-14

Esta migration representa o estado atual do banco de dados no Render.
Todas as 67 tabelas já existem no banco, então não executamos nenhuma operação.

Tabelas existentes:
- agenda_blocks, ai_generation_feedback, ai_generations, anonymization_requests
- audit_log, billing_plans, calendar_events, chat_rooms, cidades, client
- client_lawyers, credit_packages, credit_transactions, data_consents
- data_processing_logs, deadlines, deanonymization_requests, deletion_requests
- dependent, documents, estados, expenses, features, invoices, messages
- notification_preferences, notification_queue, notifications, office_invites
- offices, payments, petition_attachments, petition_balance_transactions
- petition_model_sections, petition_models, petition_sections, petition_templates
- petition_type_sections, petition_types, petition_usage, plan_features
- plan_petition_types, process_attachments, process_automations, process_costs
- process_movements, process_notifications, process_petitions, process_reports
- processes, promo_coupons, referral_codes, referrals, roadmap_categories
- roadmap_feedback, roadmap_items, roadmap_vote_quotas, roadmap_votes
- saved_petitions, subscriptions, table_preferences, template_examples
- testimonials, user, user_credits, user_petition_balance, user_plans
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'baseline_20260114'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Esta é uma migration baseline - todas as tabelas já existem no banco Render
    # Não executamos nenhuma operação aqui
    pass


def downgrade():
    # Não implementamos downgrade para baseline
    # Isso destruiria todo o banco de dados
    pass
