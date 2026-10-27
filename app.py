from flask import Flask, request, jsonify, session, render_template, Response
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from models import db, User, Room, Booking, Review, RoomImage, ContactMessage, SiteSetting, MenuItem
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os
import io
import secrets
from werkzeug.utils import secure_filename
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = 'yada-hotel-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yada_hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_test_email@gmail.com' 
app.config['MAIL_PASSWORD'] = 'your_app_password'         
app.config['MAIL_DEFAULT_SENDER'] = 'yada.hotel@example.com'
mail = Mail(app)

db.init_app(app)
CORS(app, supports_credentials=True, origins=['*'])

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None
login_manager.login_message = None

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS': return '', 200
        if not current_user.is_authenticated: return jsonify({'error': 'Please login first'}), 401
        return f(*args, **kwargs)
    return decorated_function

def create_rooms():
    rooms_data = [
        {'number': '101', 'type': 'Standard', 'price': 2000, 'desc': 'Cozy room with city view'},
        {'number': '102', 'type': 'Standard', 'price': 2000, 'desc': 'Comfortable room with garden view'},
        {'number': '103', 'type': 'Deluxe', 'price': 3500, 'desc': 'Spacious room with balcony'},
        {'number': '104', 'type': 'Deluxe', 'price': 3500, 'desc': 'Elegant room with mountain view'},
        {'number': '105', 'type': 'Suite', 'price': 5000, 'desc': 'Luxury suite with living room'},
        {'number': '106', 'type': 'Standard', 'price': 2200, 'desc': 'Modern room with workspace'},
        {'number': '107', 'type': 'Deluxe', 'price': 3800, 'desc': 'Premium room with ocean view'},
        {'number': '108', 'type': 'Suite', 'price': 5500, 'desc': 'Executive suite with jacuzzi'},
        {'number': '109', 'type': 'Standard', 'price': 2500, 'desc': 'Family room with extra bed'},
        {'number': '110', 'type': 'Standard', 'price': 2500, 'desc': 'Twin beds with city view'},
        {'number': '111', 'type': 'Deluxe', 'price': 4000, 'desc': 'Corner room with panoramic view'},
        {'number': '112', 'type': 'Deluxe', 'price': 4200, 'desc': 'Family deluxe with kitchenette'},
        {'number': '113', 'type': 'Suite', 'price': 6000, 'desc': 'Presidential suite with private balcony'}
    ]
    for room_data in rooms_data:
        room = Room.query.filter_by(room_number=room_data['number']).first()
        if not room:
            new_room = Room(room_number=room_data['number'], room_type=room_data['type'], price=room_data['price'], description=room_data['desc'], available=True)
            db.session.add(new_room)
    
    if not SiteSetting.query.first():
        db.session.add(SiteSetting())
        
    db.session.commit()

def init_db():
    with app.app_context():
        db.create_all()
        create_rooms()
        print("✅ Database initialized!")

@app.route('/')
def home(): return render_template('index.html')
@app.route('/rooms')
def rooms_page(): return render_template('rooms.html')
@app.route('/booking')
def booking_page(): return render_template('booking.html')
@app.route('/login')
def login_page(): return render_template('login.html')
@app.route('/register')
def register_page(): return render_template('register.html')
@app.route('/dashboard')
def dashboard_page(): return render_template('dashboard.html')
@app.route('/admin')
def admin_page(): return render_template('admin.html')
@app.route('/forgot-password')
def forgot_password_page(): return render_template('forgot_password.html')
@app.route('/reset-password')
def reset_password_page(): return render_template('reset_password.html')
@app.route('/contact')
def contact_page(): return render_template('contact.html')
@app.route('/restaurant')
def restaurant_page(): return render_template('restaurant.html') # NEW PAGE

# ===== NEW: RESTAURANT API ROUTES =====
@app.route('/api/menu', methods=['GET'])
def get_menu():
    items = MenuItem.query.all()
    return jsonify([{
        'id': i.id, 'name': i.name, 'description': i.description, 'price': i.price, 
        'category': i.category, 'image_filename': i.image_filename, 'is_special': i.is_special
    } for i in items]), 200

@app.route('/api/admin/menu', methods=['POST'])
@api_login_required
def admin_add_menu_item():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price')
    category = request.form.get('category')
    is_special = True if request.form.get('is_special') == 'true' else False
    
    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

    new_item = MenuItem(name=name, description=description, price=price, category=category, image_filename=image_filename, is_special=is_special)
    
    # If marked as special, unmark all others
    if is_special:
        MenuItem.query.update({MenuItem.is_special: False})
        
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'message': 'Menu item added!'}), 201

