#!/usr/bin/env python
"""
Backup de dados da produção (Render) para local
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def backup_render_to_local():
    """Conecta ao Render, faz backup dos dados principais e salva localmente"""
    
    # Conectar ao Render
    render_db_url = os.environ.get("DATABASE_URL")
    
    if not render_db_url:
        print("[ERR] DATABASE_URL not found in .env")
        return False
    
    print("[BACKUP] Conectando ao Render...")
    print(f"[INFO] Database: {render_db_url[:50]}...")
    
    try:
        from app import create_app, db
        from app.models import (
            User, RoadmapItem, BillingPlan, UserPlan, 
            RoadmapCategory, RoadmapFeedback
        )
        
        # Criar app com DB do Render
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = render_db_url
        
        with app.app_context():
            # Reconectar para garantir que usa Render
            db.create_engine(render_db_url)
            
            # Backup de dados principais
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'roadmap_items': [],
                'roadmap_categories': [],
                'users': [],
                'billing_plans': [],
                'roadmap_feedback': []
            }
            
            # Roadmap Items
            print("[BACKUP] Copiando Roadmap Items...")
            items = RoadmapItem.query.all()
            for item in items:
                backup_data['roadmap_items'].append({
                    'id': item.id,
                    'title': item.title,
                    'description': item.description,
                    'status': item.status,
                    'priority': item.priority,
                    'estimated_effort': getattr(item, 'estimated_effort', 'medium'),
                    'category_id': item.category_id,
                    'slug': item.slug,
                    'is_implemented': getattr(item, 'is_implemented', False),
                    'show_new_badge': getattr(item, 'show_new_badge', False),
                    'planned_completion_date': item.planned_completion_date.isoformat() if item.planned_completion_date else None,
                    'actual_completion_date': item.actual_completion_date.isoformat() if item.actual_completion_date else None,
                })
            print(f"[OK] {len(items)} items copiados")
            
            # Roadmap Categories
            print("[BACKUP] Copiando Roadmap Categories...")
            categories = RoadmapCategory.query.all()
            for cat in categories:
                backup_data['roadmap_categories'].append({
                    'id': cat.id,
                    'name': cat.name,
                    'slug': getattr(cat, 'slug', cat.name.lower().replace(' ', '-')),
                    'description': cat.description,
                    'icon': cat.icon,
                    'color': cat.color,
                    'order': cat.order,
                })
            print(f"[OK] {len(categories)} categorias copiadas")
            
            # Billing Plans
            print("[BACKUP] Copiando Billing Plans...")
            plans = BillingPlan.query.all()
            for plan in plans:
                backup_data['billing_plans'].append({
                    'id': plan.id,
                    'name': plan.name,
                    'monthly_fee': float(getattr(plan, 'monthly_fee', 0)),
                    'plan_type': plan.plan_type,
                    'votes_per_period': getattr(plan, 'votes_per_period', 0),
                })
            print(f"[OK] {len(plans)} planos copiados")
            
            # Users (apenas dados públicos)
            print("[BACKUP] Copiando Users...")
            users = User.query.all()
            for user in users:
                backup_data['users'].append({
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_active': user.is_active,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                })
            print(f"[OK] {len(users)} usuários copiados")
            
            # Roadmap Feedback
            print("[BACKUP] Copiando Roadmap Feedback...")
            feedback = RoadmapFeedback.query.all()
            for fb in feedback:
                backup_data['roadmap_feedback'].append({
                    'id': fb.id,
                    'roadmap_item_id': fb.roadmap_item_id,
                    'user_id': fb.user_id,
                    'title': fb.title,
                    'description': fb.description,
                    'created_at': fb.created_at.isoformat() if fb.created_at else None,
                })
            print(f"[OK] {len(feedback)} feedbacks copiados")
            
            # Salvar backup em arquivo
            backup_file = f"backup_render_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n[OK] Backup salvo em: {backup_file}")
            print(f"[OK] Total de dados:")
            print(f"   - {len(backup_data['roadmap_items'])} roadmap items")
            print(f"   - {len(backup_data['roadmap_categories'])} categorias")
            print(f"   - {len(backup_data['billing_plans'])} planos")
            print(f"   - {len(backup_data['users'])} usuários")
            print(f"   - {len(backup_data['roadmap_feedback'])} feedbacks")
            
            return True
            
    except Exception as e:
        print(f"[ERR] Erro ao fazer backup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    success = backup_render_to_local()
    sys.exit(0 if success else 1)
