#!/usr/bin/env python3
"""
Demonstração das melhorias implementadas no sistema de roadmap:
1. Data efetiva de implementação
2. Sistema de feedback dos usuários
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

from app import create_app, db
from app.models import RoadmapFeedback, RoadmapItem, User


def demonstrate_improvements():
    """Demonstra as melhorias implementadas"""

    app = create_app()
    with app.app_context():
        print("🚀 Demonstração das Melhorias do Sistema de Roadmap\n")

        # 1. Mostrar itens com data de implementação
        print("📅 1. ITENS COM DATA EFETIVA DE IMPLEMENTAÇÃO:")
        print("-" * 60)

        completed_items = RoadmapItem.query.filter_by(status="completed").all()

        if completed_items:
            for item in completed_items:
                print(f"✅ {item.title}")
                if item.implemented_at:
                    print(
                        f"   📅 Implementado em: {item.implemented_at.strftime('%d/%m/%Y %H:%M')}"
                    )
                else:
                    print("   ⚠️  Data de implementação não definida")
                print(f"   📊 Status: {item.get_status_display()[0]}")
                print()
        else:
            print("Nenhum item completado encontrado.\n")

        # 2. Mostrar sistema de feedback
        print("💬 2. SISTEMA DE FEEDBACK:")
        print("-" * 60)

        feedback_count = RoadmapFeedback.query.count()
        print(f"📊 Total de feedbacks recebidos: {feedback_count}")

        if feedback_count > 0:
            # Estatísticas de feedback
            avg_rating = (
                db.session.query(db.func.avg(RoadmapFeedback.rating)).scalar() or 0
            )
            print(f"📊 Avaliação média: {avg_rating:.1f}/5 ⭐")
            # Feedback por categoria
            rating_counts = (
                db.session.query(
                    RoadmapFeedback.rating, db.func.count(RoadmapFeedback.id)
                )
                .group_by(RoadmapFeedback.rating)
                .all()
            )

            print("⭐ Distribuição de avaliações:")
            for rating, count in sorted(rating_counts):
                stars = "⭐" * rating
                print(f"   {rating}/5 {stars}: {count} feedback(s)")

            print("\n📝 Últimos feedbacks recebidos:")
            recent_feedback = (
                RoadmapFeedback.query.join(RoadmapItem)
                .order_by(RoadmapFeedback.created_at.desc())
                .limit(3)
                .all()
            )

            for fb in recent_feedback:
                print(f"\n🎯 Funcionalidade: {fb.roadmap_item.title}")
                print(f"⭐ Avaliação: {fb.get_rating_display()}")
                if fb.title:
                    print(f"📌 Título: {fb.title}")
                if fb.comment:
                    print(
                        f"💬 Comentário: {fb.comment[:100]}{'...' if len(fb.comment) > 100 else ''}"
                    )
                print(f"👤 Usuário: {'Anônimo' if fb.is_anonymous else fb.user.name}")
                print(f"📅 Data: {fb.created_at.strftime('%d/%m/%Y %H:%M')}")
                print(f"📊 Status: {fb.get_status_display()[0]}")
        else:
            print("Nenhum feedback recebido ainda.\n")

        # 3. Mostrar funcionalidades disponíveis
        print("🔧 3. FUNCIONALIDADES DISPONÍVEIS:")
        print("-" * 60)

        print("📊 ADMIN ROADMAP:")
        print("   • Gerenciar itens do roadmap")
        print("   • Categorizar funcionalidades")
        print("   • Definir datas efetivas de implementação")
        print("   • Visualizar estatísticas")

        print("\n💬 ADMIN FEEDBACK:")
        print("   • Listar todos os feedbacks")
        print("   • Filtrar por status, avaliação, categoria")
        print("   • Responder aos usuários")
        print("   • Marcar feedbacks como tratados")
        print("   • Destacar feedbacks importantes")
        print("   • Exportar para CSV")

        print("\n👥 USUÁRIOS:")
        print("   • Visualizar roadmap público")
        print("   • Dar feedback sobre funcionalidades implementadas")
        print("   • Avaliar usabilidade, funcionalidade, performance")
        print("   • Enviar feedback anonimamente")
        print("   • Atualizar feedback anterior")

        print("\n📈 MÉTRICAS DISPONÍVEIS:")
        print("   • Avaliação média das funcionalidades")
        print("   • Distribuição de ratings")
        print("   • Feedback por categoria")
        print("   • Taxa de resposta da equipe")
        print("   • Satisfação dos usuários")

        print("\n🎯 PRÓXIMOS PASSOS:")
        print("   • Implementar notificações de novos feedbacks")
        print("   • Criar dashboard de satisfação do usuário")
        print("   • Adicionar análise de sentimento nos comentários")
        print("   • Implementar sistema de follow-up automático")

        print("\n✅ IMPLEMENTAÇÃO CONCLUÍDA!")
        print("As melhorias solicitadas foram implementadas com sucesso.")


if __name__ == "__main__":
    demonstrate_improvements()
