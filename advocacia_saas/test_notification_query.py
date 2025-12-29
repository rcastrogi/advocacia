from app import create_app, db
from app.models import ProcessNotification

app = create_app()

with app.app_context():
    print("Testing ProcessNotification query...")

    try:
        # Testar query simples
        count = ProcessNotification.query.count()
        print(f"Total notifications: {count}")

        # Testar query com filtro
        unread = ProcessNotification.query.filter_by(read=False).count()
        print(f"Unread notifications: {unread}")

        # Testar query específica como no código
        from app.processes.notifications import get_unread_notifications

        result = get_unread_notifications(1, limit=10)  # user_id = 1
        print(f"Query successful, returned {len(result)} notifications")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
