
from pathlib import Path
from flask import Flask, request, jsonify, session, render_template, Response
from flask_cors import CORS
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect, generate_csrf
from database import db
from models import (
    User, Room, Booking, Review, RoomImage, ContactMessage,
    SiteSetting, MenuItem, CartItem, FoodOrder, TableReservation,
    GalleryImage
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import os
import io
import json
import secrets

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

# Security configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"] or len(app.config["SECRET_KEY"]) < 32:
    raise RuntimeError("Configure a strong SECRET_KEY in your environment.")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///yada_hotel.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_PATH"] = "/"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# CSRF protection remains enabled.
app.config["WTF_CSRF_CHECK_DEFAULT"] = True
app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken", "X-CSRF-Token"]
app.config["WTF_CSRF_TIME_LIMIT"] = None
csrf = CSRFProtect(app)

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get(
    "MAIL_DEFAULT_SENDER", "yada.hotel@example.com"
)
mail = Mail(app)

db.init_app(app)
migrate = Migrate(app, db)

CORS(
    app,
    supports_credentials=True,
    origins=[
        "https://syumgebre1.pythonanywhere.com",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
    ],
    expose_headers=["X-CSRFToken"],
)

# Expose the same generated token in the header and frontend-readable cookie.
@app.after_request
def inject_csrf_token(response):
    if request.path.startswith("/api/"):
        try:
            token = generate_csrf()
            response.headers["X-CSRFToken"] = token
            response.set_cookie(
                "csrf_token",
                token,
                secure=request.is_secure,
                httponly=False,
                samesite="Lax",
                path="/",
            )
        except Exception:
            app.logger.exception("Unable to generate CSRF token")
    return response


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None
login_manager.login_message = None


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "OPTIONS":
            return "", 200
        if not current_user.is_authenticated:
            return jsonify({"error": "Please login first"}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "OPTIONS":
            return "", 200
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function


def get_json_data():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def save_uploaded_file(file, prefix="upload"):
    """Save an upload with a unique name to avoid overwriting existing files."""
    if not file or not file.filename:
        return None

    safe_name = secure_filename(file.filename)
    if not safe_name:
        return None

    extension = Path(safe_name).suffix.lower()
    stem = Path(safe_name).stem[:60] or prefix
    filename = f"{prefix}_{secrets.token_hex(8)}_{stem}{extension}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


def create_data():
    if Room.query.first() is None:
        rooms_data = [
            ("101", "Standard", 2000, "Cozy room with city view"),
            ("102", "Standard", 2000, "Comfortable room with garden view"),
            ("103", "Deluxe", 3500, "Spacious room with balcony"),
            ("104", "Deluxe", 3500, "Elegant room with mountain view"),
            ("105", "Suite", 5000, "Luxury suite with living room"),
            ("106", "Standard", 2200, "Modern room with workspace"),
            ("107", "Deluxe", 3800, "Premium room with ocean view"),
            ("108", "Suite", 5500, "Executive suite with jacuzzi"),
            ("109", "Standard", 2500, "Family room with extra bed"),
            ("110", "Standard", 2500, "Twin beds with city view"),
            ("111", "Deluxe", 4000, "Corner room with panoramic view"),
            ("112", "Deluxe", 4200, "Family deluxe with kitchenette"),
            ("113", "Suite", 6000, "Presidential suite with private balcony"),
        ]
        for number, room_type, price, description in rooms_data:
            db.session.add(
                Room(
                    room_number=number,
                    room_type=room_type,
                    price=price,
                    description=description,
                    available=True,
                )
            )

    if MenuItem.query.first() is None:
        foods_data = [
            ("Doro Wat", "Traditional spicy chicken stew served with injera", 450, "Lunch", True),
            ("Kitfo", "Minced raw beef seasoned with mitmita and niter kibbeh", 500, "Lunch", False),
            ("Chechebsa", "Shredded flatbread mixed with berbere and clarified butter", 250, "Breakfast", False),
            ("Tibs", "Sautéed beef or lamb with onions and peppers", 400, "Dinner", False),
            ("Macchiato", "Espresso with a dollop of steamed milk foam", 80, "Drinks", False),
        ]
        for name, description, price, category, special in foods_data:
            db.session.add(
                MenuItem(
                    name=name,
                    description=description,
                    price=price,
                    category=category,
                    is_special=special,
                )
            )

    if SiteSetting.query.first() is None:
        db.session.add(SiteSetting())

    db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        create_data()
        app.logger.info("Database initialized")


# HTML routes
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/rooms")
def rooms_page():
    return render_template("rooms.html")


@app.route("/booking")
def booking_page():
    return render_template("booking.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/admin")
@login_required
def admin_page():
    if not current_user.is_admin:
        return render_template("404.html"), 404
    return render_template("admin.html")


@app.route("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")


@app.route("/reset-password")
def reset_password_page():
    return render_template("reset_password.html")


@app.route("/contact")
def contact_page():
    return render_template("contact.html")


@app.route("/restaurant")
def restaurant_page():
    return render_template("restaurant.html")


@app.route("/gallery")
def gallery_page():
    return render_template("gallery.html")


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    db.session.rollback()
    app.logger.exception("Internal server error")
    return render_template("500.html"), 500


# Authentication APIs
@csrf.exempt
@app.route("/api/register", methods=["POST", "OPTIONS"])
def register():
    if request.method == "OPTIONS":
        return "", 200

    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all(isinstance(value, str) and value.strip()
               for value in (username, email, password)):
        return jsonify({"error": "Username, email and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400

    if "@" not in email:
        return jsonify({"error": "Invalid email address"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    try:
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            is_admin=False,
        )
        db.session.add(user)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Registration failed")
        return jsonify({"error": "Registration could not be completed"}), 500

    return jsonify({"message": "Registration successful!"}), 201


@app.route("/api/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return "", 200

    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    username = data.get("username", "")
    password = data.get("password", "")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "Invalid username or password"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid username or password"}), 401

    login_user(user, remember=True)
    session["user_id"] = user.id
    session.permanent = True

    return jsonify({
        "message": "Login successful!",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
        },
    }), 200


@app.route("/api/logout", methods=["POST"])
@api_login_required
def logout():
    logout_user()
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200


@app.route("/api/profile", methods=["GET", "PUT"])
@api_login_required
def user_profile():
    if request.method == "GET":
        return jsonify({
            "username": current_user.username,
            "email": current_user.email,
            "phone": current_user.phone,
            "is_admin": current_user.is_admin,
        }), 200

    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    if data.get("email"):
        current_user.email = data["email"]
    if data.get("phone") is not None:
        current_user.phone = data["phone"]

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Profile update failed")
        return jsonify({"error": "Could not update profile"}), 500

    return jsonify({"message": "Profile updated successfully"}), 200


@app.route("/api/change-password", methods=["POST"])
@api_login_required
def change_password():
    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not isinstance(current_password, str) or not isinstance(new_password, str):
        return jsonify({"error": "Invalid password data"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters long"}), 400
    if not check_password_hash(current_user.password, current_password):
        return jsonify({"error": "Current password is incorrect"}), 401

    current_user.password = generate_password_hash(new_password)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Password change failed")
        return jsonify({"error": "Could not change password"}), 500

    return jsonify({"message": "Password changed successfully"}), 200


# Public data APIs
@app.route("/api/rooms", methods=["GET"])
def get_rooms():
    rooms = Room.query.all()
    result = []
    for room in rooms:
        images = [image.image_filename for image in room.images]
        if not images and room.image_filename:
            images = [room.image_filename]
        result.append({
            "id": room.id,
            "room_number": room.room_number,
            "room_type": room.room_type,
            "price": room.price,
            "description": room.description,
            "available": room.available,
            "image_filename": room.image_filename,
            "images": images,
            "is_featured": room.is_featured,
            "amenities": room.amenities,
        })
    return jsonify(result), 200


@app.route("/api/rooms/<int:room_id>", methods=["GET"])
def get_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    images = [image.image_filename for image in room.images]
    if not images and room.image_filename:
        images = [room.image_filename]

    return jsonify({
        "id": room.id,
        "room_number": room.room_number,
        "room_type": room.room_type,
        "price": room.price,
        "description": room.description,
        "available": room.available,
        "image_filename": room.image_filename,
        "images": images,
        "is_featured": room.is_featured,
        "amenities": room.amenities,
    }), 200


@app.route("/api/reviews/<int:room_id>", methods=["GET"])
def get_room_reviews(room_id):
    reviews = Review.query.filter_by(room_id=room_id).order_by(
        Review.created_at.desc()
    ).all()
    return jsonify([
        {
            "id": review.id,
            "author": review.author.username,
            "rating": review.rating,
            "comment": review.comment,
            "date": review.created_at.strftime("%Y-%m-%d"),
        }
        for review in reviews
    ]), 200


@app.route("/api/menu", methods=["GET"])
def get_menu():
    items = MenuItem.query.all()
    return jsonify([
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "category": item.category,
            "image_filename": item.image_filename,
            "is_special": item.is_special,
        }
        for item in items
    ]), 200


@app.route("/api/settings", methods=["GET"])
def get_settings():
    setting = SiteSetting.query.first()
    if not setting:
        return jsonify({
            "whatsapp": "",
            "telegram": "",
            "gmail": "",
            "address": "",
        }), 200

    return jsonify({
        "whatsapp": setting.whatsapp,
        "telegram": setting.telegram,
        "gmail": setting.gmail,
        "address": setting.address,
    }), 200


@app.route("/api/check-availability", methods=["POST"])
def check_availability():
    data = get_json_data()
    if not data or not data.get("check_in") or not data.get("check_out"):
        return jsonify({"error": "Check-in and check-out dates are required"}), 400

    try:
        check_in = datetime.strptime(data["check_in"], "%Y-%m-%d")
        check_out = datetime.strptime(data["check_out"], "%Y-%m-%d")
    except (TypeError, ValueError):
        return jsonify({"error": "Dates must use YYYY-MM-DD format"}), 400

    if check_out <= check_in:
        return jsonify({"error": "Check-out must be after check-in"}), 400

    overlapping = Booking.query.filter(
        Booking.status == "confirmed",
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    ).all()
    booked_room_ids = [booking.room_id for booking in overlapping]

    query = Room.query
    if booked_room_ids:
        query = query.filter(Room.id.notin_(booked_room_ids))

    result = []
    for room in query.all():
        images = [image.image_filename for image in room.images]
        if not images and room.image_filename:
            images = [room.image_filename]
        result.append({
            "id": room.id,
            "room_number": room.room_number,
            "room_type": room.room_type,
            "price": room.price,
            "description": room.description,
            "image_filename": room.image_filename,
            "images": images,
            "is_featured": room.is_featured,
            "amenities": room.amenities,
        })
    return jsonify(result), 200


# Booking APIs
@app.route("/api/bookings", methods=["POST"])
@api_login_required
def create_booking():
    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    required = ("room_id", "check_in", "check_out", "guest_name")
    if any(not data.get(field) for field in required):
        return jsonify({"error": "Room, dates and guest name are required"}), 400

    try:
        room_id = int(data["room_id"])
        check_in = datetime.strptime(data["check_in"], "%Y-%m-%d")
        check_out = datetime.strptime(data["check_out"], "%Y-%m-%d")
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid room ID or date format"}), 400

    if check_out <= check_in:
        return jsonify({"error": "Check-out must be after check-in"}), 400

    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    overlapping = Booking.query.filter(
        Booking.room_id == room.id,
        Booking.status == "confirmed",
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    ).first()
    if overlapping:
        return jsonify({"error": "Room is already booked for these dates"}), 400

    nights = (check_out - check_in).days
    total = nights * room.price
    booking = Booking(
        user_id=current_user.id,
        room_id=room.id,
        guest_name=data["guest_name"].strip(),
        guest_phone=data.get("guest_phone", ""),
        check_in=check_in,
        check_out=check_out,
        total_price=total,
        status="confirmed",
    )

    try:
        db.session.add(booking)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Booking creation failed")
        return jsonify({"error": "Could not create booking"}), 500

    return jsonify({
        "message": "Booking confirmed!",
        "booking_id": booking.id,
        "total_price": total,
        "nights": nights,
    }), 201


@app.route("/api/my-bookings", methods=["GET", "OPTIONS"])
@api_login_required
def get_my_bookings():
    if request.method == "OPTIONS":
        return "", 200

    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return jsonify([
        {
            "id": booking.id,
            "room_id": booking.room_id,
            "room_number": booking.room.room_number,
            "room_type": booking.room.room_type,
            "guest_name": booking.guest_name,
            "check_in": booking.check_in.strftime("%Y-%m-%d"),
            "check_out": booking.check_out.strftime("%Y-%m-%d"),
            "total_price": booking.total_price,
            "status": booking.status,
        }
        for booking in bookings
    ]), 200


@app.route("/api/bookings/<int:booking_id>/cancel", methods=["POST"])
@api_login_required
def cancel_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if booking.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    if booking.status == "cancelled":
        return jsonify({"error": "Booking already cancelled"}), 400

    booking.status = "cancelled"
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Booking cancellation failed")
        return jsonify({"error": "Could not cancel booking"}), 500

    return jsonify({"message": "Booking cancelled successfully"}), 200


# Cart APIs
@app.route("/api/cart", methods=["GET"])
@api_login_required
def get_cart():
    cart = CartItem.query.filter_by(user_id=current_user.id).all()
    return jsonify([
        {
            "id": item.id,
            "name": item.menu_item.name,
            "price": item.menu_item.price,
            "quantity": item.quantity,
            "image": item.menu_item.image_filename,
        }
        for item in cart
    ]), 200


@app.route("/api/cart/add", methods=["POST"])
@api_login_required
def add_to_cart():
    data = get_json_data()
    if not data or data.get("menu_item_id") is None:
        return jsonify({"error": "Menu item ID is required"}), 400

    try:
        menu_item_id = int(data["menu_item_id"])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid menu item ID"}), 400

    menu_item = db.session.get(MenuItem, menu_item_id)
    if not menu_item:
        return jsonify({"error": "Menu item not found"}), 404

    item = CartItem.query.filter_by(
        user_id=current_user.id,
        menu_item_id=menu_item_id,
    ).first()

    if item:
        item.quantity += 1
    else:
        db.session.add(CartItem(
            user_id=current_user.id,
            menu_item_id=menu_item_id,
            quantity=1,
        ))

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Adding item to cart failed")
        return jsonify({"error": "Could not update cart"}), 500

    return jsonify({"message": "Added to cart!"}), 200


@app.route("/api/cart/remove/<int:cart_id>", methods=["DELETE"])
@api_login_required
def remove_from_cart(cart_id):
    item = db.session.get(CartItem, cart_id)
    if not item or item.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(item)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Cart removal failed")
        return jsonify({"error": "Could not remove item"}), 500

    return jsonify({"message": "Removed"}), 200


@app.route("/api/cart/checkout", methods=["POST"])
@api_login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400

    data = get_json_data() or {}
    room_number = data.get("room_number", "")
    total = sum(item.menu_item.price * item.quantity for item in cart_items)
    items_summary = json.dumps([
        {"name": item.menu_item.name, "qty": item.quantity}
        for item in cart_items
    ])

    order = FoodOrder(
        user_id=current_user.id,
        total_price=total,
        items=items_summary,
        room_number=room_number,
    )
    try:
        db.session.add(order)
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Checkout failed")
        return jsonify({"error": "Could not place order"}), 500

    return jsonify({"message": "Order placed successfully!", "total": total}), 201


@app.route("/api/my-food-orders", methods=["GET"])
@api_login_required
def get_my_food_orders():
    orders = FoodOrder.query.filter_by(user_id=current_user.id).order_by(
        FoodOrder.created_at.desc()
    ).all()
    return jsonify([
        {
            "id": order.id,
            "total": order.total_price,
            "room": order.room_number,
            "items": order.items,
            "status": order.status,
            "date": order.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for order in orders
    ]), 200


# Table reservation APIs
@app.route("/api/table-reservations", methods=["POST"])
@api_login_required
def book_table():
    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    required = ("guest_name", "phone", "date", "time", "guests")
    if any(data.get(field) in (None, "") for field in required):
        return jsonify({"error": "All reservation fields are required"}), 400

    try:
        reservation_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
        guests = int(data["guests"])
        if guests < 1:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid date or guest count"}), 400

    reservation = TableReservation(
        user_id=current_user.id,
        guest_name=data["guest_name"],
        phone=data["phone"],
        date=reservation_date,
        time=data["time"],
        guests=guests,
    )

    try:
        db.session.add(reservation)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Table reservation failed")
        return jsonify({"error": "Could not create reservation"}), 500

    return jsonify({"message": "Table reservation requested!"}), 201


# Food receipt PDF
@app.route("/api/food-orders/<int:order_id>/receipt", methods=["GET"])
@api_login_required
def food_receipt(order_id):
    order = db.session.get(FoodOrder, order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    elements = []
    styles = getSampleStyleSheet()
    gold = colors.HexColor("#D4AF37")
    silver = colors.HexColor("#C0C0C0")
    red = colors.HexColor("#e74c3c")

    title_style = ParagraphStyle(
        "ReceiptTitle", parent=styles["Heading1"], alignment=TA_CENTER,
        textColor=gold, fontSize=24, spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle", parent=styles["Normal"], alignment=TA_CENTER,
        textColor=silver, fontSize=12, spaceAfter=20
    )
    red_style = ParagraphStyle(
        "ReceiptTotal", parent=styles["Normal"],
        textColor=red, fontName="Helvetica-Bold"
    )

    elements.append(Paragraph("<b>YADA HOTEL</b>", title_style))
    elements.append(Paragraph("Ethiopian Hospitality at its Finest", subtitle_style))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Food Order Receipt</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    user = db.session.get(User, order.user_id)
    details = [
        ["Order ID:", f"#{order.id}"],
        ["Date:", order.created_at.strftime("%Y-%m-%d %H:%M")],
        ["Customer:", user.username if user else "Customer"],
        ["Room Service:", order.room_number or "Takeaway"],
        ["Status:", order.status.upper()],
    ]
    table = Table(details, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), silver),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.black),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 1, gold),
        ("PADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    items_data = [["Qty", "Item Name"]]
    try:
        order_items = json.loads(order.items or "[]")
    except (TypeError, ValueError):
        order_items = []

    for item in order_items:
        items_data.append([str(item.get("qty", "")), str(item.get("name", ""))])

    items_table = Table(items_data, colWidths=[50, 400])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), gold),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 1, silver),
        ("PADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        f"<b>Total: {order.total_price:,.2f} ETB</b>", red_style
    ))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(
        "<i>Thank you for dining with us!</i>", styles["Normal"]
    ))

    doc.build(elements)
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Food_Receipt_{order.id}.pdf"},
    )