@app.route('/api/admin/menu/<int:item_id>', methods=['DELETE'])
@api_login_required
def admin_delete_menu_item(item_id):
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    item = db.session.get(MenuItem, item_id)
    if not item: return jsonify({'error': 'Item not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item deleted'}), 200

# ===== EXISTING ROUTES (Unchanged) =====
@app.route('/api/settings', methods=['GET'])
def get_settings():
    s = SiteSetting.query.first()
    if not s: return jsonify({'whatsapp': '', 'telegram': '', 'gmail': '', 'address': ''}), 200
    return jsonify({'whatsapp': s.whatsapp, 'telegram': s.telegram, 'gmail': s.gmail, 'address': s.address}), 200

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    if User.query.filter_by(username=data.get('username')).first(): return jsonify({'error': 'Username already exists'}), 400
    hashed_password = generate_password_hash(data['password'])
    user = User(username=data['username'], email=data['email'], password=hashed_password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Registration successful!'}), 201

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if not user or not check_password_hash(user.password, data.get('password')): return jsonify({'error': 'Invalid username or password'}), 401
    login_user(user, remember=True)
    session['user_id'] = user.id
    session.permanent = True
    return jsonify({'message': 'Login successful!', 'user': {'id': user.id, 'username': user.username, 'email': user.email}}), 200

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    if not user: return jsonify({'message': 'If that email exists, a reset link has been sent.'}), 200
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiration = datetime.utcnow() + timedelta(minutes=15)
    db.session.commit()
    reset_link = f"http://127.0.0.1:5000/reset-password?token={token}"
    try:
        msg = Message(subject="Password Reset - YADA HOTEL", recipients=[email])
        msg.body = f"Hello {user.username},\n\nYou requested a password reset. Click the link below to reset your password:\n\n{reset_link}\n\nThis link expires in 15 minutes."
        mail.send(msg)
    except Exception as e:
        print(f"\n⚠️ Could not send actual email. Printing to terminal instead:\nTo: {email}\nSubject: Password Reset\nBody: Click here to reset: {reset_link}\n")
    return jsonify({'message': 'If that email exists, a reset link has been sent.'}), 200

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.reset_token_expiration < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired reset token.'}), 400
    user.password = generate_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expiration = None
    db.session.commit()
    return jsonify({'message': 'Password has been reset successfully!'}), 200

@app.route('/api/logout', methods=['POST'])
@api_login_required
def logout():
    logout_user()
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/profile', methods=['GET', 'PUT'])
@api_login_required
def user_profile():
    if request.method == 'GET':
        return jsonify({'username': current_user.username, 'email': current_user.email, 'phone': current_user.phone}), 200
    if request.method == 'PUT':
        data = request.get_json()
        if data.get('email'): current_user.email = data['email']
        if data.get('phone') is not None: current_user.phone = data['phone']
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'}), 200

@app.route('/api/change-password', methods=['POST'])
@api_login_required
def change_password():
    data = request.get_json()
    if not check_password_hash(current_user.password, data.get('current_password')):
        return jsonify({'error': 'Current password is incorrect'}), 401
    current_user.password = generate_password_hash(data.get('new_password'))
    db.session.commit()
    return jsonify({'message': 'Password changed successfully'}), 200

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms = Room.query.all()
    rooms_data = []
    for r in rooms:
        images = [img.image_filename for img in r.images] 
        if not images: images = [r.image_filename]
        rooms_data.append({'id': r.id, 'room_number': r.room_number, 'room_type': r.room_type, 'price': r.price, 'description': r.description, 'available': r.available, 'image_filename': r.image_filename, 'images': images, 'is_featured': r.is_featured, 'amenities': r.amenities})
    return jsonify(rooms_data), 200

@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    room = db.session.get(Room, room_id)
    if not room: return jsonify({'error': 'Room not found'}), 404
    images = [img.image_filename for img in room.images]
    if not images: images = [room.image_filename]
    return jsonify({'id': room.id, 'room_number': room.room_number, 'room_type': room.room_type, 'price': room.price, 'description': room.description, 'available': room.available, 'image_filename': room.image_filename, 'images': images, 'is_featured': room.is_featured, 'amenities': room.amenities}), 200

@app.route('/api/check-availability', methods=['POST'])
def check_availability():
    data = request.get_json()
    check_in = datetime.strptime(data['check_in'], '%Y-%m-%d')
    check_out = datetime.strptime(data['check_out'], '%Y-%m-%d')
    overlapping_bookings = Booking.query.filter(Booking.status == 'confirmed', Booking.check_in < check_out, Booking.check_out > check_in).all()
    booked_room_ids = [b.room_id for b in overlapping_bookings]
    available_rooms = Room.query.filter(Room.id.notin_(booked_room_ids)).all()
    rooms_data = []
    for r in available_rooms:
        images = [img.image_filename for img in r.images]
        if not images: images = [r.image_filename]
        rooms_data.append({'id': r.id, 'room_number': r.room_number, 'room_type': r.room_type, 'price': r.price, 'description': r.description, 'image_filename': r.image_filename, 'images': images, 'is_featured': r.is_featured, 'amenities': r.amenities})
    return jsonify(rooms_data), 200

@app.route('/api/bookings', methods=['POST'])
@api_login_required
def create_booking():
    data = request.get_json()
    room = db.session.get(Room, data['room_id'])
    if not room: return jsonify({'error': 'Room not found'}), 404
    check_in = datetime.strptime(data['check_in'], '%Y-%m-%d')
    check_out = datetime.strptime(data['check_out'], '%Y-%m-%d')
    nights = (check_out - check_in).days
    if nights <= 0: return jsonify({'error': 'Check-out must be after check-in'}), 400
    overlapping = Booking.query.filter(Booking.room_id == room.id, Booking.status == 'confirmed', Booking.check_in < check_out, Booking.check_out > check_in).first()
    if overlapping: return jsonify({'error': 'Room is already booked for these dates'}), 400
    total = nights * room.price
    booking = Booking(user_id=current_user.id, room_id=room.id, guest_name=data['guest_name'], guest_phone=data.get('guest_phone', ''), check_in=check_in, check_out=check_out, total_price=total, status='confirmed')
    db.session.add(booking)
    db.session.commit()
    print(f"\n📧 [SIMULATED EMAIL] To: {current_user.email}\nSubject: Booking Confirmed - Room {room.room_number}\nBody: Room {room.room_number} booked from {data['check_in']} to {data['check_out']}. Total: {total} ETB\n")
    return jsonify({'message': 'Booking confirmed!', 'booking_id': booking.id, 'total_price': total, 'nights': nights}), 201

@app.route('/api/my-bookings', methods=['GET', 'OPTIONS'])
@api_login_required
def get_my_bookings():
    if request.method == 'OPTIONS': return '', 200
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return jsonify([{'id': b.id, 'room_id': b.room_id, 'room_number': b.room.room_number, 'room_type': b.room.room_type, 'guest_name': b.guest_name, 'check_in': b.check_in.strftime('%Y-%m-%d'), 'check_out': b.check_out.strftime('%Y-%m-%d'), 'total_price': b.total_price, 'status': b.status} for b in bookings]), 200

@app.route('/api/bookings/<int:booking_id>/invoice', methods=['GET'])
@api_login_required
def download_invoice(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking: return jsonify({'error': 'Booking not found'}), 404
    if booking.user_id != current_user.id: return jsonify({'error': 'Unauthorized'}), 403
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("<b>YADA HOTEL - Booking Invoice</b>", styles['Title']))
    elements.append(Spacer(1, 20))
    data = [['Invoice Date:', datetime.utcnow().strftime('%Y-%m-%d')], ['Booking ID:', f"#{booking.id}"], ['Guest Name:', booking.guest_name], ['Phone:', booking.guest_phone or 'N/A'], ['Room Number:', booking.room.room_number], ['Room Type:', booking.room.room_type], ['Check-in:', booking.check_in.strftime('%Y-%m-%d')], ['Check-out:', booking.check_out.strftime('%Y-%m-%d')], ['Total Paid:', f"{booking.total_price:,.2f} ETB"], ['Status:', booking.status.upper()]]
    table = Table(data, colWidths=[150, 300])
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f0f4f8")),('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#1a3a5c")),('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),('GRID', (0, 0), (-1, -1), 1, colors.grey),('PADDING', (0, 0), (-1, -1), 10),]))
    elements.append(table)
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Thank you for choosing YADA HOTEL!", styles['Normal']))
    doc.build(elements)
    buffer.seek(0)
    return Response(buffer.getvalue(), mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename=YADA_Invoice_{booking.id}.pdf"})

@app.route('/api/bookings/<int:booking_id>/cancel', methods=['POST'])
@api_login_required
def cancel_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking: return jsonify({'error': 'Booking not found'}), 404
    if booking.user_id != current_user.id: return jsonify({'error': 'Unauthorized'}), 403
    if booking.status == 'cancelled': return jsonify({'error': 'Booking already cancelled'}), 400
    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'message': 'Booking cancelled successfully'}), 200

