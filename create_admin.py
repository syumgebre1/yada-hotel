from app import app
from database import db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    
    if admin:
        print("Admin already exists. Updating password...")
        admin.password = generate_password_hash('YadaAdmin2026!')
        db.session.commit()
        print("Admin password updated successfully!")
    else:
        print("Creating new admin user...")
        hashed_password = generate_password_hash('YadaAdmin2026!')
        new_admin = User(
            username='admin', 
            email='admin@yadahotel.com', 
            password=hashed_password
        )
        db.session.add(new_admin)
        db.session.commit()
        print("Admin created successfully!")

    print("\n===================================")
    print("Username: admin")
    print("Password: YadaAdmin2026!")
    print("===================================")
