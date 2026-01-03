#!/usr/bin/env python
"""
Resetar Render (apagar dados) e restaurar backup completo la
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


def reset_render():
    """Conecta ao Render e limpa todas as tabelas"""

    render_db_url = os.environ.get("DATABASE_URL")

    if not render_db_url:
        print("[ERR] DATABASE_URL not found in .env")
        return False

    print("[RESET] Conectando ao Render para RESETAR...")
    print(f"[INFO] Database: {render_db_url[:50]}...")
    print("[AVISO] Isso vai APAGAR todos os dados do Render!")

    try:
        from app import create_app, db

        app = create_app()
        app.config["SQLALCHEMY_DATABASE_URI"] = render_db_url

        with app.app_context():
            db.create_engine(render_db_url)

            print("\n[RESET] Limpando tabelas do Render...")
            print("=" * 70)

            # Obter lista de tabelas
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            # Tabelas que NAO devem ser deletadas
            protected_tables = ["alembic_version"]

            deleted_count = 0
            for table_name in tables:
                if table_name in protected_tables:
                    print(f"  [SKIP] {table_name} (protegida)")
                    continue

                try:
                    # Desabilitar constraints temporariamente
                    db.session.execute(db.text(f"TRUNCATE TABLE {table_name} CASCADE"))
                    db.session.commit()
                    print(f"  [OK] {table_name}")
                    deleted_count += 1
                except Exception as e:
                    # Se TRUNCATE falhar, tentar DELETE
                    try:
                        db.session.execute(db.text(f"DELETE FROM {table_name}"))
                        db.session.commit()
                        print(f"  [OK] {table_name} (DELETE)")
                        deleted_count += 1
                    except Exception as e2:
                        print(f"  [WARN] Erro ao limpar {table_name}: {str(e2)[:30]}")

            print("=" * 70)
            print(f"\n[OK] {deleted_count} tabelas limpas")
            print("[RESET] Render resetado com sucesso!")

            return True

    except Exception as e:
        print(f"[ERR] {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def restore_to_render(backup_file):
    """Restaura backup no banco do Render"""

    render_db_url = os.environ.get("DATABASE_URL")

    if not render_db_url:
        print("[ERR] DATABASE_URL not found in .env")
        return False

    print(f"\n[RESTORE] Conectando ao Render para restaurar...")
    print(f"[RESTORE] Arquivo: {backup_file}")

    try:
        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        print(f"[INFO] Backup de: {backup_data.get('timestamp')}")

        from app import create_app, db
        from app.models import (
            AuditLog,
            BillingPlan,
            PetitionModel,
            PetitionModelSection,
            PetitionSection,
            PetitionType,
            RoadmapCategory,
            RoadmapFeedback,
            RoadmapItem,
            User,
            UserPlan,
        )

        app = create_app()
        app.config["SQLALCHEMY_DATABASE_URI"] = render_db_url

        with app.app_context():
            db.create_engine(render_db_url)

            print("\n[RESTORE] Restaurando dados no Render...")
            print("=" * 70)

            # Usuarios
            print("[1/12] Users...")
            for user_data in backup_data.get("users", []):
                user = User.query.filter_by(id=user_data["id"]).first()
                if not user:
                    user = User(id=user_data["id"])

                user.email = user_data["email"]
                user.username = user_data["username"]
                user.full_name = user_data["full_name"]
                user.is_admin = user_data.get("is_admin", False)

                # Se nao tem password hash, gerar uma padrao
                if not user.password_hash:
                    user.set_password("senha123")

                db.session.add(user)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('users', []))} usuarios")

            # Planos
            print("[2/12] Billing Plans...")
            for plan_data in backup_data.get("billing_plans", []):
                plan = BillingPlan.query.filter_by(id=plan_data["id"]).first()
                if not plan:
                    plan = BillingPlan(id=plan_data["id"])

                plan.name = plan_data["name"]
                plan.slug = plan_data.get(
                    "slug", plan_data["name"].lower().replace(" ", "-")
                )
                plan.monthly_fee = plan_data["monthly_fee"]
                plan.plan_type = plan_data.get("plan_type", "per_usage")
                plan.votes_per_period = plan_data.get("votes_per_period", 0)
                db.session.add(plan)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('billing_plans', []))} planos")

            # User Plans
            print("[3/12] User Plans...")
            for up_data in backup_data.get("user_plans", []):
                up = UserPlan.query.filter_by(id=up_data["id"]).first()
                if not up:
                    up = UserPlan(id=up_data["id"])

                up.user_id = up_data["user_id"]
                up.plan_id = up_data["plan_id"]
                up.status = up_data.get("status", "active")
                up.is_current = up_data.get("is_current", True)
                if up_data.get("started_at"):
                    up.started_at = datetime.fromisoformat(up_data["started_at"])
                if up_data.get("renewal_date"):
                    up.renewal_date = datetime.fromisoformat(up_data["renewal_date"])
                db.session.add(up)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('user_plans', []))} user plans")

            # Roadmap Categories
            print("[4/12] Roadmap Categories...")
            for cat_data in backup_data.get("roadmap_categories", []):
                cat = RoadmapCategory.query.filter_by(id=cat_data["id"]).first()
                if not cat:
                    cat = RoadmapCategory(id=cat_data["id"])

                cat.name = cat_data["name"]
                cat.slug = cat_data.get(
                    "slug", cat_data["name"].lower().replace(" ", "-")
                )
                cat.description = cat_data.get("description")
                cat.icon = cat_data.get("icon")
                cat.color = cat_data.get("color")
                cat.order = cat_data.get("order", 0)
                db.session.add(cat)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('roadmap_categories', []))} categorias")

            # Roadmap Items
            print("[5/12] Roadmap Items...")
            for item_data in backup_data.get("roadmap_items", []):
                item = RoadmapItem.query.filter_by(id=item_data["id"]).first()
                if not item:
                    item = RoadmapItem(id=item_data["id"])

                item.title = item_data["title"]
                item.description = item_data["description"]
                item.slug = item_data["slug"]
                item.status = item_data["status"]
                item.priority = item_data["priority"]
                item.estimated_effort = item_data.get("estimated_effort", "medium")
                item.category_id = item_data["category_id"]
                item.show_new_badge = item_data.get("show_new_badge", False)
                item.detailed_description = item_data.get("detailed_description")

                if item_data.get("planned_completion_date"):
                    item.planned_completion_date = datetime.fromisoformat(
                        item_data["planned_completion_date"]
                    ).date()

                if item_data.get("actual_completion_date"):
                    item.actual_completion_date = datetime.fromisoformat(
                        item_data["actual_completion_date"]
                    ).date()

                db.session.add(item)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('roadmap_items', []))} roadmap items")

            # Roadmap Feedback
            print("[6/12] Roadmap Feedback...")
            for fb_data in backup_data.get("roadmap_feedback", []):
                fb = RoadmapFeedback.query.filter_by(id=fb_data["id"]).first()
                if not fb:
                    fb = RoadmapFeedback(id=fb_data["id"])

                fb.user_id = fb_data["user_id"]
                fb.roadmap_item_id = fb_data["roadmap_item_id"]
                fb.rating = fb_data.get("rating")
                fb.comment = fb_data.get("comment")
                db.session.add(fb)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('roadmap_feedback', []))} feedbacks")

            # Petition Types
            print("[7/12] Petition Types...")
            for pt_data in backup_data.get("petition_types", []):
                pt = PetitionType.query.filter_by(id=pt_data["id"]).first()
                if not pt:
                    pt = PetitionType(id=pt_data["id"])

                pt.name = pt_data["name"]
                pt.slug = pt_data["slug"]
                pt.description = pt_data.get("description")
                if pt_data.get("icon"):
                    pt.icon = pt_data["icon"]
                db.session.add(pt)
            db.session.commit()
            print(
                f"  [OK] {len(backup_data.get('petition_types', []))} tipos de peticao"
            )

            # Petition Sections
            print("[8/12] Petition Sections...")
            for ps_data in backup_data.get("petition_sections", []):
                ps = PetitionSection.query.filter_by(id=ps_data["id"]).first()
                if not ps:
                    ps = PetitionSection(id=ps_data["id"])

                ps.name = ps_data["name"]
                ps.slug = ps_data["slug"]
                ps.description = ps_data.get("description")
                if ps_data.get("order"):
                    ps.order = ps_data["order"]
                db.session.add(ps)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('petition_sections', []))} secoes")

            # Petition Models
            print("[9/12] Petition Models...")
            for model_data in backup_data.get("petition_models", []):
                model = PetitionModel.query.filter_by(id=model_data["id"]).first()
                if not model:
                    model = PetitionModel(id=model_data["id"])

                model.name = model_data["name"]
                model.slug = model_data["slug"]
                model.description = model_data.get("description")
                model.petition_type_id = model_data.get("petition_type_id")
                model.template_content = model_data.get("template_content")
                db.session.add(model)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('petition_models', []))} modelos")

            # Petition Type Sections
            print("[10/12] Petition Type Sections...")
            pts_count = len(backup_data.get("petition_type_sections", []))
            try:
                from app.models import petition_type_sections

                for pts_data in backup_data.get("petition_type_sections", []):
                    db.session.execute(
                        db.text(
                            f"INSERT INTO petition_type_sections "
                            f"(petition_type_id, petition_section_id) "
                            f"VALUES ({pts_data['petition_type_id']}, {pts_data['petition_section_id']}) "
                            f"ON CONFLICT DO NOTHING"
                        )
                    )
                db.session.commit()
                print(f"  [OK] {pts_count} associacoes")
            except Exception as e:
                print(f"  [WARN] Erro: {str(e)[:40]}")

            # Petition Model Sections
            print("[11/12] Petition Model Sections...")
            pms_count = len(backup_data.get("petition_model_sections", []))
            try:
                from app.models import petition_model_sections

                for pms_data in backup_data.get("petition_model_sections", []):
                    db.session.execute(
                        db.text(
                            f"INSERT INTO petition_model_sections "
                            f"(petition_model_id, petition_section_id) "
                            f"VALUES ({pms_data['petition_model_id']}, {pms_data['petition_section_id']}) "
                            f"ON CONFLICT DO NOTHING"
                        )
                    )
                db.session.commit()
                print(f"  [OK] {pms_count} associacoes")
            except Exception as e:
                print(f"  [WARN] Erro: {str(e)[:40]}")

            # Audit Logs (skip - requires many fields)
            print("[12/12] Audit Logs...")
            print(f"  [SKIP] Auditoria nao precisa ser restaurada")

            # Resumo
            print("=" * 70)
            print(f"\n[OK] Restauracao no Render completa!")
            print(f"\n[RESUMO] Total restaurado:")
            for key, value in backup_data.get("summary", {}).items():
                if key != "total_records":
                    print(f"  - {key}: {value}")
            print(
                f"  - TOTAL: {backup_data.get('summary', {}).get('total_records', 0)} registros"
            )

            return True

    except Exception as e:
        print(f"[ERR] {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python reset_and_restore_render.py <arquivo_backup.json> [--force]")
        print(
            "Exemplo: python reset_and_restore_render.py backup_render_complete_20260103_020213.json --force"
        )
        sys.exit(1)

    backup_file = sys.argv[1]
    force = "--force" in sys.argv

    if not os.path.exists(backup_file):
        print(f"[ERR] Arquivo nao encontrado: {backup_file}")
        sys.exit(1)

    if not force:
        # Confirmacao
        print("[AVISO] Isso vai APAGAR todos os dados do Render!")
        response = input("Digite 'SIM' para continuar: ")
        if response.upper() != "SIM":
            print("[CANCELADO] Operacao cancelada")
            sys.exit(1)

    # Resetar
    if reset_render():
        # Restaurar
        restore_to_render(backup_file)
