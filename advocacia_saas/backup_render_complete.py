#!/usr/bin/env python
"""
Backup COMPLETO de dados da producao (Render) para local
Inclui todas as tabelas com dados
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def backup_render_complete():
    """Conecta ao Render, faz backup COMPLETO de todos os dados e salva localmente"""
    
    render_db_url = os.environ.get("DATABASE_URL")
    
    if not render_db_url:
        print("[ERR] DATABASE_URL not found in .env")
        return False
    
    print("[BACKUP] Conectando ao Render para backup COMPLETO...")
    print(f"[INFO] Database: {render_db_url[:50]}...")
    
    try:
        from app import create_app, db
        from app.models import (
            User, RoadmapItem, BillingPlan, UserPlan, 
            RoadmapCategory, RoadmapFeedback,
            PetitionType, PetitionSection, PetitionModel,
            PetitionModelSection, AuditLog
        )
        
        # Criar app com DB do Render
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = render_db_url
        
        with app.app_context():
            db.create_engine(render_db_url)
            
            # Estrutura do backup
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'render_db_url_prefix': render_db_url[:30],
                
                # Tabelas principais
                'users': [],
                'billing_plans': [],
                'user_plans': [],
                
                # Roadmap
                'roadmap_categories': [],
                'roadmap_items': [],
                'roadmap_feedback': [],
                
                # Peticoes
                'petition_types': [],
                'petition_sections': [],
                'petition_models': [],
                'petition_model_sections': [],
                'petition_type_sections': [],
                
                # Auditoria
                'audit_logs': [],
                
                'summary': {}
            }
            
            print("\n[BACKUP] Iniciando backup de tabelas...")
            print("=" * 70)
            
            # Users
            print("[1/12] Users...")
            users = User.query.all()
            for user in users:
                backup_data['users'].append({
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_admin': user.is_admin,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                })
            print(f"  [OK] {len(users)} usuarios")
            
            # Plans
            print("[2/12] Billing Plans...")
            plans = BillingPlan.query.all()
            for plan in plans:
                backup_data['billing_plans'].append({
                    'id': plan.id,
                    'name': plan.name,
                    'monthly_fee': float(plan.monthly_fee),
                    'plan_type': plan.plan_type,
                    'votes_per_period': plan.votes_per_period,
                    'created_at': plan.created_at.isoformat() if plan.created_at else None,
                })
            print(f"  [OK] {len(plans)} planos")
            
            # User Plans
            print("[3/12] User Plans...")
            user_plans = UserPlan.query.all()
            for up in user_plans:
                backup_data['user_plans'].append({
                    'id': up.id,
                    'user_id': up.user_id,
                    'plan_id': up.plan_id,
                    'status': up.status,
                    'started_at': up.started_at.isoformat() if up.started_at else None,
                    'renewal_date': up.renewal_date.isoformat() if up.renewal_date else None,
                    'is_current': up.is_current,
                })
            print(f"  [OK] {len(user_plans)} user plans")
            
            # Roadmap Categories
            print("[4/12] Roadmap Categories...")
            categories = RoadmapCategory.query.all()
            for cat in categories:
                backup_data['roadmap_categories'].append({
                    'id': cat.id,
                    'name': cat.name,
                    'slug': cat.slug,
                    'description': cat.description,
                    'icon': cat.icon,
                    'color': cat.color,
                    'order': cat.order,
                })
            print(f"  [OK] {len(categories)} categorias")
            
            # Roadmap Items
            print("[5/12] Roadmap Items...")
            items = RoadmapItem.query.all()
            for item in items:
                backup_data['roadmap_items'].append({
                    'id': item.id,
                    'title': item.title,
                    'description': item.description,
                    'detailed_description': item.detailed_description,
                    'slug': item.slug,
                    'status': item.status,
                    'priority': item.priority,
                    'estimated_effort': item.estimated_effort,
                    'category_id': item.category_id,
                    'show_new_badge': item.show_new_badge,
                    'planned_completion_date': item.planned_completion_date.isoformat() if item.planned_completion_date else None,
                    'actual_completion_date': item.actual_completion_date.isoformat() if item.actual_completion_date else None,
                })
            print(f"  [OK] {len(items)} roadmap items")
            
            # Roadmap Feedback
            print("[6/12] Roadmap Feedback...")
            feedback = RoadmapFeedback.query.all()
            for fb in feedback:
                backup_data['roadmap_feedback'].append({
                    'id': fb.id,
                    'user_id': fb.user_id,
                    'roadmap_item_id': fb.roadmap_item_id,
                    'rating': fb.rating,
                    'comment': fb.comment,
                    'created_at': fb.created_at.isoformat() if fb.created_at else None,
                })
            print(f"  [OK] {len(feedback)} feedbacks")
            
            # Petition Types
            print("[7/12] Petition Types...")
            petition_types = PetitionType.query.all()
            for pt in petition_types:
                backup_data['petition_types'].append({
                    'id': pt.id,
                    'name': pt.name,
                    'slug': pt.slug,
                    'description': pt.description,
                    'icon': pt.icon if hasattr(pt, 'icon') else None,
                })
            print(f"  [OK] {len(petition_types)} tipos de peticao")
            
            # Petition Sections
            print("[8/12] Petition Sections...")
            petition_sections = PetitionSection.query.all()
            for ps in petition_sections:
                backup_data['petition_sections'].append({
                    'id': ps.id,
                    'name': ps.name,
                    'slug': ps.slug,
                    'description': ps.description,
                    'order': ps.order if hasattr(ps, 'order') else 0,
                })
            print(f"  [OK] {len(petition_sections)} secoes")
            
            # Petition Models
            print("[9/12] Petition Models...")
            models = PetitionModel.query.all()
            for model in models:
                backup_data['petition_models'].append({
                    'id': model.id,
                    'name': model.name,
                    'slug': model.slug,
                    'description': model.description,
                    'petition_type_id': model.petition_type_id,
                    'template_content': model.template_content,
                })
            print(f"  [OK] {len(models)} modelos de peticao")
            
            # Petition Type Sections
            print("[10/12] Petition Type Sections...")
            try:
                from app.models import petition_type_sections
                result = db.session.execute(db.select(petition_type_sections))
                rows = result.fetchall()
                petition_type_section_data = []
                for row in rows:
                    petition_type_section_data.append({
                        'petition_type_id': row[0],
                        'petition_section_id': row[1],
                    })
                backup_data['petition_type_sections'] = petition_type_section_data
                print(f"  [OK] {len(petition_type_section_data)} associacoes")
            except Exception as e:
                print(f"  [WARN] Erro ao backup: {str(e)[:30]}")
                backup_data['petition_type_sections'] = []
            
            # Petition Model Sections
            print("[11/12] Petition Model Sections...")
            try:
                from app.models import petition_model_sections
                result = db.session.execute(db.select(petition_model_sections))
                rows = result.fetchall()
                model_section_data = []
                for row in rows:
                    model_section_data.append({
                        'petition_model_id': row[0],
                        'petition_section_id': row[1],
                    })
                backup_data['petition_model_sections'] = model_section_data
                print(f"  [OK] {len(model_section_data)} associacoes")
            except Exception as e:
                print(f"  [WARN] Erro ao backup: {str(e)[:30]}")
                backup_data['petition_model_sections'] = []
            
            # Audit Logs
            print("[12/12] Audit Logs...")
            logs = AuditLog.query.all()
            for log in logs:
                backup_data['audit_logs'].append({
                    'id': log.id,
                    'user_id': log.user_id if hasattr(log, 'user_id') else None,
                    'action': log.action if hasattr(log, 'action') else None,
                    'details': log.details if hasattr(log, 'details') else None,
                    'created_at': log.created_at.isoformat() if hasattr(log, 'created_at') and log.created_at else None,
                })
            print(f"  [OK] {len(logs)} registros de auditoria")
            
            # Summary
            print("=" * 70)
            backup_data['summary'] = {
                'users': len(backup_data['users']),
                'billing_plans': len(backup_data['billing_plans']),
                'user_plans': len(backup_data['user_plans']),
                'roadmap_categories': len(backup_data['roadmap_categories']),
                'roadmap_items': len(backup_data['roadmap_items']),
                'roadmap_feedback': len(backup_data['roadmap_feedback']),
                'petition_types': len(backup_data['petition_types']),
                'petition_sections': len(backup_data['petition_sections']),
                'petition_models': len(backup_data['petition_models']),
                'petition_type_sections': len(backup_data['petition_type_sections']),
                'petition_model_sections': len(backup_data['petition_model_sections']),
                'audit_logs': len(backup_data['audit_logs']),
                'total_records': sum([
                    len(backup_data['users']),
                    len(backup_data['billing_plans']),
                    len(backup_data['user_plans']),
                    len(backup_data['roadmap_categories']),
                    len(backup_data['roadmap_items']),
                    len(backup_data['roadmap_feedback']),
                    len(backup_data['petition_types']),
                    len(backup_data['petition_sections']),
                    len(backup_data['petition_models']),
                    len(backup_data['petition_type_sections']),
                    len(backup_data['petition_model_sections']),
                    len(backup_data['audit_logs']),
                ])
            }
            
            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_render_complete_{timestamp}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n[OK] Backup criado: {backup_file}")
            print(f"\nResumo do backup:")
            for key, value in backup_data['summary'].items():
                if key != 'total_records':
                    print(f"  - {key}: {value}")
            print(f"  - TOTAL: {backup_data['summary']['total_records']} registros")
            
            return True
            
    except Exception as e:
        print(f"[ERR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    backup_render_complete()
