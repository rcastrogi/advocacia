#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sincronização Bidirecional - Render ↔ Local
Sincroniza dados reais entre o banco do Render e o banco local
"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()


def get_render_url():
    """Extrai URL do Render do arquivo .env"""
    env_path = ".env"
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"{env_path} não encontrado")

    with open(env_path, "r") as f:
        for line in f:
            # Procura por linha com dpg- e postgresql (mesmo se comentada)
            if "dpg-" in line and "postgresql" in line:
                # Se tiver comentário no início, tira
                if line.strip().startswith("#"):
                    line = line.lstrip("#").strip()
                else:
                    line = line.strip()

                # Remove DATABASE_URL= se houver
                if "DATABASE_URL=" in line:
                    line = line.split("DATABASE_URL=")[1].strip()

                # Remove comentários inline
                if "#" in line:
                    line = line.split("#")[0].strip()

                return line
    raise ValueError("DATABASE_URL não encontrada no .env")


def get_local_url():
    """Retorna URL do banco local"""
    return "sqlite:///f:/PROJETOS/advocacia/advocacia_saas/instance/app.db"


def read_roadmap_items(engine):
    """Lê todos os itens do roadmap de um banco"""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT id, title, status, planned_start_date, actual_start_date, "
                "planned_completion_date, actual_completion_date, implemented_at, "
                "category_id, priority, estimated_effort, visible_to_users, "
                "internal_only, show_new_badge, description, created_at, updated_at "
                "FROM roadmap_items ORDER BY id"
            )
        )

        columns = result.keys()
        items = []
        for row in result:
            items.append(dict(zip(columns, row)))
        return items


def sync_from_render_to_local():
    """Sincroniza dados do Render para Local"""
    print("\n" + "=" * 80)
    print("SINCRONIZAR RENDER → LOCAL")
    print("=" * 80 + "\n")

    try:
        render_url = get_render_url()
        render_engine = create_engine(render_url)
        local_engine = create_engine(get_local_url())

        print("[OK] Conectados aos bancos de dados\n")

        # Ler do Render
        print("Lendo dados do Render...")
        render_items = read_roadmap_items(render_engine)
        print(f"[OK] {len(render_items)} itens encontrados no Render\n")

        # Sincronizar para Local
        print("Sincronizando para Local...")
        with local_engine.begin() as conn:
            for i, item in enumerate(render_items, 1):
                # Preparar dados
                placeholders = ", ".join([f":{k}" for k in item.keys()])
                columns = ", ".join(item.keys())

                insert_sql = f"""
                    INSERT OR REPLACE INTO roadmap_item ({columns})
                    VALUES ({placeholders})
                """

                try:
                    conn.execute(text(insert_sql), item)
                    print(
                        f"  [{i}/{len(render_items)}] ID {item['id']}: {item['title'][:40]}"
                    )
                except Exception as e:
                    print(f"  [!] Erro ao sincronizar ID {item['id']}: {str(e)}")

            conn.commit()

        print(f"\n[✓] Sincronização concluída! {len(render_items)} itens atualizados")

    except Exception as e:
        print(f"[ERRO] {str(e)}")


