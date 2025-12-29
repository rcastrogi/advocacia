#!/usr/bin/env python3
"""
Script para atualizar status dos itens do roadmap que foram implementados
"""

import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import RoadmapItem


def update_roadmap_status():
    """Atualiza o status dos itens implementados do roadmap"""

    app = create_app()
    with app.app_context():
        print("🔄 Atualizando status do roadmap...")

        # Atualizar Dashboard de Analytics Avançado para completed
        dashboard_item = RoadmapItem.query.filter_by(
            slug="dashboard-analytics-avancado"
        ).first()
        if dashboard_item:
            dashboard_item.status = "completed"
            dashboard_item.actual_completion_date = datetime.utcnow().date()
            print("✅ Dashboard de Analytics Avançado marcado como concluído")
        else:
            print("⚠️ Item 'Dashboard de Analytics Avançado' não encontrado")

        # Atualizar Otimização de Performance para completed
        performance_item = RoadmapItem.query.filter_by(
            slug="otimizacao-performance"
        ).first()
        if performance_item:
            performance_item.status = "completed"
            performance_item.actual_completion_date = datetime.utcnow().date()
            print("✅ Otimização de Performance marcada como concluída")
        else:
            print("⚠️ Item 'Otimização de Performance' não encontrado")

        # Adicionar Portal do Cliente Avançado se não existir
        portal_item = RoadmapItem.query.filter_by(
            slug="portal-cliente-avancado"
        ).first()
        if not portal_item:
            from app.models import RoadmapCategory

            funcionalidades_cat = RoadmapCategory.query.filter_by(
                slug="funcionalidades"
            ).first()
            if funcionalidades_cat:
                portal_item = RoadmapItem(
                    category_id=funcionalidades_cat.id,
                    title="Portal do Cliente Avançado",
                    slug="portal-cliente-avancado",
                    description="Portal completo para clientes acompanharem seus processos",
                    detailed_description="Sistema avançado de portal do cliente com acompanhamento de processos, documentos, pagamentos e comunicação direta com o escritório.",
                    status="completed",
                    priority="high",
                    estimated_effort="large",
                    visible_to_users=True,
                    internal_only=False,
                    business_value="Melhorar experiência do cliente e reduzir workload administrativo",
                    technical_complexity="medium",
                    user_impact="high",
                    tags="portal, cliente, processos, comunicação",
                    planned_start_date=datetime.utcnow().date() - timedelta(days=30),
                    planned_completion_date=datetime.utcnow().date()
                    + timedelta(days=30),
                    actual_start_date=datetime.utcnow().date() - timedelta(days=30),
                    actual_completion_date=datetime.utcnow().date(),
                )
                db.session.add(portal_item)
                print("✅ Portal do Cliente Avançado adicionado como concluído")
            else:
                print("⚠️ Categoria 'funcionalidades' não encontrada")

        db.session.commit()
        print("🎉 Atualização do roadmap concluída!")


if __name__ == "__main__":
    update_roadmap_status()
