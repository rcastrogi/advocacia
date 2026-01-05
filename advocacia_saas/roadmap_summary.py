#!/usr/bin/env python3
"""
Gerar visualização completa do roadmap atualizado
"""
import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime

# Cores ANSI para terminal mais vibrantes
class Colors:
    # Backgrounds coloridos para badges
    CRITICAL = '\033[38;2;255;255;255m\033[48;2;220;0;0m'  # Branco fundo vermelho intenso
    HIGH = '\033[38;2;255;255;255m\033[48;2;255;140;0m'    # Branco fundo laranja intenso
    MEDIUM = '\033[38;2;0;0;0m\033[48;2;255;215;0m'        # Preto fundo amarelo ouro
    LOW = '\033[38;2;0;0;0m\033[48;2;144;238;144m'         # Preto fundo verde claro
    
    # Status com cores
    COMPLETED = '\033[38;2;255;255;255m\033[48;2;34;139;34m'      # Branco fundo verde escuro
    IN_PROGRESS = '\033[38;2;0;0;0m\033[48;2;30;144;255m'         # Preto fundo azul
    PLANNED = '\033[38;2;255;255;255m\033[48;2;75;0;130m'         # Branco fundo índigo
    
    # Reset
    RESET = '\033[0m'
    BOLD = '\033[1m'

database_url = os.getenv('DATABASE_URL')

if not database_url:
    print("[ERRO] DATABASE_URL não configurada")
    exit(1)

def badge_priority(priority):
    """Cria badge colorido para prioridade"""
    badges = {
        'critical': f"{Colors.CRITICAL} CRÍTICA {Colors.RESET}",
        'high': f"{Colors.HIGH} ALTA {Colors.RESET}",
        'medium': f"{Colors.MEDIUM} MÉDIA {Colors.RESET}",
        'low': f"{Colors.LOW} BAIXA {Colors.RESET}"
    }
    return badges.get(priority, priority)

def badge_status(status):
    """Cria badge colorido para status"""
    badges = {
        'completed': f"{Colors.COMPLETED} ✅ COMPLETO {Colors.RESET}",
        'in_progress': f"{Colors.IN_PROGRESS} 🚀 EM DEV {Colors.RESET}",
        'planned': f"{Colors.PLANNED} 📅 PLANEJADO {Colors.RESET}"
    }
    return badges.get(status, status)

