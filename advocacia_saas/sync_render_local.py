#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sincronização Simples - Render ↔ Local (usando ORM)
Sincroniza dados reais entre o banco do Render e o banco local
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

def get_render_url():
    """Extrai URL do Render do arquivo .env"""
    env_path = '.env'
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"{env_path} não encontrado")
    
    with open(env_path, 'r') as f:
        for line in f:
            if 'dpg-' in line and 'postgresql' in line:
                if line.strip().startswith('#'):
                    line = line.lstrip('#').strip()
                else:
                    line = line.strip()
                
                if 'DATABASE_URL=' in line:
                    line = line.split('DATABASE_URL=')[1].strip()
                
                if '#' in line:
                    line = line.split('#')[0].strip()
                
                return line
    raise ValueError("DATABASE_URL não encontrada no .env")

def get_local_url():
    """Retorna URL do banco local"""
    return 'sqlite:///./instance/app.db'

def sync_local_to_render():
    """Sincroniza dados do Local para Render"""
    print("\n" + "="*80)
    print("SINCRONIZAR LOCAL → RENDER")
    print("="*80 + "\n")
    
    try:
        # Importar models
        from app import create_app, db
        from app.models import RoadmapItem
        
        # Criar app context
        app = create_app()
        
        with app.app_context():
            # Conectar ao Render
            render_url = get_render_url()
            render_engine = create_engine(render_url, echo=False)
            render_session = sessionmaker(bind=render_engine)()
            
            # Ler dados do Local
            print("Lendo dados do Local...")
            local_items = db.session.query(RoadmapItem).order_by(RoadmapItem.id).all()
            print(f"[OK] {len(local_items)} itens encontrados localmente\n")
            
            # Sincronizar para Render
            print("Sincronizando para Render...")
            
            updated = 0
            inserted = 0
            
            for i, local_item in enumerate(local_items, 1):
                try:
                    # Verificar se existe no Render
                    render_item = render_session.query(RoadmapItem).filter_by(id=local_item.id).first()
                    
                    if render_item:
                        # Atualizar campos
                        render_item.title = local_item.title
                        render_item.status = local_item.status
                        render_item.planned_start_date = local_item.planned_start_date
                        render_item.actual_start_date = local_item.actual_start_date
                        render_item.planned_completion_date = local_item.planned_completion_date
                        render_item.actual_completion_date = local_item.actual_completion_date
                        render_item.implemented_at = local_item.implemented_at
                        render_item.category_id = local_item.category_id
                        render_item.priority = local_item.priority
                        render_item.estimated_effort = local_item.estimated_effort
                        render_item.visible_to_users = local_item.visible_to_users
                        render_item.internal_only = local_item.internal_only
                        render_item.show_new_badge = local_item.show_new_badge
                        render_item.description = local_item.description
                        render_item.created_at = local_item.created_at
                        render_item.updated_at = local_item.updated_at
                        
                        updated += 1
                        print(f"  [{i}/{len(local_items)}] ✓ ID {local_item.id}: {local_item.title[:40]}")
                    else:
                        # Inserir novo
                        new_item = RoadmapItem(
                            id=local_item.id,
                            title=local_item.title,
                            status=local_item.status,
                            planned_start_date=local_item.planned_start_date,
                            actual_start_date=local_item.actual_start_date,
                            planned_completion_date=local_item.planned_completion_date,
                            actual_completion_date=local_item.actual_completion_date,
                            implemented_at=local_item.implemented_at,
                            category_id=local_item.category_id,
                            priority=local_item.priority,
                            estimated_effort=local_item.estimated_effort,
                            visible_to_users=local_item.visible_to_users,
                            internal_only=local_item.internal_only,
                            show_new_badge=local_item.show_new_badge,
                            description=local_item.description,
                            created_at=local_item.created_at,
                            updated_at=local_item.updated_at
                        )
                        render_session.add(new_item)
                        inserted += 1
                        print(f"  [{i}/{len(local_items)}] + ID {local_item.id}: {local_item.title[:40]} (novo)")
                        
                except Exception as e:
                    print(f"  [!] Erro ao sincronizar ID {local_item.id}: {str(e)}")
            
            # Commit
            try:
                render_session.commit()
                print(f"\n[✓] Sincronização concluída!")
                print(f"    → {updated} atualizados")
                print(f"    → {inserted} novos")
                print(f"    → Total: {len(local_items)} itens")
            except Exception as e:
                render_session.rollback()
                print(f"\n[!] Erro ao fazer commit: {str(e)}")
            finally:
                render_session.close()
        
    except Exception as e:
        print(f"[ERRO] {str(e)}")