# Gallery APIs
@app.route("/api/gallery", methods=["GET"])
def get_gallery():
    images = GalleryImage.query.order_by(GalleryImage.created_at.desc()).all()
    return jsonify([
        {
            "id": image.id,
            "title": image.title,
            "image_filename": image.image_filename,
        }
        for image in images
    ]), 200


@app.route("/api/admin/gallery", methods=["POST"])
@admin_required
def admin_add_gallery():
    title = (request.form.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Image title is required"}), 400

    upload = request.files.get("image")
    filename = save_uploaded_file(upload, "gallery") if upload else None
    if not filename:
        return jsonify({"error": "A valid image file is required"}), 400

    image = GalleryImage(title=title, image_filename=filename)
    try:
        db.session.add(image)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Gallery upload failed")
        return jsonify({"error": "Could not save gallery image"}), 500

    return jsonify({"message": "Image added to gallery!"}), 201


@app.route("/api/admin/gallery/<int:image_id>", methods=["DELETE"])
@admin_required
def admin_delete_gallery(image_id):
    image = db.session.get(GalleryImage, image_id)
    if not image:
        return jsonify({"error": "Not found"}), 404

    try:
        db.session.delete(image)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Gallery deletion failed")
        return jsonify({"error": "Could not delete gallery image"}), 500

    return jsonify({"message": "Image deleted"}), 200


# Admin APIs
@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    return jsonify({
        "total_rooms": Room.query.count(),
        "available_rooms": Room.query.filter_by(available=True).count(),
        "total_bookings": Booking.query.count(),
        "total_revenue": db.session.query(
            db.func.sum(Booking.total_price)
        ).scalar() or 0,
        "total_guests": User.query.count(),
    }), 200


@app.route("/api/admin/chart-data", methods=["GET"])
@admin_required
def admin_chart_data():
    today = datetime.utcnow().date()
    labels, values = [], []

    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        labels.append(day.strftime("%b %d"))
        start = datetime.combine(day, datetime.min.time())
        end = datetime.combine(day, datetime.max.time())
        revenue = db.session.query(
            db.func.sum(Booking.total_price)
        ).filter(
            Booking.status == "confirmed",
            Booking.check_in >= start,
            Booking.check_in <= end,
        ).scalar() or 0
        values.append(revenue)

    return jsonify({"labels": labels, "data": values}), 200


@app.route("/api/admin/bookings", methods=["GET"])
@admin_required
def admin_bookings():
    bookings = Booking.query.all()
    return jsonify([
        {
            "id": booking.id,
            "room_number": booking.room.room_number,
            "guest_name": booking.guest_name,
            "check_in": booking.check_in.strftime("%Y-%m-%d"),
            "check_out": booking.check_out.strftime("%Y-%m-%d"),
            "total_price": booking.total_price,
            "status": booking.status,
        }
        for booking in bookings
    ]), 200


@app.route("/api/admin/reviews", methods=["GET"])
@admin_required
def admin_reviews():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return jsonify([
        {
            "id": review.id,
            "room_number": review.room.room_number,
            "author": review.author.username,
            "rating": review.rating,
            "comment": review.comment,
            "date": review.created_at.strftime("%Y-%m-%d"),
        }
        for review in reviews
    ]), 200


@app.route("/api/admin/guests", methods=["GET"])
@admin_required
def admin_guests():
    users = User.query.all()
    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "total_bookings": Booking.query.filter_by(user_id=user.id).count(),
        }
        for user in users
    ]), 200


