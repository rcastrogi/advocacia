#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: Comparar Roadmap - Render vs Local
Conecta no banco do Render e compara dados reais
Uso: python compare_render_local.py
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

def get_render_url():
    """Extrai URL real do Render do .env"""
    env_file = '.env'
    if not os.path.exists(env_file):
        return None
    
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        for line in content.split('\n'):
            if 'dpg-' in line and 'postgresql' in line:
                # Remover comentário e DATABASE_URL=
                url = line.strip()
                if url.startswith('#'):
                    url = url[1:].strip()
                if url.startswith('DATABASE_URL='):
                    url = url[13:].strip()
                return url
    return None

def compare_databases():
    """Compara dados do Render com local"""
    
    print()
    print("=" * 80)
    print("COMPARAR ROADMAP - RENDER vs LOCAL")
    print("=" * 80)
    print()
    
    # 1. Conectar no Render
    render_url = get_render_url()
    if not render_url:
        print("[ERRO] URL do Render nao encontrada no .env")
        return False
    
    print("[OK] URL do Render encontrada")
    print()
    
    # Testar conexao no Render
    print("Conectando no banco do Render...")
    
    try:
        from sqlalchemy import create_engine, text
        
        # Criar engine para Render
        render_engine = create_engine(render_url, echo=False)
        render_conn = render_engine.connect()
        
        print("[OK] Conectado ao Render!")
        print()
        
        # Ler dados do Render
        print("Lendo dados do Render...")
        print("-" * 80)
        print()
        
        # Contar itens no Render
        result = render_conn.execute(text("SELECT COUNT(*) as total FROM roadmap_items"))
        render_total = result.scalar()
        print(f"Total de itens no Render: {render_total}")
        
        # Status no Render
        result = render_conn.execute(text("""
            SELECT status, COUNT(*) as count 
            FROM roadmap_items 
            GROUP BY status 
            ORDER BY status
        """))
        
        print("\nStatus no Render:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")
        
        # Primeiros 5 itens
        result = render_conn.execute(text("""
            SELECT id, title, status, planned_start_date, actual_start_date, 
                   planned_completion_date, actual_completion_date
            FROM roadmap_items 
            LIMIT 5
        """))
        
        print("\nPrimeiros 5 itens no Render:")
        for row in result:
            print(f"\n  ID: {row[0]}")
            print(f"  Titulo: {row[1]}")
            print(f"  Status: {row[2]}")
            print(f"  Planejado inicio: {row[3]}")
            print(f"  Inicio real: {row[4]}")
            print(f"  Planejado fim: {row[5]}")
            print(f"  Fim real: {row[6]}")
        
        print()
        render_conn.close()
        
    except Exception as e:
        print(f"[ERRO] Nao conseguiu conectar no Render: {str(e)}")
        print()
        print("Possivel motivo:")
        print("- URL incorreta ou expirada")
        print("- Rede bloqueada")
        print("- Credenciais inválidas")
        return False
    
    print()
    print("=" * 80)
    print("LEITURA LOCAL")
    print("=" * 80)
    print()
    
    # 2. Conectar localmente
    print("Conectando no banco local...")
    
    try:
        from app import create_app, db
        from app.models import RoadmapItem
        
        app = create_app()
        with app.app_context():
            print("[OK] Conectado ao banco local!")
            print()
            
            # Contar itens locais
            local_total = RoadmapItem.query.count()
            print(f"Total de itens locais: {local_total}")
            
            # Status locais
            from sqlalchemy import func
            
            status_counts = db.session.query(
                RoadmapItem.status,
                func.count(RoadmapItem.id)
            ).group_by(RoadmapItem.status).all()
            
            print("\nStatus locais:")
            for status, count in status_counts:
                print(f"  {status}: {count}")
            
            # Primeiros 5 itens locais
            local_items = RoadmapItem.query.limit(5).all()
            
            print("\nPrimeiros 5 itens locais:")
            for item in local_items:
                print(f"\n  ID: {item.id}")
                print(f"  Titulo: {item.title}")
                print(f"  Status: {item.status}")
                print(f"  Planejado inicio: {item.planned_start_date}")
                print(f"  Inicio real: {item.actual_start_date}")
                print(f"  Planejado fim: {item.planned_completion_date}")
                print(f"  Fim real: {item.actual_completion_date}")
            
    except Exception as e:
        print(f"[ERRO] Nao conseguiu conectar localmente: {str(e)}")
        return False
    
    print()
    print("=" * 80)
    print("COMPARACAO")
    print("=" * 80)
    print()
    
    if render_total == local_total:
        print(f"[OK] Mesma quantidade de itens: {render_total}")
    else:
        print(f"[!] Diferença na quantidade:")
        print(f"    Render: {render_total}")
        print(f"    Local:  {local_total}")
    
    print()
    return True

if __name__ == '__main__':
    try:
        success = compare_databases()
        import sys
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERRO] {str(e)}")
        import sys
        sys.exit(1)
