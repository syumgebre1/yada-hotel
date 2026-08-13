from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Room, Booking
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
from functools import wraps

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'yada-hotel-secret-key-2026'

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yada_hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session configuration
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db.init_app(app)

# CORS configuration
CORS(app, 
     supports_credentials=True,
     origins=['*'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Cookie'])

# Add CORS headers after every request
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Cookie'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None
login_manager.login_message = None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ===== CUSTOM AUTH DECORATOR FOR API =====
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow OPTIONS requests (CORS preflight) without authentication
        if request.method == 'OPTIONS':
            return '', 200
        
        if not current_user.is_authenticated:
            return jsonify({'error': 'Please login first'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ===== CREATE TABLES AND SAMPLE DATA =====
def create_rooms():
    rooms_data = [
        # Existing rooms
        {'number': '101', 'type': 'Standard', 'price': 2000, 'desc': 'Cozy room with city view'},
        {'number': '102', 'type': 'Standard', 'price': 2000, 'desc': 'Comfortable room with garden view'},
        {'number': '103', 'type': 'Deluxe', 'price': 3500, 'desc': 'Spacious room with balcony'},
        {'number': '104', 'type': 'Deluxe', 'price': 3500, 'desc': 'Elegant room with mountain view'},
        {'number': '105', 'type': 'Suite', 'price': 5000, 'desc': 'Luxury suite with living room'},
        {'number': '106', 'type': 'Standard', 'price': 2200, 'desc': 'Modern room with workspace'},
        {'number': '107', 'type': 'Deluxe', 'price': 3800, 'desc': 'Premium room with ocean view'},
        {'number': '108', 'type': 'Suite', 'price': 5500, 'desc': 'Executive suite with jacuzzi'},
        # NEW ROOMS - 5 more
        {'number': '109', 'type': 'Standard', 'price': 2500, 'desc': 'Family room with extra bed'},
        {'number': '110', 'type': 'Standard', 'price': 2500, 'desc': 'Twin beds with city view'},
        {'number': '111', 'type': 'Deluxe', 'price': 4000, 'desc': 'Corner room with panoramic view'},
        {'number': '112', 'type': 'Deluxe', 'price': 4200, 'desc': 'Family deluxe with kitchenette'},
        {'number': '113', 'type': 'Suite', 'price': 6000, 'desc': 'Presidential suite with private balcony'}
    ]
    
    for room_data in rooms_data:
        room = Room.query.filter_by(room_number=room_data['number']).first()
        if not room:
            new_room = Room(
                room_number=room_data['number'],
                room_type=room_data['type'],
                price=room_data['price'],
                description=room_data['desc'],
                available=True
            )
            db.session.add(new_room)
    db.session.commit()

def init_db():
    with app.app_context():
        db.create_all()
        create_rooms()
        print("✅ Database initialized with 13 rooms!")

# ===== TEST ROUTE =====
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'message': 'API is working!'}), 200

# ===== AUTH ROUTES =====
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    hashed_password = generate_password_hash(data['password'])
    user = User(
        username=data['username'],
        email=data['email'],
        password=hashed_password
    )
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'Registration successful!'}), 201

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user or not check_password_hash(user.password, data.get('password')):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    login_user(user, remember=True)
    session['user_id'] = user.id
    session.permanent = True
    
    return jsonify({
        'message': 'Login successful!',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    }), 200

@app.route('/api/logout', methods=['POST'])
@api_login_required
def logout():
    logout_user()
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/current-user', methods=['GET'])
@api_login_required
def current_user_info():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email
    }), 200

# ===== ROOM ROUTES =====
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms = Room.query.all()
    rooms_list = []
    for room in rooms:
        rooms_list.append({
            'id': room.id,
            'room_number': room.room_number,
            'room_type': room.room_type,
            'price': room.price,
            'description': room.description,
            'available': room.available
        })
    return jsonify(rooms_list), 200

@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    return jsonify({
        'id': room.id,
        'room_number': room.room_number,
        'room_type': room.room_type,
        'price': room.price,
        'description': room.description,
        'available': room.available
    }), 200

# ===== BOOKING ROUTES =====
@app.route('/api/bookings', methods=['POST'])
@api_login_required
def create_booking():
    data = request.get_json()
    
    room = Room.query.get(data['room_id'])
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    if not room.available:
        return jsonify({'error': 'Room is not available'}), 400
    
    check_in = datetime.strptime(data['check_in'], '%Y-%m-%d')
    check_out = datetime.strptime(data['check_out'], '%Y-%m-%d')
    nights = (check_out - check_in).days
    
    if nights <= 0:
        return jsonify({'error': 'Check-out must be after check-in'}), 400
    
    total = nights * room.price
    
    booking = Booking(
        user_id=current_user.id,
        room_id=room.id,
        guest_name=data['guest_name'],
        guest_phone=data.get('guest_phone', ''),
        check_in=check_in,
        check_out=check_out,
        total_price=total,
        status='confirmed'
    )
    
    room.available = False
    db.session.add(booking)
    db.session.commit()
    
    return jsonify({
        'message': 'Booking confirmed!',
        'booking_id': booking.id,
        'total_price': total,
        'nights': nights
    }), 201

@app.route('/api/my-bookings', methods=['GET', 'OPTIONS'])
@api_login_required
def get_my_bookings():
    # OPTIONS request is already handled in the decorator
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        user_id = current_user.id
        print(f"📡 Fetching bookings for user: {user_id}")
        
        bookings = Booking.query.filter_by(user_id=user_id).all()
        bookings_list = []
        
        for booking in bookings:
            bookings_list.append({
                'id': booking.id,
                'room_number': booking.room.room_number,
                'room_type': booking.room.room_type,
                'guest_name': booking.guest_name,
                'check_in': booking.check_in.strftime('%Y-%m-%d'),
                'check_out': booking.check_out.strftime('%Y-%m-%d'),
                'total_price': booking.total_price,
                'status': booking.status
            })
        
        print(f"📋 Found {len(bookings_list)} bookings")
        return jsonify(bookings_list), 200
    except Exception as e:
        print(f"❌ Error in my-bookings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookings/<int:booking_id>/cancel', methods=['POST'])
@api_login_required
def cancel_booking(booking_id):
    booking = Booking.query.get(booking_id)
    
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    
    if booking.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if booking.status == 'cancelled':
        return jsonify({'error': 'Booking already cancelled'}), 400
    
    room = Room.query.get(booking.room_id)
    if room:
        room.available = True
    
    booking.status = 'cancelled'
    db.session.commit()
    
    return jsonify({'message': 'Booking cancelled successfully'}), 200

# ===== CHECK AVAILABILITY =====
@app.route('/api/check-availability', methods=['POST'])
def check_availability():
    data = request.get_json()
    check_in = datetime.strptime(data['check_in'], '%Y-%m-%d')
    check_out = datetime.strptime(data['check_out'], '%Y-%m-%d')
    
    available_rooms = Room.query.filter_by(available=True).all()
    
    rooms_list = []
    for room in available_rooms:
        rooms_list.append({
            'id': room.id,
            'room_number': room.room_number,
            'room_type': room.room_type,
            'price': room.price,
            'description': room.description
        })
    
    return jsonify(rooms_list), 200

# ===== START THE APP =====
if __name__ == '__main__':
    init_db()
    # ⭐⭐⭐ IMPORTANT: host='0.0.0.0' allows connections from any IP ⭐⭐⭐
    app.run(host='0.0.0.0', port=5000, debug=True)
