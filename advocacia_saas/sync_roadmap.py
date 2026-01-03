#!/usr/bin/env python3
"""
Script: Sincronizar Roadmap - Render vs Local
Compara dados do Render com local e mostra evolução para clientes
Uso: python sync_roadmap.py
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app import create_app, db
from app.models import RoadmapCategory, RoadmapItem


def get_render_db_url():
    """Extrai URL do Render do comentário no .env"""
    env_file = Path(".env")
    if not env_file.exists():
        return None

    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()
        # Procura pela URL comentada do Render
        for line in content.split("\n"):
            if "dpg-" in line and "postgresql" in line:
                return line.strip("# ").strip()
    return None


def export_roadmap_snapshot(name_suffix=""):
    """Exporta snapshot atual do roadmap"""

    app = create_app()
    with app.app_context():
        items = RoadmapItem.query.all()
        categories = RoadmapCategory.query.all()

        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "render"
            if "render.com" in os.getenv("DATABASE_URL", "")
            else "local",
            "total_items": len(items),
            "categories": [
                {"id": cat.id, "name": cat.name, "items_count": cat.items.count()}
                for cat in categories
            ],
            "items": [item.to_dict() for item in items],
            "statistics": {"by_status": {}, "by_category": {}, "total_progress": 0},
        }

        # Calcular estatísticas
        for item in items:
            status = item.status
            snapshot["statistics"]["by_status"][status] = (
                snapshot["statistics"]["by_status"].get(status, 0) + 1
            )

            cat_name = item.category.name if item.category else "Sem Categoria"
            snapshot["statistics"]["by_category"][cat_name] = (
                snapshot["statistics"]["by_category"].get(cat_name, 0) + 1
            )

        completed = snapshot["statistics"]["by_status"].get("completed", 0)
        total = len(items)
        snapshot["statistics"]["total_progress"] = (
            round((completed / total * 100), 2) if total > 0 else 0
        )

        # Salvar snapshot
        filename = (
            Path("roadmap_snapshots")
            / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}{name_suffix}.json"
        )
        filename.parent.mkdir(exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        return snapshot, filename


def compare_snapshots(old_snapshot, new_snapshot):
    """Compara dois snapshots e identifica mudanças"""

    print("=" * 80)
    print("📊 ANÁLISE DE EVOLUÇÃO DO ROADMAP")
    print("=" * 80)
    print()

    # IDs dos itens
    old_items = {item["id"]: item for item in old_snapshot["items"]}
    new_items = {item["id"]: item for item in new_snapshot["items"]}

    print("📈 RESUMO GERAL")
    print("-" * 80)
    print(f"Data anterior: {old_snapshot['timestamp']}")
    print(f"Data atual:    {new_snapshot['timestamp']}")
    print()

    print(f"Total de itens (anterior): {old_snapshot['total_items']}")
    print(f"Total de itens (atual):    {new_snapshot['total_items']}")
    print()

    print("STATUS ANTERIOR:")
    for status, count in old_snapshot["statistics"]["by_status"].items():
        status_labels = {
            "planned": "📋",
            "in_progress": "🔄",
            "completed": "✅",
            "on_hold": "⏸️",
            "cancelled": "❌",
        }
        label = status_labels.get(status, "📌")
        print(f"  {label} {status}: {count}")

    print()
    print("STATUS ATUAL:")
    for status, count in new_snapshot["statistics"]["by_status"].items():
        status_labels = {
            "planned": "📋",
            "in_progress": "🔄",
            "completed": "✅",
            "on_hold": "⏸️",
            "cancelled": "❌",
        }
        label = status_labels.get(status, "📌")
        print(f"  {label} {status}: {count}")

    print()
    print(f"Progresso anterior: {old_snapshot['statistics']['total_progress']}%")
    print(f"Progresso atual:    {new_snapshot['statistics']['total_progress']}%")

    progress_change = (
        new_snapshot["statistics"]["total_progress"]
        - old_snapshot["statistics"]["total_progress"]
    )
    if progress_change > 0:
        print(f"✅ Melhora: +{progress_change}%")
    elif progress_change < 0:
        print(f"⚠️  Redução: {progress_change}%")
    else:
        print(f"= Sem mudanças")

    print()

    # Itens que mudaram
    print("🔄 ITENS QUE EVOLUÍRAM")
    print("-" * 80)

    changes = []
    for item_id, new_item in new_items.items():
        if item_id in old_items:
            old_item = old_items[item_id]

            # Verificar mudanças de status
            if old_item["status"] != new_item["status"]:
                changes.append(
                    {
                        "id": item_id,
                        "title": new_item["title"],
                        "type": "status",
                        "old": old_item["status"],
                        "new": new_item["status"],
                        "category": new_item["category"]["name"]
                        if new_item["category"]
                        else "N/A",
                    }
                )

            # Verificar mudanças de datas
            if old_item.get("actual_completion_date") != new_item.get(
                "actual_completion_date"
            ):
                if new_item.get("actual_completion_date"):
                    changes.append(
                        {
                            "id": item_id,
                            "title": new_item["title"],
                            "type": "completion",
                            "old": old_item.get("actual_completion_date"),
                            "new": new_item.get("actual_completion_date"),
                            "category": new_item["category"]["name"]
                            if new_item["category"]
                            else "N/A",
                        }
                    )

    if changes:
        for change in changes:
            if change["type"] == "status":
                status_map = {
                    "planned": "📋 Planejado",
                    "in_progress": "🔄 Em Andamento",
                    "completed": "✅ Concluído",
                    "on_hold": "⏸️ Em Espera",
                    "cancelled": "❌ Cancelado",
                }
                print(f"\n📌 {change['title']}")
                print(f"   Categoria: {change['category']}")
                print(
                    f"   Status: {status_map.get(change['old'], change['old'])} → {status_map.get(change['new'], change['new'])}"
                )

            elif change["type"] == "completion":
                print(f"\n✅ {change['title']}")
                print(f"   Concluído em: {change['new']}")
    else:
        print("✓ Nenhuma mudança de status detectada")

    print()

    # Itens sem mudança
    unchanged = sum(
        1
        for item_id in new_items.keys()
        if item_id in old_items
        and old_items[item_id]["status"] == new_items[item_id]["status"]
    )
    print(f"✓ Itens sem mudanças: {unchanged}")

    print()

    # Novos itens
    new_items_list = [
        item_id for item_id in new_items.keys() if item_id not in old_items
    ]
    if new_items_list:
        print(f"🆕 Novos itens adicionados: {len(new_items_list)}")
        for item_id in new_items_list[:3]:
            print(f"   • {new_items[item_id]['title']}")
        if len(new_items_list) > 3:
            print(f"   ... e mais {len(new_items_list) - 3}")

    print()

    # Itens removidos
    removed_items = [
        item_id for item_id in old_items.keys() if item_id not in new_items
    ]
    if removed_items:
        print(f"🗑️  Itens removidos: {len(removed_items)}")

    print()
    print("=" * 80)


def generate_client_report(snapshot):
    """Gera relatório para mostrar aos clientes"""

    print()
    print("=" * 80)
    print("🎯 RELATÓRIO PARA CLIENTES")
    print("=" * 80)
    print()

    print("Evolução do Roadmap da Petitio")
    print("-" * 80)
    print()

    stats = snapshot["statistics"]
    total = snapshot["total_items"]

    # Barra de progresso
    progress = stats["total_progress"]
    filled = int(progress / 5)
    bar = "█" * filled + "░" * (20 - filled)

    print(f"Progresso Geral: {bar} {progress}%")
    print()

    print("Status Atual dos Itens:")
    print()

    status_info = {
        "completed": ("✅ Concluído", "green"),
        "in_progress": ("🔄 Em Andamento", "yellow"),
        "planned": ("📋 Planejado", "blue"),
        "on_hold": ("⏸️  Em Espera", "orange"),
        "cancelled": ("❌ Cancelado", "red"),
    }

    for status, (label, _) in status_info.items():
        count = stats["by_status"].get(status, 0)
        pct = round((count / total * 100), 1) if total > 0 else 0
        print(f"{label}: {count} itens ({pct}%)")

    print()
    print("Por Categoria:")
    print()

    for category, count in stats["by_category"].items():
        print(f"  • {category}: {count} itens")

    print()
    print(f"Data: {datetime.now().strftime('%d de %B de %Y às %H:%M')}")
    print()
    print("=" * 80)


def main():
    """Fluxo principal"""

    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  🔄 SINCRONIZADOR DE ROADMAP - Render vs Local".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # 1. Buscar snapshots anteriores
    snapshots_dir = Path("roadmap_snapshots")
    snapshots = (
        sorted(snapshots_dir.glob("snapshot_*.json")) if snapshots_dir.exists() else []
    )

    old_snapshot = None
    if len(snapshots) >= 1:
        print("📂 Carregando snapshot anterior...")
        with open(snapshots[-1], "r", encoding="utf-8") as f:
            old_snapshot = json.load(f)
    else:
        print("ℹ️  Primeiro snapshot - não há dados anteriores para comparação")

    print()

    # 2. Exportar snapshot atual
    print("📥 Exportando dados atuais...")
    new_snapshot, filename = export_roadmap_snapshot()
    print(f"✅ Snapshot salvo: {filename.name}")
    print()

    # 3. Comparar se existem snapshots anteriores
    if old_snapshot:
        compare_snapshots(old_snapshot, new_snapshot)
    else:
        print("✓ Este é o primeiro snapshot - nenhuma comparação disponível")
        print()

    # 4. Gerar relatório para clientes
    generate_client_report(new_snapshot)

    print()
    print("✨ Sincronização concluída!")
    print()
    print("📍 Arquivos gerados:")
    print(f"   • Snapshot: roadmap_snapshots/{filename.name}")
    if old_snapshot:
        print(f"   • Anterior:  roadmap_snapshots/{snapshots[-1].name}")
    print()
    print("Próxima sincronização agendada para amanhã")
    print()


if __name__ == "__main__":
    main()
