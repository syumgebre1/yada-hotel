from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@yadahotel.com',
            password=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin created successfully!')
        print('Username: admin')
        print('Password: admin123')
    else:
        print('Admin already exists!')