def sync_from_local_to_render():
    """Sincroniza dados do Local para Render"""
    print("\n" + "=" * 80)
    print("SINCRONIZAR LOCAL → RENDER")
    print("=" * 80 + "\n")

    try:
        render_url = get_render_url()
        render_engine = create_engine(render_url)
        local_engine = create_engine(get_local_url())

        print("[OK] Conectados aos bancos de dados\n")

        # Ler do Local
        print("Lendo dados do Local...")
        local_items = read_roadmap_items(local_engine)
        print(f"[OK] {len(local_items)} itens encontrados localmente\n")

        # Sincronizar para Render
        print("Sincronizando para Render...")
        with render_engine.begin() as conn:
            for i, item in enumerate(local_items, 1):
                # Preparar dados (sem IDs gerados, usar ID real)
                item_copy = item.copy()

                # Montar UPDATE para evitar violações de constraint
                set_clause = ", ".join(
                    [f"{k}=%s" for k in item_copy.keys() if k != "id"]
                )
                update_sql = f"""
                    UPDATE roadmap_item 
                    SET {set_clause}
                    WHERE id = %s
                """

                try:
                    # Primeiro tenta UPDATE
                    cursor = conn.execute(
                        update_sql.replace("%s", ":val"),
                        {f"val{i}": v for i, v in enumerate(item_copy.values())},
                    )

                    # Se não atualizou, tenta INSERT
                    if cursor.rowcount == 0:
                        columns = ", ".join(item_copy.keys())
                        placeholders = ", ".join([f":{k}" for k in item_copy.keys()])
                        insert_sql = f"INSERT INTO roadmap_item ({columns}) VALUES ({placeholders})"
                        conn.execute(text(insert_sql), item_copy)

                    print(
                        f"  [{i}/{len(local_items)}] ID {item['id']}: {item['title'][:40]}"
                    )
                except Exception as e:
                    print(f"  [!] Erro ao sincronizar ID {item['id']}: {str(e)}")

            conn.commit()

        print(f"\n[✓] Sincronização concluída! {len(local_items)} itens atualizados")

    except Exception as e:
        print(f"[ERRO] {str(e)}")


def compare_databases():
    """Compara os dois bancos sem modificar"""
    print("\n" + "=" * 80)
    print("COMPARAR RENDER vs LOCAL (SEM MODIFICAR)")
    print("=" * 80 + "\n")

    try:
        render_url = get_render_url()
        render_engine = create_engine(render_url)
        local_engine = create_engine(get_local_url())

        render_items = read_roadmap_items(render_engine)
        local_items = read_roadmap_items(local_engine)

        render_ids = {item["id"] for item in render_items}
        local_ids = {item["id"] for item in local_items}

        print(f"Render: {len(render_items)} itens")
        print(f"Local:  {len(local_items)} itens\n")

        # Apenas no Render
        only_render = render_ids - local_ids
        if only_render:
            print(f"[+] Apenas no Render ({len(only_render)}):")
            for id in sorted(only_render):
                item = next(i for i in render_items if i["id"] == id)
                print(f"    ID {id}: {item['title']}")

        # Apenas no Local
        only_local = local_ids - render_ids
        if only_local:
            print(f"\n[+] Apenas no Local ({len(only_local)}):")
            for id in sorted(only_local):
                item = next(i for i in local_items if i["id"] == id)
                print(f"    ID {id}: {item['title']}")

        # Em ambos
        common = render_ids & local_ids
        if common:
            print(f"\n[=] Em ambos ({len(common)}):")
            differences = []
            for id in sorted(common):
                render_item = next(i for i in render_items if i["id"] == id)
                local_item = next(i for i in local_items if i["id"] == id)

                # Comparar status
                if render_item["status"] != local_item["status"]:
                    differences.append(
                        {
                            "id": id,
                            "title": render_item["title"],
                            "render_status": render_item["status"],
                            "local_status": local_item["status"],
                        }
                    )

            if differences:
                print(f"\n[!] Diferenças de status ({len(differences)}):")
                for diff in differences:
                    print(f"    ID {diff['id']}: {diff['title']}")
                    print(
                        f"      Render: {diff['render_status']} → Local: {diff['local_status']}"
                    )
            else:
                print(f"    Todos com dados iguais")

        print(f"\n[✓] Comparação concluída")

    except Exception as e:
        print(f"[ERRO] {str(e)}")


def main():
    print("\n" + "=" * 80)
    print("SINCRONIZADOR BIDIRECIONAL - RENDER ↔ LOCAL")
    print("=" * 80)
    print("\nOpções:")
    print("  1 - Comparar Render vs Local (visualizar diferenças)")
    print("  2 - Sincronizar Render → Local")
    print("  3 - Sincronizar Local → Render")
    print("  0 - Sair")

    choice = input("\nEscolha uma opção: ").strip()

    if choice == "1":
        compare_databases()
    elif choice == "2":
        sync_from_render_to_local()
    elif choice == "3":
        sync_from_local_to_render()
    elif choice == "0":
        print("\nSaindo...")
    else:
        print("\n[!] Opção inválida")


if __name__ == "__main__":
    main()