@app.route("/api/admin/settings", methods=["GET", "PUT"])
@admin_required
def admin_settings():
    setting = SiteSetting.query.first()
    if not setting:
        setting = SiteSetting()
        db.session.add(setting)
        db.session.commit()

    if request.method == "GET":
        return jsonify({
            "whatsapp": setting.whatsapp,
            "telegram": setting.telegram,
            "gmail": setting.gmail,
            "address": setting.address,
        }), 200

    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    for key in ("whatsapp", "telegram", "gmail", "address"):
        if key in data:
            setattr(setting, key, data[key])

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Settings update failed")
        return jsonify({"error": "Could not update settings"}), 500

    return jsonify({"message": "Settings updated successfully"}), 200


@app.route("/api/admin/calendar", methods=["GET"])
@admin_required
def admin_calendar():
    bookings = Booking.query.filter_by(status="confirmed").all()
    events = []

    for booking in bookings:
        color = "#3788d8"
        if booking.room.room_type == "Deluxe":
            color = "#27ae60"
        elif booking.room.room_type == "Suite":
            color = "#8e44ad"

        events.append({
            "title": f"Room {booking.room.room_number} - {booking.guest_name}",
            "start": booking.check_in.strftime("%Y-%m-%d"),
            "end": booking.check_out.strftime("%Y-%m-%d"),
            "backgroundColor": color,
            "borderColor": color,
        })

    return jsonify(events), 200


