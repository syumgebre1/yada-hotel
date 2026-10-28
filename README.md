# 🏨 YADA HOTEL - Full-Stack Hotel Management System

A complete, production-ready web application for managing a hotel's operations. This system handles everything from public room bookings and restaurant orders to a secure administrative dashboard with PDF receipt generation.

Built with **Python (Flask)** and **Vanilla JavaScript**, this project focuses on performance, security, and a seamless user experience.

🔗 **Live Demo:** [https://syumgebre1.pythonanywhere.com](https://syumgebre1.pythonanywhere.com)

---

## ✨ Core Features

### 🛏️ For Guests (Public & Authenticated)
*   **Room Bookings:** Browse rooms with a dynamic image carousel, filter by type, and check real-time date availability.
*   **Restaurant & Cart:** View the menu (including "Today's Special"), add items to a persistent cart, and checkout with an option for room service delivery.
*   **User Dashboard:** A modern sidebar layout where guests can manage bookings, view food orders, download PDF invoices/receipts, update profiles, and change passwords.
*   **Reviews & Ratings:** Guests can leave 5-star reviews for rooms they have stayed in.
*   **Multi-Language Support:** Full English and Amharic (አማርኛ) translation toggle.
*   **Dark Mode:** A sleek, persistent dark theme for night-time browsing.

### 🔐 For Administrators (Secure Dashboard)
*   **Analytics:** Real-time revenue tracking with Chart.js visualization (last 7 days).
*   **Calendar View:** FullCalendar integration to see all room bookings at a glance.
*   **Room Management:** Add, edit, or delete rooms. Upload multiple images per room, set amenities, and feature rooms on the homepage.
*   **Menu Management:** Add, edit, or delete food items. Upload food images and mark items as "Today's Special."
*   **Order Management:** Track food orders by status (Pending, Preparing, Delivered) and print kitchen tickets.
*   **PDF Generation:** Export full booking reports and individual food order receipts (styled with gold/silver/red branding).
*   **Site Settings:** Update the hotel's WhatsApp number, Telegram, email, and address dynamically from the dashboard.

---

## 🛠️ Tech Stack

*   **Backend:** Python, Flask, Flask-Login, Flask-Mail
*   **Database:** SQLite (with SQLAlchemy ORM)
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript (ES6+)
*   **Libraries (Frontend):** Swiper.js (carousels), Chart.js (analytics), FullCalendar (scheduling), Toastify.js (notifications), FontAwesome (icons)
*   **PDF Generation:** ReportLab (Python)
*   **Deployment:** PythonAnywhere

---

## 📂 Project Structure

```text
yada-hotel/
├── app.py                  # Main Flask application & API routes
├── models.py               # SQLAlchemy database models
├── create_admin.py         # Script to generate the initial admin user
├── requirements.txt        # Python dependencies
├── instance/               # SQLite database (created automatically)
├── static/                 # CSS, JS, PWA icons, and uploaded images
│   ├── uploads/            # Room, food, and gallery images
│   ├── logo.png            # Hotel branding
│   ├── style.css           # Global styles & Dark Mode variables
│   ├── manifest.json       # PWA manifest
│   └── service-worker.js   # PWA offline caching
└── templates/              # Jinja2 HTML templates
    ├── index.html          # Landing page
    ├── rooms.html          # Room listings & filters
    ├── restaurant.html     # Food menu & cart
    ├── dashboard.html      # User profile & orders
    └── admin.html          # Admin control panel
