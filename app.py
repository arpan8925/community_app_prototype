from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Activity
import os
from sqlalchemy import func
from datetime import datetime
# Add to your imports
import psycopg2

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'



# Update database configuration
if os.environ.get('VERCEL_ENV') == 'production':
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bluecup.db'

# Set instance path
app.instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db.init_app(app)

# Add these constants near the top of the file, after the imports
STATIC_EMAIL = "admin@example.com"
STATIC_PASSWORD = "admin123"  # In production, never store passwords in plaintext

REWARD_TIERS = [
    {'name': 'Bronze Badge', 'hours': 10, 'description': 'Earned at 10 hours'},
    {'name': 'Silver Badge', 'hours': 25, 'description': 'Earned at 25 hours'},
    {'name': 'Gold Badge', 'hours': 50, 'description': 'Earned at 50 hours'},
    {'name': 'Platinum Badge', 'hours': 100, 'description': 'Earned at 100 hours'}
]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Static data for prototype
STATIC_EVENTS = [
    {"id": 1, "title": "Community Cleanup", "date": "2024-04-01", "location": "Downtown"},
    {"id": 2, "title": "Voter Registration Drive", "date": "2024-04-15", "location": "City Hall"},
]

@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Add static credential check
        if email == STATIC_EMAIL and password == STATIC_PASSWORD:
            user = User.query.filter_by(email=STATIC_EMAIL).first()
            if not user:
                # Create static user if it doesn't exist
                user = User(
                    email=STATIC_EMAIL,
                    password=generate_password_hash(STATIC_PASSWORD),
                    county="Test County",
                    home_club="Test Club"
                )
                db.session.add(user)
                db.session.commit()
            login_user(user)
            return redirect(url_for('home'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        county = request.form.get('county')
        home_club = request.form.get('home_club')
        
        user = User(
            email=email,
            password=generate_password_hash(password),
            county=county,
            home_club=home_club
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/log-activity', methods=['GET', 'POST'])
@login_required
def log_activity():
    if request.method == 'POST':
        activity = Activity(
            activity_type=request.form.get('activity_type'),
            hours=float(request.form.get('hours')),
            description=request.form.get('description'),
            user_id=current_user.id
        )
        db.session.add(activity)
        db.session.commit()
        flash('Activity logged successfully!')
        return redirect(url_for('home'))
    return render_template('log_activity.html', events=STATIC_EVENTS)

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.all()
    leaderboard_data = []
    for user in users:
        total_hours = db.session.query(func.sum(Activity.hours))\
            .filter(Activity.user_id == user.id)\
            .scalar() or 0
        leaderboard_data.append({
            'email': user.email,
            'hours': float(total_hours)
        })
    leaderboard_data.sort(key=lambda x: x['hours'], reverse=True)
    return render_template('leaderboard.html', leaderboard=leaderboard_data)

@app.route('/events')
@login_required
def events():
    return render_template('events.html', events=STATIC_EVENTS)

@app.route('/rewards')
@login_required
def rewards():
    total_hours = db.session.query(func.sum(Activity.hours))\
        .filter(Activity.user_id == current_user.id)\
        .scalar() or 0
    
    earned_rewards = [
        reward for reward in REWARD_TIERS 
        if total_hours >= reward['hours']
    ]
    next_rewards = [
        reward for reward in REWARD_TIERS 
        if total_hours < reward['hours']
    ]
    
    return render_template('rewards.html', 
                         total_hours=float(total_hours),
                         earned_rewards=earned_rewards,
                         next_rewards=next_rewards)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

with app.app_context():
    db.create_all()
