import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    user = User.query.filter_by(email='admin@petitio.com').first()
    if user:
        print(f'Usuário encontrado: {user.email}')
        print(f'user_type: {user.user_type}')
        print(f'is_active: {user.is_active}')
        print(f'is_master: {getattr(user, "is_master", "N/A")}')
    else:
        print('Usuário admin@petitio.com não encontrado')