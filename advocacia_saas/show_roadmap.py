from app import create_app, db
from app.models import RoadmapItem

app = create_app()
app.app_context().push()

print("=== TODOS OS ITENS DO ROADMAP ===\n")

items = (
    RoadmapItem.query.join(RoadmapItem.category)
    .order_by(RoadmapItem.priority.desc(), RoadmapItem.planned_start_date)
    .all()
)

for item in items:
    visibility = (
        "👁️ Público"
        if item.visible_to_users
        else "🔒 Interno"
        if item.internal_only
        else "👁️ Público"
    )
    status_emoji = {
        "planned": "📋",
        "in_progress": "🚧",
        "completed": "✅",
        "cancelled": "❌",
        "on_hold": "⏸️",
    }.get(item.status, "❓")
    priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
        item.priority, "⚪"
    )

    print(f"{status_emoji} {priority_emoji} {item.title}")
    print(f"   📁 {item.category.name} | {visibility}")
    start_date = (
        item.planned_start_date.strftime("%d/%m/%Y")
        if item.planned_start_date
        else "Não definido"
    )
    end_date = (
        item.planned_completion_date.strftime("%d/%m/%Y")
        if item.planned_completion_date
        else "Não definido"
    )
    print(f"   📅 {start_date} - {end_date} ({item.get_effort_display()[1]})")
    print()