def sync_render_to_local():
    """Sincroniza dados do Render para Local"""
    print("\n" + "="*80)
    print("SINCRONIZAR RENDER → LOCAL")
    print("="*80 + "\n")
    
    try:
        from app import create_app, db
        from app.models import RoadmapItem
        
        app = create_app()
        
        with app.app_context():
            # Conectar ao Render
            render_url = get_render_url()
            render_engine = create_engine(render_url, echo=False)
            render_session = sessionmaker(bind=render_engine)()
            
            # Ler dados do Render
            print("Lendo dados do Render...")
            render_items = render_session.query(RoadmapItem).order_by(RoadmapItem.id).all()
            print(f"[OK] {len(render_items)} itens encontrados no Render\n")
            
            # Sincronizar para Local
            print("Sincronizando para Local...")
            
            updated = 0
            inserted = 0
            
            for i, render_item in enumerate(render_items, 1):
                try:
                    local_item = db.session.query(RoadmapItem).filter_by(id=render_item.id).first()
                    
                    if local_item:
                        local_item.title = render_item.title
                        local_item.status = render_item.status
                        local_item.planned_start_date = render_item.planned_start_date
                        local_item.actual_start_date = render_item.actual_start_date
                        local_item.planned_completion_date = render_item.planned_completion_date
                        local_item.actual_completion_date = render_item.actual_completion_date
                        local_item.implemented_at = render_item.implemented_at
                        local_item.category_id = render_item.category_id
                        local_item.priority = render_item.priority
                        local_item.estimated_effort = render_item.estimated_effort
                        local_item.visible_to_users = render_item.visible_to_users
                        local_item.internal_only = render_item.internal_only
                        local_item.show_new_badge = render_item.show_new_badge
                        local_item.description = render_item.description
                        local_item.created_at = render_item.created_at
                        local_item.updated_at = render_item.updated_at
                        
                        updated += 1
                        print(f"  [{i}/{len(render_items)}] ✓ ID {render_item.id}: {render_item.title[:40]}")
                    else:
                        new_item = RoadmapItem(
                            id=render_item.id,
                            title=render_item.title,
                            status=render_item.status,
                            planned_start_date=render_item.planned_start_date,
                            actual_start_date=render_item.actual_start_date,
                            planned_completion_date=render_item.planned_completion_date,
                            actual_completion_date=render_item.actual_completion_date,
                            implemented_at=render_item.implemented_at,
                            category_id=render_item.category_id,
                            priority=render_item.priority,
                            estimated_effort=render_item.estimated_effort,
                            visible_to_users=render_item.visible_to_users,
                            internal_only=render_item.internal_only,
                            show_new_badge=render_item.show_new_badge,
                            description=render_item.description,
                            created_at=render_item.created_at,
                            updated_at=render_item.updated_at
                        )
                        db.session.add(new_item)
                        inserted += 1
                        print(f"  [{i}/{len(render_items)}] + ID {render_item.id}: {render_item.title[:40]} (novo)")
                        
                except Exception as e:
                    print(f"  [!] Erro ao sincronizar ID {render_item.id}: {str(e)}")
            
            try:
                db.session.commit()
                print(f"\n[✓] Sincronização concluída!")
                print(f"    → {updated} atualizados")
                print(f"    → {inserted} novos")
                print(f"    → Total: {len(render_items)} itens")
            except Exception as e:
                db.session.rollback()
                print(f"\n[!] Erro ao fazer commit: {str(e)}")
            finally:
                render_session.close()
        
    except Exception as e:
        print(f"[ERRO] {str(e)}")

def main():
    import sys
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        print("\n" + "="*80)
        print("SINCRONIZADOR - RENDER ↔ LOCAL")
        print("="*80)
        print("\nOpções:")
        print("  1 - Sincronizar Render → Local")
        print("  2 - Sincronizar Local → Render")
        choice = input("\nEscolha uma opção: ").strip()
    
    if choice == "1":
        sync_render_to_local()
    elif choice == "2":
        sync_local_to_render()
    else:
        print("\n[!] Opção inválida")

if __name__ == '__main__':
    main()
