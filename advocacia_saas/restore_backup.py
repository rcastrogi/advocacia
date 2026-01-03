#!/usr/bin/env python
"""
Restaurar backup do Render no banco local
"""

import json
import sys
from datetime import datetime

def restore_backup(backup_file):
    """Restaura dados do backup no banco local"""
    
    print(f"[RESTORE] Lendo backup: {backup_file}")
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        print(f"[INFO] Backup de: {backup_data.get('timestamp')}")
        
        from app import create_app, db
        from app.models import (
            User, RoadmapItem, BillingPlan, UserPlan,
            RoadmapCategory, RoadmapFeedback
        )
        
        app = create_app()
        
        with app.app_context():
            # Restaurar categorias
            print("\n[RESTORE] Restaurando Roadmap Categories...")
            for cat_data in backup_data.get('roadmap_categories', []):
                cat = RoadmapCategory.query.filter_by(id=cat_data['id']).first()
                if not cat:
                    cat = RoadmapCategory(id=cat_data['id'])
                
                cat.name = cat_data['name']
                cat.slug = cat_data.get('slug', cat_data['name'].lower().replace(' ', '-'))
                cat.description = cat_data['description']
                cat.icon = cat_data['icon']
                cat.color = cat_data['color']
                cat.order = cat_data.get('order', 0)
                db.session.add(cat)
            db.session.commit()
            print(f"[OK] {len(backup_data.get('roadmap_categories', []))} categorias restauradas")
            
            # Restaurar planos
            print("[RESTORE] Restaurando Billing Plans...")
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
            print(f"[OK] {len(backup_data.get('billing_plans', []))} planos restaurados")
            
            # Restaurar roadmap items
            print("[RESTORE] Restaurando Roadmap Items...")
            for item_data in backup_data.get('roadmap_items', []):
                # Update if exists, else insert
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
            print(f"[OK] {len(backup_data.get('roadmap_items', []))} items restaurados")
            
            # Restaurar usuários
            print("[RESTORE] Restaurando Users...")
            for user_data in backup_data.get('users', []):
                user = User.query.filter_by(id=user_data['id']).first()
                if not user:
                    user = User(id=user_data['id'])
                
                user.email = user_data['email']
                user.username = user_data['username']
                user.full_name = user_data['full_name']
                user.is_active = user_data['is_active']
                db.session.add(user)
            db.session.commit()
            print(f"[OK] {len(backup_data.get('users', []))} usuários restaurados")
            
            print("\n[OK] Restauração completa!")
            print(f"[OK] Total restaurado:")
            print(f"   - {len(backup_data.get('roadmap_items', []))} roadmap items")
            print(f"   - {len(backup_data.get('roadmap_categories', []))} categorias")
            print(f"   - {len(backup_data.get('billing_plans', []))} planos")
            print(f"   - {len(backup_data.get('users', []))} usuários")
            
            return True
        
    except FileNotFoundError:
        print(f"[ERR] Arquivo não encontrado: {backup_file}")
        return False
    except Exception as e:
        print(f"[ERR] Erro ao restaurar: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python restore_backup.py <backup_file>")
        print("\nExemplo:")
        print("  python restore_backup.py backup_render_20260103_015327.json")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    success = restore_backup(backup_file)
    sys.exit(0 if success else 1)
