import os
from app import app
from database import db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    password = os.environ.get('ADMIN_PASSWORD')
    if not password:
        print("❌ Error: ADMIN_PASSWORD environment variable is not set.")
        print("Run: export ADMIN_PASSWORD='YourStrongPassword123!' and try again.")
        exit(1)

    admin = User.query.filter_by(username='admin').first()
    if admin:
        admin.password = generate_password_hash(password)
        admin.is_admin = True
        db.session.commit()
        print("Admin updated successfully!")
    else:
        new_admin = User(username='admin', email='admin@yadahotel.com', password=generate_password_hash(password), is_admin=True)
        db.session.add(new_admin)
        db.session.commit()
        print("Admin created successfully!")
