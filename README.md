# YADA Hotel

A full-stack hotel management web application built with Flask, SQLAlchemy, and vanilla JavaScript.

## Features

- User registration, login, and secure session management
- Room browsing, availability checking, and booking
- Restaurant menu, cart, and food ordering
- Table reservations
- Gallery with image uploads
- Admin panel with full CRUD for rooms, menu, gallery, and bookings
- PDF generation (food receipts, kitchen tickets) with logo and QR code
- Password change (admin and users)
- CSRF protection across all POST/PUT/DELETE requests

## Tech Stack

- Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, Flask-Mail
- SQLite (dev) / compatible with PostgreSQL
- Pillow for image validation, ReportLab for PDFs, qrcode for QR generation
- Vanilla JavaScript frontend

## Deployment

### Local Setup

```bash
git clone https://github.com/syumgebre1/yada-hotel.git
cd yada-hotel
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

### Environment Variables

Create a `.env` file in the project root:

```
SECRET_KEY=your-strong-random-secret-key-at-least-32-chars
FLASK_DEBUG=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-char-app-password
```

Generate a strong SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Database Setup

```bash
export FLASK_APP=app.py
flask db upgrade
```

### Create Admin

```bash
export ADMIN_PASSWORD='YourStrongPassword123!'
python create_admin.py
```

### Run

```bash
python app.py
```

App runs at `http://127.0.0.1:5002`.

### Production (PythonAnywhere)

1. Clone the repo in a Bash console
2. `pip install -r requirements.txt`
3. Create `.env` with a strong `SECRET_KEY`
4. `flask db upgrade`
5. Configure WSGI file to point to `app.py`
6. Reload the web app

---

## Database Migrations

After changing models in `models.py`:

```bash
export FLASK_APP=app.py
flask db migrate -m "Describe your change"
flask db upgrade
```

Commit the generated `migrations/versions/*.py` file to Git.
