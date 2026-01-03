#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create admin user with admin@petitio.com"""

from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # Check if user already exists
    user = User.query.filter_by(email="admin@petitio.com").first()
    if user:
        print(f"User {user.email} already exists")
    else:
        # Create new master admin
        new_user = User(
            username="admin_petitio",
            email="admin@petitio.com",
            password_hash=generate_password_hash("admin123"),
            full_name="Admin Petitio",
            user_type="master",
            is_active=True,
        )
        db.session.add(new_user)
        db.session.commit()
        print(f"[OK] Created user: {new_user.email} ({new_user.user_type})")
        print(f"Password: admin123")
