#!/usr/bin/env python
"""
Restaurar backup COMPLETO do Render no banco local
"""

import json
import sys
from datetime import datetime

def restore_backup_complete(backup_file):
    """Restaura dados COMPLETOS do backup no banco local"""
    
    print(f"[RESTORE] Lendo backup: {backup_file}")
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        print(f"[INFO] Backup de: {backup_data.get('timestamp')}")
        
        from app import create_app, db
        from app.models import (
            User, RoadmapItem, BillingPlan, UserPlan,
            RoadmapCategory, RoadmapFeedback,
            PetitionType, PetitionSection, PetitionModel,
            PetitionModelSection, AuditLog
        )
        
        app = create_app()
        
        with app.app_context():
            print("\n[RESTORE] Restaurando dados...")
            print("=" * 70)
            
            # Restaurar usuarios
            print("[1/12] Users...")
            for user_data in backup_data.get('users', []):
                user = User.query.filter_by(id=user_data['id']).first()
                if not user:
                    user = User(id=user_data['id'])
                
                user.email = user_data['email']
                user.username = user_data['username']
                user.full_name = user_data['full_name']
                user.is_admin = user_data.get('is_admin', False)
                db.session.add(user)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('users', []))} usuarios")
            
            # Restaurar planos
            print("[2/12] Billing Plans...")
            for plan_data in backup_data.get('billing_plans', []):
                plan = BillingPlan.query.filter_by(id=plan_data['id']).first()
                if not plan:
                    plan = BillingPlan(id=plan_data['id'])
                
                plan.name = plan_data['name']
                plan.monthly_fee = plan_data['monthly_fee']
                plan.plan_type = plan_data.get('plan_type', 'per_usage')
                plan.votes_per_period = plan_data.get('votes_per_period', 0)
                db.session.add(plan)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('billing_plans', []))} planos")
            
            # Restaurar user plans
            print("[3/12] User Plans...")
            for up_data in backup_data.get('user_plans', []):
                up = UserPlan.query.filter_by(id=up_data['id']).first()
                if not up:
                    up = UserPlan(id=up_data['id'])
                
                up.user_id = up_data['user_id']
                up.plan_id = up_data['plan_id']
                up.status = up_data.get('status', 'active')
                up.is_current = up_data.get('is_current', True)
                if up_data.get('started_at'):
                    up.started_at = datetime.fromisoformat(up_data['started_at'])
                if up_data.get('renewal_date'):
                    up.renewal_date = datetime.fromisoformat(up_data['renewal_date'])
                db.session.add(up)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('user_plans', []))} user plans")
            
            # Restaurar categorias roadmap
            print("[4/12] Roadmap Categories...")
            for cat_data in backup_data.get('roadmap_categories', []):
                cat = RoadmapCategory.query.filter_by(id=cat_data['id']).first()
                if not cat:
                    cat = RoadmapCategory(id=cat_data['id'])
                
                cat.name = cat_data['name']
                cat.slug = cat_data.get('slug', cat_data['name'].lower().replace(' ', '-'))
                cat.description = cat_data.get('description')
                cat.icon = cat_data.get('icon')
                cat.color = cat_data.get('color')
                cat.order = cat_data.get('order', 0)
                db.session.add(cat)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('roadmap_categories', []))} categorias")
            
            # Restaurar roadmap items
            print("[5/12] Roadmap Items...")
            for item_data in backup_data.get('roadmap_items', []):
                item = RoadmapItem.query.filter_by(id=item_data['id']).first()
                if not item:
                    item = RoadmapItem(id=item_data['id'])
                
                item.title = item_data['title']
                item.description = item_data['description']
                item.slug = item_data['slug']
                item.status = item_data['status']
                item.priority = item_data['priority']
                item.estimated_effort = item_data.get('estimated_effort', 'medium')
                item.category_id = item_data['category_id']
                item.show_new_badge = item_data.get('show_new_badge', False)
                item.detailed_description = item_data.get('detailed_description')
                
                if item_data.get('planned_completion_date'):
                    item.planned_completion_date = datetime.fromisoformat(
                        item_data['planned_completion_date']
                    ).date()
                
                if item_data.get('actual_completion_date'):
                    item.actual_completion_date = datetime.fromisoformat(
                        item_data['actual_completion_date']
                    ).date()
                
                db.session.add(item)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('roadmap_items', []))} roadmap items")
            
            # Restaurar roadmap feedback
            print("[6/12] Roadmap Feedback...")
            for fb_data in backup_data.get('roadmap_feedback', []):
                fb = RoadmapFeedback.query.filter_by(id=fb_data['id']).first()
                if not fb:
                    fb = RoadmapFeedback(id=fb_data['id'])
                
                fb.user_id = fb_data['user_id']
                fb.roadmap_item_id = fb_data['roadmap_item_id']
                fb.rating = fb_data.get('rating')
                fb.comment = fb_data.get('comment')
                db.session.add(fb)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('roadmap_feedback', []))} feedbacks")
            
            # Restaurar tipos de peticao
            print("[7/12] Petition Types...")
            for pt_data in backup_data.get('petition_types', []):
                pt = PetitionType.query.filter_by(id=pt_data['id']).first()
                if not pt:
                    pt = PetitionType(id=pt_data['id'])
                
                pt.name = pt_data['name']
                pt.slug = pt_data['slug']
                pt.description = pt_data.get('description')
                if pt_data.get('icon'):
                    pt.icon = pt_data['icon']
                db.session.add(pt)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('petition_types', []))} tipos de peticao")
            
            # Restaurar secoes de peticao
            print("[8/12] Petition Sections...")
            for ps_data in backup_data.get('petition_sections', []):
                ps = PetitionSection.query.filter_by(id=ps_data['id']).first()
                if not ps:
                    ps = PetitionSection(id=ps_data['id'])
                
                ps.name = ps_data['name']
                ps.slug = ps_data['slug']
                ps.description = ps_data.get('description')
                if ps_data.get('order'):
                    ps.order = ps_data['order']
                db.session.add(ps)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('petition_sections', []))} secoes")
            
            # Restaurar modelos de peticao
            print("[9/12] Petition Models...")
            for model_data in backup_data.get('petition_models', []):
                model = PetitionModel.query.filter_by(id=model_data['id']).first()
                if not model:
                    model = PetitionModel(id=model_data['id'])
                
                model.name = model_data['name']
                model.slug = model_data['slug']
                model.description = model_data.get('description')
                model.petition_type_id = model_data.get('petition_type_id')
                model.template_content = model_data.get('template_content')
                db.session.add(model)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('petition_models', []))} modelos")
            
            # Restaurar petition type sections
            print("[10/12] Petition Type Sections...")
            pts_count = len(backup_data.get('petition_type_sections', []))
            try:
                from app.models import petition_type_sections
                for pts_data in backup_data.get('petition_type_sections', []):
                    # Insert via raw SQL para association table
                    db.session.execute(db.text(
                        f"INSERT OR IGNORE INTO petition_type_sections "
                        f"(petition_type_id, petition_section_id) "
                        f"VALUES ({pts_data['petition_type_id']}, {pts_data['petition_section_id']})"
                    ))
                db.session.commit()
                print(f"  [OK] {pts_count} associacoes")
            except Exception as e:
                print(f"  [WARN] Erro ao restaurar: {str(e)[:40]}")
            
            # Restaurar petition model sections
            print("[11/12] Petition Model Sections...")
            pms_count = len(backup_data.get('petition_model_sections', []))
            try:
                from app.models import petition_model_sections
                for pms_data in backup_data.get('petition_model_sections', []):
                    # Insert via raw SQL para association table
                    db.session.execute(db.text(
                        f"INSERT OR IGNORE INTO petition_model_sections "
                        f"(petition_model_id, petition_section_id) "
                        f"VALUES ({pms_data['petition_model_id']}, {pms_data['petition_section_id']})"
                    ))
                db.session.commit()
                print(f"  [OK] {pms_count} associacoes")
            except Exception as e:
                print(f"  [WARN] Erro ao restaurar: {str(e)[:40]}")
            
            # Restaurar audit logs
            print("[12/12] Audit Logs...")
            for log_data in backup_data.get('audit_logs', []):
                log = AuditLog.query.filter_by(id=log_data['id']).first()
                if not log:
                    log = AuditLog(id=log_data['id'])
                
                if log_data.get('user_id'):
                    log.user_id = log_data['user_id']
                if log_data.get('action'):
                    log.action = log_data['action']
                if log_data.get('details'):
                    log.details = log_data['details']
                db.session.add(log)
            db.session.commit()
            print(f"  [OK] {len(backup_data.get('audit_logs', []))} registros de auditoria")
            
            # Resumo
            print("=" * 70)
            print(f"\n[OK] Restauracao completa!")
            print(f"\n[RESUMO] Total restaurado:")
            for key, value in backup_data.get('summary', {}).items():
                if key != 'total_records':
                    print(f"  - {key}: {value}")
            print(f"  - TOTAL: {backup_data.get('summary', {}).get('total_records', 0)} registros")
            
            return True
            
    except Exception as e:
        print(f"[ERR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python restore_backup_complete.py <arquivo_backup.json>")
        print("Exemplo: python restore_backup_complete.py backup_render_complete_20260103_020213.json")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    restore_backup_complete(backup_file)
