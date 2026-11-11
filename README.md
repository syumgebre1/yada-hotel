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