@app.route('/api/reviews/<int:room_id>', methods=['GET'])
def get_room_reviews(room_id):
    reviews = Review.query.filter_by(room_id=room_id).order_by(Review.created_at.desc()).all()
    return jsonify([{'id': r.id, 'author': r.author.username, 'rating': r.rating, 'comment': r.comment, 'date': r.created_at.strftime('%Y-%m-%d')} for r in reviews]), 200

@app.route('/api/reviews', methods=['POST'])
@api_login_required
def add_review():
    data = request.get_json()
    booking = Booking.query.filter_by(user_id=current_user.id, room_id=data['room_id'], status='confirmed').first()
    if not booking: return jsonify({'error': 'You can only review rooms you have booked.'}), 403
    existing_review = Review.query.filter_by(user_id=current_user.id, room_id=data['room_id']).first()
    if existing_review: return jsonify({'error': 'You have already reviewed this room.'}), 400
    review = Review(user_id=current_user.id, room_id=data['room_id'], rating=data['rating'], comment=data['comment'])
    db.session.add(review)
    db.session.commit()
    return jsonify({'message': 'Review submitted successfully'}), 201

@app.route('/api/admin/stats', methods=['GET'])
@api_login_required
def admin_stats():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    return jsonify({'total_rooms': Room.query.count(), 'available_rooms': Room.query.filter_by(available=True).count(), 'total_bookings': Booking.query.count(), 'total_revenue': db.session.query(db.func.sum(Booking.total_price)).scalar() or 0, 'total_guests': User.query.count()}), 200

