#!/usr/bin/env python3
from app import create_app

app = create_app()
with app.app_context():
    from app.admin.routes import petition_models_list

    print("Função petition_models_list existe e pode ser importada")