try:
    parsed = urlparse(database_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password
    )
    
    cursor = conn.cursor()
    
    # Título
    print("\n" + "="*100)
    print("📊 ROADMAP VALIDADO E SINCRONIZADO - JANEIRO 2026".center(100))
    print("="*100)
    
    # Estatísticas gerais
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN status='completed' THEN 1 END) as completed,
            COUNT(CASE WHEN status='in_progress' THEN 1 END) as in_progress,
            COUNT(CASE WHEN status='planned' THEN 1 END) as planned,
            ROUND(100.0 * COUNT(CASE WHEN status='completed' THEN 1 END) / COUNT(*), 1) as completion_pct
        FROM roadmap_items
    """)
    
    total, completed, in_progress, planned, completion_pct = cursor.fetchone()
    
    print(f"\n📈 PROGRESSO GERAL:")
    print(f"   ✅ {completed}/{ total} Completas ({completion_pct}%)")
    print(f"   🚀 {in_progress}/{total} Em Desenvolvimento")
    print(f"   📅 {planned}/{total} Planejadas")
    
    # Prioridades
    cursor.execute("""
        SELECT priority, COUNT(*) as count FROM roadmap_items 
        GROUP BY priority 
        ORDER BY CASE priority 
            WHEN 'critical' THEN 1 WHEN 'high' THEN 2 
            WHEN 'medium' THEN 3 WHEN 'low' THEN 4 
        END
    """)
    
    print(f"\n🎯 PRIORIDADES:")
    for priority, count in cursor.fetchall():
        badge = badge_priority(priority)
        print(f"   {badge} : {count:2d} items")

    
    # Completos recentes
    print(f"\n✅ RECENTEMENTE COMPLETADOS (últimos 30 dias):")
    cursor.execute("""
        SELECT title, actual_completion_date FROM roadmap_items 
        WHERE status='completed' AND actual_completion_date >= CURRENT_DATE - 30
        ORDER BY actual_completion_date DESC
        LIMIT 10
    """)
    
    for idx, (title, date) in enumerate(cursor.fetchall(), 1):
        print(f"   {idx:2d}. {title[:50]:50s} ({date})")
    
    # Em desenvolvimento
    print(f"\n🚀 EM DESENVOLVIMENTO (10):")
    cursor.execute("""
        SELECT id, title, priority, effort_score FROM roadmap_items 
        WHERE status='in_progress'
        ORDER BY 
            CASE priority 
                WHEN 'critical' THEN 1 
                WHEN 'high' THEN 2 
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4 
            END,
            effort_score DESC
        LIMIT 10
    """)
    
    for id, title, priority, effort in cursor.fetchall():
        badge = badge_priority(priority)
        effort_bar = "█" * effort + "░" * (5-effort)
        print(f"   [{id:2d}] {badge} {title[:35]:35s} {effort_bar}")

    
    # Próximos a implementar (High priority + Not started)
    print(f"\n📅 PRÓXIMOS NA FILA (High Priority + Planejado):")
    cursor.execute("""
        SELECT id, title, planned_start_date FROM roadmap_items 
        WHERE status='planned' AND priority IN ('critical', 'high')
        ORDER BY planned_start_date ASC, impact_score DESC
        LIMIT 8
    """)
    
    for idx, (id, title, start_date) in enumerate(cursor.fetchall(), 1):
        print(f"   {idx}. [{id:2d}] {title[:45]:45s} (Início: {start_date})")
    
    # Resumo por categoria
    print(f"\n📂 DISTRIBUIÇÃO POR CATEGORIA:")
    cursor.execute("""
        SELECT tags, COUNT(*) as count FROM roadmap_items 
        WHERE tags IS NOT NULL
        GROUP BY tags
        ORDER BY count DESC
        LIMIT 12
    """)
    
    for tags, count in cursor.fetchall():
        tag_list = tags.split(',')[:2]  # Primeiras 2 tags
        tag_str = ' / '.join(tag_list)
        print(f"   • {tag_str:35s} {count:2d} items")
    
    # Effort vs Impact
    print(f"\n💪 ANÁLISE EFFORT vs IMPACT:")
    cursor.execute("""
        SELECT 
            CASE effort_score 
                WHEN 1 THEN 'Trivial' 
                WHEN 2 THEN 'Simples' 
                WHEN 3 THEN 'Médio' 
                WHEN 4 THEN 'Complexo' 
                WHEN 5 THEN 'Muito Complexo'
            END as difficulty,
            COUNT(*) as count,
            ROUND(AVG(impact_score), 1) as avg_impact
        FROM roadmap_items
        GROUP BY effort_score
        ORDER BY effort_score
    """)
    
    for difficulty, count, avg_impact in cursor.fetchall():
        print(f"   {difficulty:15s}: {count:2d} items (Impact médio: {avg_impact:.1f}/5)")
    
    # Status timeline
    print(f"\n⏰ TIMELINE ESTIMADA:")
    cursor.execute("""
        SELECT 
            EXTRACT(MONTH FROM planned_completion_date)::int as month,
            EXTRACT(YEAR FROM planned_completion_date)::int as year,
            COUNT(*) as count,
            COUNT(CASE WHEN status='completed' THEN 1 END) as completed
        FROM roadmap_items 
        WHERE planned_completion_date IS NOT NULL
        GROUP BY year, month
        ORDER BY year, month
        LIMIT 12
    """)
    
    months_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                  7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    
    for month, year, total_planned, completed in cursor.fetchall():
        if month:  # Evitar None
            month_name = months_map.get(month, '???')
            remaining = total_planned - (completed or 0)
            print(f"   {month_name}/{year}: {completed or 0} completas + {remaining} planejadas")
    
    # Métricas finais
    print(f"\n📊 MÉTRICAS FINAIS:")
    cursor.execute("""
        SELECT 
            ROUND(AVG(impact_score), 1) as avg_impact,
            ROUND(AVG(effort_score), 1) as avg_effort,
            MAX(impact_score) as max_impact,
            COUNT(CASE WHEN show_new_badge=true THEN 1 END) as new_features
        FROM roadmap_items
    """)
    
    avg_impact, avg_effort, max_impact, new_features = cursor.fetchone()
    print(f"   📈 Impacto médio: {avg_impact}/5")
    print(f"   💪 Effort médio: {avg_effort}/5")
    print(f"   ⭐ Impacto máximo: {max_impact}/5")
    print(f"   🆕 Novas features: {new_features}")
    
    print("\n" + "="*100)
    print(f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}".center(100))
    print(f"Veja detalhes completos em: VALIDATION_REPORT_2026.md".center(100))
    print("="*100 + "\n")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"[ERRO] {str(e)}")
    import traceback
    traceback.print_exc()