@app.route('/api/admin/chart-data', methods=['GET'])
@api_login_required
def admin_chart_data():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    today = datetime.utcnow().date()
    labels = []
    data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime('%b %d')
        labels.append(day_str)
        start_of_day = datetime.combine(day, datetime.min.time())
        end_of_day = datetime.combine(day, datetime.max.time())
        daily_revenue = db.session.query(db.func.sum(Booking.total_price)).filter(
            Booking.status == 'confirmed', Booking.check_in >= start_of_day, Booking.check_in <= end_of_day
        ).scalar() or 0
        data.append(daily_revenue)
    return jsonify({'labels': labels, 'data': data}), 200

@app.route('/api/admin/calendar', methods=['GET'])
@api_login_required
def admin_calendar():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    bookings = Booking.query.filter_by(status='confirmed').all()
    events = []
    for b in bookings:
        color = '#3788d8'
        if b.room.room_type == 'Deluxe': color = '#27ae60'
        elif b.room.room_type == 'Suite': color = '#8e44ad'
        events.append({'title': f"Room {b.room.room_number} - {b.guest_name}", 'start': b.check_in.strftime('%Y-%m-%d'), 'end': b.check_out.strftime('%Y-%m-%d'), 'backgroundColor': color, 'borderColor': color})
    return jsonify(events), 200

@app.route('/api/admin/bookings', methods=['GET'])
@api_login_required
def admin_bookings():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    bookings = Booking.query.all()
    return jsonify([{'id': b.id, 'room_number': b.room.room_number, 'guest_name': b.guest_name, 'check_in': b.check_in.strftime('%Y-%m-%d'), 'check_out': b.check_out.strftime('%Y-%m-%d'), 'total_price': b.total_price, 'status': b.status} for b in bookings]), 200

@app.route('/api/admin/reviews', methods=['GET'])
@api_login_required
def admin_reviews():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return jsonify([{'id': r.id, 'room_number': r.room.room_number, 'author': r.author.username, 'rating': r.rating, 'comment': r.comment, 'date': r.created_at.strftime('%Y-%m-%d')} for r in reviews]), 200

@app.route('/api/admin/guests', methods=['GET'])
@api_login_required
def admin_guests():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'email': u.email, 'total_bookings': Booking.query.filter_by(user_id=u.id).count()} for u in users]), 200

@app.route('/api/admin/settings', methods=['GET', 'PUT'])
@api_login_required
def admin_settings():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    s = SiteSetting.query.first()
    if request.method == 'GET':
        return jsonify({'whatsapp': s.whatsapp, 'telegram': s.telegram, 'gmail': s.gmail, 'address': s.address}), 200
    if request.method == 'PUT':
        data = request.get_json()
        if 'whatsapp' in data: s.whatsapp = data['whatsapp']
        if 'telegram' in data: s.telegram = data['telegram']
        if 'gmail' in data: s.gmail = data['gmail']
        if 'address' in data: s.address = data['address']
        db.session.commit()
        return jsonify({'message': 'Settings updated successfully'}), 200