@app.route("/api/admin/food-orders", methods=["GET"])
@admin_required
def admin_food_orders():
    orders = FoodOrder.query.order_by(FoodOrder.created_at.desc()).all()
    return jsonify([
        {
            "id": order.id,
            "user": order.user.username,
            "total": order.total_price,
            "room": order.room_number,
            "items": order.items,
            "status": order.status,
            "date": order.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for order in orders
    ]), 200


@app.route("/api/admin/food-orders/<int:order_id>", methods=["PUT"])
@admin_required
def admin_update_food_order(order_id):
    order = db.session.get(FoodOrder, order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    if "status" in data:
        order.status = data["status"]

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Food order update failed")
        return jsonify({"error": "Could not update order"}), 500

    return jsonify({"message": "Order status updated!"}), 200


@app.route("/api/admin/table-reservations", methods=["GET"])
@admin_required
def admin_get_reservations():
    reservations = TableReservation.query.order_by(
        TableReservation.date.desc()
    ).all()
    return jsonify([
        {
            "id": reservation.id,
            "name": reservation.guest_name,
            "phone": reservation.phone,
            "date": reservation.date.strftime("%Y-%m-%d"),
            "time": reservation.time,
            "guests": reservation.guests,
            "status": reservation.status,
        }
        for reservation in reservations
    ]), 200


@app.route("/api/admin/table-reservations/<int:res_id>", methods=["PUT"])
@admin_required
def admin_update_reservation(res_id):
    reservation = db.session.get(TableReservation, res_id)
    if not reservation:
        return jsonify({"error": "Not found"}), 404

    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    if "status" in data:
        reservation.status = data["status"]

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Reservation update failed")
        return jsonify({"error": "Could not update reservation"}), 500

    return jsonify({"message": "Status updated"}), 200


@app.route("/api/admin/rooms", methods=["POST"])
@admin_required
def admin_add_room():
    room_number = (request.form.get("room_number") or "").strip()
    room_type = (request.form.get("room_type") or "").strip()
    description = request.form.get("description", "")
    amenities = request.form.get("amenities", "")
    is_featured = request.form.get("is_featured") == "true"

    if not room_number or not room_type:
        return jsonify({"error": "Room number and type are required"}), 400

    try:
        price = float(request.form.get("price", ""))
        if price < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid non-negative price"}), 400

    if Room.query.filter_by(room_number=room_number).first():
        return jsonify({"error": "Room number already exists"}), 400

    saved_filenames = []
    for upload in request.files.getlist("images"):
        if upload and upload.filename:
            filename = save_uploaded_file(upload, "room")
            if filename:
                saved_filenames.append(filename)

    image_filename = saved_filenames[0] if saved_filenames else "default_room.jpg"
    room = Room(
        room_number=room_number,
        room_type=room_type,
        price=price,
        description=description,
        available=True,
        image_filename=image_filename,
        is_featured=is_featured,
        amenities=amenities,
    )

    try:
        db.session.add(room)
        db.session.flush()
        for filename in saved_filenames:
            db.session.add(RoomImage(room_id=room.id, image_filename=filename))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Room creation failed")
        return jsonify({"error": "Could not add room"}), 500

    return jsonify({"message": "Room added with gallery!"}), 201


@app.route("/api/admin/rooms/<int:room_id>/edit", methods=["POST"])
@admin_required
def admin_edit_room_with_image(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    room_number = request.form.get("room_number", room.room_number)
    room_type = request.form.get("room_type", room.room_type)
    description = request.form.get("description", room.description)
    amenities = request.form.get("amenities", room.amenities)

    if not room_number or not room_type:
        return jsonify({"error": "Room number and type are required"}), 400

    try:
        price = float(request.form.get("price", room.price))
        if price < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid non-negative price"}), 400

    duplicate = Room.query.filter(
        Room.room_number == room_number,
        Room.id != room.id,
    ).first()
    if duplicate:
        return jsonify({"error": "Room number already exists"}), 400

    room.room_number = room_number
    room.room_type = room_type
    room.price = price
    room.description = description
    room.amenities = amenities

    if "is_featured" in request.form:
        room.is_featured = request.form.get("is_featured") == "true"

    upload = request.files.get("image")
    if upload and upload.filename:
        filename = save_uploaded_file(upload, "room")
        if not filename:
            return jsonify({"error": "Invalid image filename"}), 400
        room.image_filename = filename
        db.session.add(RoomImage(room_id=room.id, image_filename=filename))

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Room update failed")
        return jsonify({"error": "Could not update room"}), 500

    return jsonify({"message": "Room updated with new image!"}), 200


@app.route("/api/admin/rooms/<int:room_id>", methods=["PUT", "DELETE"])
@admin_required
def admin_manage_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    if request.method == "DELETE":
        try:
            db.session.delete(room)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Room deletion failed")
            return jsonify({"error": "Could not delete room"}), 500
        return jsonify({"message": "Room deleted"}), 200

    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    for key in ("room_number", "room_type", "price", "description", "is_featured", "amenities"):
        if key in data:
            setattr(room, key, data[key])

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Room update failed")
        return jsonify({"error": "Could not update room"}), 500

    return jsonify({"message": "Room updated"}), 200


@app.route("/api/admin/menu", methods=["POST"])
@admin_required
def admin_add_menu():
    name = (request.form.get("name") or "").strip()
    description = request.form.get("description", "")
    category = (request.form.get("category") or "").strip()
    is_special = request.form.get("is_special") == "true"

    if not name or not category:
        return jsonify({"error": "Food name and category are required"}), 400

    try:
        price = float(request.form.get("price", ""))
        if price < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid non-negative price"}), 400

    filename = None
    upload = request.files.get("image")
    if upload and upload.filename:
        filename = save_uploaded_file(upload, "menu")
        if not filename:
            return jsonify({"error": "Invalid image filename"}), 400

    item = MenuItem(
        name=name,
        description=description,
        price=price,
        category=category,
        image_filename=filename,
        is_special=is_special,
    )

    try:
        if is_special:
            MenuItem.query.update({MenuItem.is_special: False})
        db.session.add(item)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Menu item creation failed")
        return jsonify({"error": "Could not add menu item"}), 500

    return jsonify({"message": "Menu item added!"}), 201


@app.route("/api/admin/menu/<int:item_id>/edit", methods=["POST"])
@admin_required
def admin_edit_menu(item_id):
    item = db.session.get(MenuItem, item_id)
    if not item:
        return jsonify({"error": "Menu item not found"}), 404

    name = (request.form.get("name") or "").strip()
    description = request.form.get("description", item.description or "").strip()
    category = (request.form.get("category") or "").strip()

    if not name:
        return jsonify({"error": "Food name is required"}), 400
    if not category:
        return jsonify({"error": "Category is required"}), 400

    try:
        price = float(request.form.get("price", ""))
        if price < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid non-negative price"}), 400

    is_special = request.form.get("is_special", "false").lower() == "true"
    upload = request.files.get("image")

    if upload and upload.filename:
        filename = save_uploaded_file(upload, f"menu_{item.id}")
        if not filename:
            return jsonify({"error": "Invalid image filename"}), 400
        item.image_filename = filename

    item.name = name
    item.description = description
    item.price = price
    item.category = category
    item.is_special = is_special

    try:
        if is_special:
            MenuItem.query.filter(MenuItem.id != item.id).update(
                {MenuItem.is_special: False},
                synchronize_session=False,
            )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Failed to update menu item %s", item_id)
        return jsonify({"error": "Could not save menu item changes"}), 500

    return jsonify({"message": "Menu item updated successfully"}), 200


@app.route("/api/admin/menu/<int:item_id>", methods=["DELETE"])
@admin_required
def admin_delete_menu(item_id):
    item = db.session.get(MenuItem, item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    try:
        db.session.delete(item)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Menu item deletion failed")
        return jsonify({"error": "Could not delete menu item"}), 500

    return jsonify({"message": "Item deleted"}), 200


@app.route("/api/admin/export/bookings/pdf", methods=["GET"])
@admin_required
def export_bookings_pdf():
    bookings = Booking.query.all()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("YADA HOTEL - Booking Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    data = [[
        "ID", "Room", "Guest Name", "Check-in", "Check-out",
        "Total (ETB)", "Status"
    ]]
    for booking in bookings:
        data.append([
            str(booking.id),
            booking.room.room_number,
            booking.guest_name,
            booking.check_in.strftime("%Y-%m-%d"),
            booking.check_out.strftime("%Y-%m-%d"),
            f"{booking.total_price:,.2f}",
            booking.status.upper(),
        ])

    table = Table(data, colWidths=[40, 50, 120, 80, 80, 80, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=yada_hotel_bookings.pdf"},
    )


@app.route("/api/admin/food-orders/<int:order_id>/ticket", methods=["GET"])
@admin_required
def kitchen_ticket(order_id):
    order = db.session.get(FoodOrder, order_id)
    if not order:
        return jsonify({"error": "Not found"}), 404

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(3.15 * inch, 5 * inch),
        rightMargin=10,
        leftMargin=10,
        topMargin=10,
        bottomMargin=10,
    )
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>KITCHEN TICKET</b>", styles["Title"]))
    elements.append(Paragraph(f"Order #{order.id}", styles["Normal"]))
    elements.append(Paragraph(
        f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}",
        styles["Normal"],
    ))

    if order.room_number:
        elements.append(Paragraph(
            f"<b>ROOM SERVICE: {order.room_number}</b>", styles["Normal"]
        ))

    elements.append(Spacer(1, 10))
    try:
        items = json.loads(order.items or "[]")
    except (TypeError, ValueError):
        items = []

    for item in items:
        elements.append(Paragraph(
            f"<b>{item.get('qty', '')}x</b> {item.get('name', '')}",
            styles["Normal"],
        ))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "<b>DO NOT DELIVER WITHOUT PAYMENT</b>", styles["Normal"]
    ))
    doc.build(elements)
    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Ticket_{order.id}.pdf"},
    )


