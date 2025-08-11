from datetime import datetime
from app import db, login_manager, bcrypt
from flask_login import UserMixin

# This function is used by Flask-Login to retrieve a user from the database by their ID.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# This is a 'helper table' or 'association table' for the many-to-many relationship
# between users (for following). It doesn't need its own model class.
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(db.Model, UserMixin):
    """User model for storing user accounts and their relationships."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    bio = db.Column(db.String(300), nullable=True, default='')
    profile_pic = db.Column(db.String(100), nullable=False, default='default.jpg')
    
    # --- NEW: Added role to distinguish between user types ---
    # 'consumer' is the default role for all new users.
    # 'creator' will be assigned manually to users who can upload.
    role = db.Column(db.String(20), nullable=False, default='consumer')
    
    posts = db.relationship('Post', backref='author', lazy=True, cascade="all, delete-orphan")
    stories = db.relationship('Story', backref='author', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='author', lazy=True, cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='author', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def set_password(self, password):
        """Hashes the password before storing it."""
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks a given password against the stored hash."""
        return bcrypt.check_password_hash(self.password, password)

    def is_following(self, user):
        """Checks if the current user is following the given user."""
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def follow(self, user):
        """Follows a user if not already following."""
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        """Unfollows a user if currently following."""
        if self.is_following(user):
            self.followed.remove(user)
            
    def unread_notifications_count(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Post(db.Model):
    """Post model for storing user-created posts."""
    id = db.Column(db.Integer, primary_key=True)
    caption = db.Column(db.String(1000), nullable=True)
    filename = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # --- NEW: Added media_type to distinguish between images and videos ---
    media_type = db.Column(db.String(10), nullable=False, default='image')
    
    # --- NEW: Added fields for video metadata as per coursework ---
    title = db.Column(db.String(100), nullable=True)
    publisher = db.Column(db.String(100), nullable=True)
    producer = db.Column(db.String(100), nullable=True)
    genre = db.Column(db.String(50), nullable=True)
    age_rating = db.Column(db.String(10), nullable=True) # e.g., 'PG', '18'
    
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='post', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"Post('{self.caption}', '{self.timestamp}')"

class Comment(db.Model):
    """Comment model for storing comments on posts."""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Like(db.Model):
    """Like model for tracking likes on posts."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Story(db.Model):
    """Story model for temporary, 24-hour posts."""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def is_active(self):
        """Checks if the story is still within its 24-hour active window."""
        return (datetime.utcnow() - self.timestamp).total_seconds() < 86400

class Message(db.Model):
    """Message model for private messages between users."""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

class Notification(db.Model):
    """Notification model for tracking user activity."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    
    actor = db.relationship('User', foreign_keys=[actor_id])