@app.route('/api/admin/rooms', methods=['POST'])
@api_login_required
def admin_add_room():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    room_number = request.form.get('room_number')
    room_type = request.form.get('room_type')
    price = request.form.get('price')
    description = request.form.get('description')
    is_featured = True if request.form.get('is_featured') == 'true' else False
    amenities = request.form.get('amenities', '')
    image_filename = 'default_room.jpg'
    images = request.files.getlist('images')
    saved_filenames = []
    for file in images:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            saved_filenames.append(filename)
    if saved_filenames: image_filename = saved_filenames[0]
    new_room = Room(room_number=room_number, room_type=room_type, price=price, description=description, available=True, image_filename=image_filename, is_featured=is_featured, amenities=amenities)
    db.session.add(new_room)
    db.session.commit()
    for filename in saved_filenames:
        new_image = RoomImage(room_id=new_room.id, image_filename=filename)
        db.session.add(new_image)
    db.session.commit()
    return jsonify({'message': 'Room added with gallery!'}), 201

@app.route('/api/admin/rooms/<int:room_id>/edit', methods=['POST'])
@api_login_required
def admin_edit_room_with_image(room_id):
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    room = db.session.get(Room, room_id)
    if not room: return jsonify({'error': 'Room not found'}), 404
    room.room_number = request.form.get('room_number', room.room_number)
    room.room_type = request.form.get('room_type', room.room_type)
    room.price = request.form.get('price', room.price)
    room.description = request.form.get('description', room.description)
    if 'is_featured' in request.form: room.is_featured = True if request.form.get('is_featured') == 'true' else False
    if 'amenities' in request.form: room.amenities = request.form.get('amenities', '')
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            room.image_filename = filename 
            new_image = RoomImage(room_id=room.id, image_filename=filename)
            db.session.add(new_image)
    db.session.commit()
    return jsonify({'message': 'Room updated with new image!'}), 200

@app.route('/api/admin/rooms/<int:room_id>', methods=['PUT', 'DELETE'])
@api_login_required
def admin_manage_room(room_id):
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    room = db.session.get(Room, room_id)
    if not room: return jsonify({'error': 'Room not found'}), 404
    if request.method == 'DELETE':
        db.session.delete(room)
        db.session.commit()
        return jsonify({'message': 'Room deleted'}), 200
    if request.method == 'PUT':
        data = request.get_json()
        if 'room_number' in data: room.room_number = data['room_number']
        if 'room_type' in data: room.room_type = data['room_type']
        if 'price' in data: room.price = data['price']
        if 'description' in data: room.description = data['description']
        if 'is_featured' in data: room.is_featured = data['is_featured']
        if 'amenities' in data: room.amenities = data['amenities']
        db.session.commit()
        return jsonify({'message': 'Room updated'}), 200

@app.route('/api/admin/export/bookings/pdf', methods=['GET'])
@api_login_required
def export_bookings_pdf():
    if current_user.username != 'admin': return jsonify({'error': 'Admin access required'}), 403
    bookings = Booking.query.all()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("YADA HOTEL - Booking Report", styles['Title']))
    elements.append(Spacer(1, 12))
    data = [['ID', 'Room', 'Guest Name', 'Check-in', 'Check-out', 'Total (ETB)', 'Status']]
    for b in bookings:
        data.append([str(b.id), b.room.room_number, b.guest_name, b.check_in.strftime('%Y-%m-%d'), b.check_out.strftime('%Y-%m-%d'), f"{b.total_price:,.2f}", b.status.upper()])
    table = Table(data, colWidths=[40, 50, 120, 80, 80, 80, 80])
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),('ALIGN', (0, 0), (-1, -1), 'CENTER'),('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),('FONTSIZE', (0, 0), (-1, 0), 12),('BOTTOMPADDING', (0, 0), (-1, 0), 12),('BACKGROUND', (0, 1), (-1, -1), colors.white),('GRID', (0, 0), (-1, -1), 1, colors.black),('FONTSIZE', (0, 1), (-1, -1), 10),]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return Response(buffer.getvalue(), mimetype="application/pdf", headers={"Content-Disposition": "attachment; filename=yada_hotel_bookings.pdf"})

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    data = request.get_json()
    new_msg = ContactMessage(name=data['name'], email=data['email'], message=data['message'])
    db.session.add(new_msg)
    db.session.commit()
    return jsonify({'message': 'Message sent successfully!'}), 201

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