@csrf.exempt
@app.route("/api/contact", methods=["POST"])
def submit_contact():
    data = get_json_data()
    if not data:
        return jsonify({"error": "A valid JSON request is required"}), 400

    name = data.get("name")
    email = data.get("email")
    message = data.get("message")

    if not all(isinstance(value, str) and value.strip()
               for value in (name, email, message)):
        return jsonify({"error": "Name, email and message are required"}), 400

    contact_message = ContactMessage(
        name=name.strip(),
        email=email.strip(),
        message=message.strip(),
    )

    try:
        db.session.add(contact_message)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Contact message submission failed")
        return jsonify({"error": "Could not submit contact message"}), 500

    return jsonify({"message": "Message sent successfully!"}), 201


# Error handling
@app.errorhandler(400)
def handle_bad_request(error):
    description = getattr(error, "description", "Bad request.")
    if request.path.startswith("/api/"):
        return jsonify({"error": description}), 400
    return render_template("404.html"), 400


@app.errorhandler(413)
def handle_file_too_large(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Uploaded file exceeds the 10 MB limit"}), 413
    return "Uploaded file is too large.", 413


if __name__ == "__main__":
    init_db()
    is_debug = os.environ.get("FLASK_DEBUG", "False").lower() in (
        "true", "1", "t"
    )
    app.run(host="127.0.0.1", port=5002, debug=is_debug)
