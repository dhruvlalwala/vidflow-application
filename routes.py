import os
import uuid
from datetime import datetime, timedelta
from flask import (render_template, url_for, flash, redirect, request, Blueprint,
                   current_app, jsonify)
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import or_, desc
from sqlalchemy.orm import joinedload, subqueryload
from app import db
from app.models import User, Post, Like, Comment, Story, Message, Notification

main = Blueprint('main', __name__)

# --- Helper Functions ---
def is_video(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['mp4', 'mov', 'avi', 'mkv', 'webm']

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_file(file, folder_key):
    original_extension = file.filename.rsplit('.', 1)[1].lower()
    random_hex = uuid.uuid4().hex
    filename = f"{random_hex}.{original_extension}"
    file_path = os.path.join(current_app.root_path, '..', current_app.config[folder_key], filename)
    file.save(file_path)
    return filename

# --- Main Page Routes ---
@main.route("/")
@main.route("/feed")
@login_required
def feed():
    followed_ids = [user.id for user in current_user.followed]
    followed_ids.append(current_user.id)
    
    posts = Post.query.options(
        joinedload(Post.author),
        subqueryload(Post.comments),
        subqueryload(Post.likes)
    ).filter(Post.user_id.in_(followed_ids)).order_by(Post.timestamp.desc()).all()

    stories_by_user = {}
    all_active_stories = Story.query.filter(
        Story.user_id.in_(followed_ids),
        Story.timestamp > (datetime.utcnow() - timedelta(hours=24))
    ).order_by(Story.user_id, Story.timestamp.desc()).all()

    for story in all_active_stories:
        if story.user_id not in stories_by_user:
            stories_by_user[story.user_id] = {
                'author': story.author,
                'stories': []
            }
        stories_by_user[story.user_id]['stories'].append({
            'filename': story.filename,
            'id': story.id
        })

    return render_template('feed.html', title='Feed', posts=posts, stories_by_user=stories_by_user)

@main.route('/stories/<string:username>')
@login_required
def view_stories(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    stories = Story.query.filter_by(author=user).filter(
        Story.timestamp > (datetime.utcnow() - timedelta(hours=24))
    ).order_by(Story.timestamp.asc()).all()

    if not stories:
        flash('This user has no active stories.', 'info')
        return redirect(url_for('main.feed'))

    serialized_stories = [
        {
            'id': story.id,
            'filename': story.filename,
            'user_id': story.user_id,
            'author_username': story.author.username,
            'author_pic': url_for('static', filename='profile_pics/' + story.author.profile_pic)
        }
        for story in stories
    ]

    start_story_id = request.args.get('story_id', type=int)
    start_index = 0
    if start_story_id:
        for i, story in enumerate(serialized_stories):
            if story['id'] == start_story_id:
                start_index = i
                break

    return render_template('story_detail.html', stories=serialized_stories, start_index=start_index, author=user)

@main.route('/profile/<string:username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.timestamp.desc()).all()
    return render_template('profile.html', user=user, posts=posts)

@main.route('/post/<int:post_id>')
@login_required
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)

# --- Authentication Routes ---
@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.feed'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('main.register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('main.register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('main.register'))
        
        user = User(username=username, email=email, role='consumer')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.feed'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.feed'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
    return render_template('login.html', title='Login')

@main.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))

# --- Content Creation/Deletion/Edit Routes ---
@main.route('/upload_post', methods=['GET', 'POST'])
@login_required
def upload_post():
    if current_user.role != 'creator':
        flash('Only creator accounts can upload content.', 'danger')
        return redirect(url_for('main.feed'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part.', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file.', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = save_file(file, 'UPLOAD_FOLDER')
            media_type = 'video' if is_video(filename) else 'image'
            title = request.form.get('title', '')
            publisher = request.form.get('publisher', '')
            producer = request.form.get('producer', '')
            genre = request.form.get('genre', '')
            age_rating = request.form.get('age_rating', '')
            caption = request.form.get('caption', '')

            post = Post(caption=caption, filename=filename, author=current_user,
                        media_type=media_type, title=title, publisher=publisher, 
                        producer=producer, genre=genre, age_rating=age_rating)
            
            db.session.add(post)
            db.session.commit()
            flash('Your post has been created!', 'success')
            return redirect(url_for('main.feed'))
        else:
            flash('File type not allowed.', 'danger')
    return render_template('upload_post.html', title='New Post')

@main.route('/upload_story', methods=['GET', 'POST'])
@login_required
def upload_story():
    if current_user.role != 'creator':
        flash('Only creator accounts can upload stories.', 'danger')
        return redirect(url_for('main.feed'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part.', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file.', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = save_file(file, 'STORY_PICS_FOLDER')
            story = Story(filename=filename, author=current_user)
            db.session.add(story)
            db.session.commit()
            flash('Your story has been uploaded!', 'success')
            return redirect(url_for('main.feed'))
        else:
            flash('Invalid file type.', 'danger')
    return render_template('upload_story.html', title='New Story')

@main.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You do not have permission to delete this post.', 'danger')
        return redirect(request.referrer or url_for('main.feed'))
    try:
        os.remove(os.path.join(current_app.root_path, '..', current_app.config['UPLOAD_FOLDER'], post.filename))
    except OSError as e:
        print(f"Error deleting file {post.filename}: {e}")
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully.', 'success')
    return redirect(url_for('main.profile', username=current_user.username))

@main.route('/delete_story/<int:story_id>', methods=['POST'])
@login_required
def delete_story(story_id):
    story = Story.query.get_or_404(story_id)
    if story.author != current_user:
        flash('You do not have permission to delete this story.', 'danger')
        return redirect(url_for('main.feed'))
    try:
        os.remove(os.path.join(current_app.root_path, '..', current_app.config['STORY_PICS_FOLDER'], story.filename))
    except OSError as e:
        print(f"Error deleting story file {story.filename}: {e}")
    db.session.delete(story)
    db.session.commit()
    return redirect(request.referrer or url_for('main.feed'))

@main.route('/edit_post/<int:post_id>', methods=['POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        return jsonify({'status': 'error', 'message': 'Permission denied.'}), 403
    
    new_caption = request.form.get('caption', '').strip()
    if not new_caption:
        return jsonify({'status': 'error', 'message': 'Caption cannot be empty.'}), 400
    
    post.caption = new_caption
    db.session.commit()
    
    return jsonify({'status': 'success', 'new_caption': new_caption}), 200

# --- Interactive Feature Routes (Likes, Comments) ---
@main.route('/like_post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(author=current_user, post_id=post.id).first()
    if like:
        db.session.delete(like)
        db.session.commit()
        return jsonify({'status': 'unliked', 'likes_count': len(post.likes)})
    else:
        like = Like(author=current_user, post_id=post.id)
        db.session.add(like)
        if post.author != current_user:
            notification = Notification(name='like', user_id=post.author.id, actor_id=current_user.id, post_id=post.id)
            db.session.add(notification)
        db.session.commit()
        return jsonify({'status': 'liked', 'likes_count': len(post.likes)})

@main.route('/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    comment_text = request.form.get('comment_text', '').strip()
    if comment_text:
        comment = Comment(text=comment_text, author=current_user, post_id=post.id)
        db.session.add(comment)
        if post.author != current_user:
            notification = Notification(name='comment', user_id=post.author.id, actor_id=current_user.id, post_id=post.id)
            db.session.add(notification)
        db.session.commit()
        return jsonify({'status': 'success', 'comment': {'text': comment.text, 'username': current_user.username, 'profile_pic': url_for('static', filename='profile_pics/' + current_user.profile_pic)}})
    return jsonify({'status': 'error', 'message': 'Comment cannot be empty.'}), 400

# --- Profile Update & Follow Routes ---
@main.route('/update_profile_pic', methods=['POST'])
@login_required
def update_profile_pic():
    if 'profile_pic' in request.files:
        file = request.files['profile_pic']
        if file.filename != '' and allowed_file(file.filename):
            if current_user.profile_pic != 'default.jpg':
                try:
                    os.remove(os.path.join(current_app.root_path, '..', current_app.config['PROFILE_PICS_FOLDER'], current_user.profile_pic))
                except OSError:
                    pass
            filename = save_file(file, 'PROFILE_PICS_FOLDER')
            current_user.profile_pic = filename
            db.session.commit()
            flash('Profile picture updated!', 'success')
        else:
            flash('Invalid file type.', 'danger')
    else:
        flash('No file selected.', 'danger')
    return redirect(url_for('main.profile', username=current_user.username))

@main.route('/update_bio', methods=['POST'])
@login_required
def update_bio():
    bio = request.form.get('bio', '').strip()
    current_user.bio = bio
    db.session.commit()
    flash('Bio updated successfully.', 'success')
    return redirect(url_for('main.profile', username=current_user.username))

@main.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('You cannot follow yourself.', 'danger')
        return redirect(url_for('main.profile', username=username))
    current_user.follow(user)
    notification = Notification(name='follow', user_id=user.id, actor_id=current_user.id)
    db.session.add(notification)
    db.session.commit()
    flash(f'You are now following {username}.', 'success')
    return redirect(url_for('main.profile', username=username))

@main.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('You cannot unfollow yourself.', 'danger')
        return redirect(url_for('main.profile', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(f'You have unfollowed {username}.', 'info')
    return redirect(url_for('main.profile', username=username))

# --- Direct Messaging Routes ---
@main.route('/direct_inbox')
@login_required
def direct_inbox():
    sent_to = db.session.query(Message.receiver_id).filter(Message.sender_id == current_user.id)
    received_from = db.session.query(Message.sender_id).filter(Message.receiver_id == current_user.id)
    user_ids = {item[0] for item in sent_to.union(received_from).all()}
    conversations = []
    for user_id in user_ids:
        other_user = User.query.get(user_id)
        last_message = Message.query.filter(or_((Message.sender_id == current_user.id) & (Message.receiver_id == user_id), (Message.sender_id == user_id) & (Message.receiver_id == current_user.id))).order_by(desc(Message.timestamp)).first()
        conversations.append({'user': other_user, 'last_message': last_message})
    conversations.sort(key=lambda x: x['last_message'].timestamp, reverse=True)
    return render_template('direct_inbox.html', conversations=conversations, title="Inbox")

@main.route('/messages/<string:username>', methods=['GET', 'POST'])
@login_required
def messages(username):
    receiver = User.query.filter_by(username=username).first_or_404()
    if request.method == 'POST':
        text = request.form.get('message_text')
        if text:
            message = Message(text=text, sender=current_user, receiver=receiver)
            db.session.add(message)
            notification = Notification(name='message', user_id=receiver.id, actor_id=current_user.id)
            db.session.add(notification)
            db.session.commit()
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Message cannot be empty.'}), 400
    
    messages = Message.query.filter(or_((Message.sender == current_user) & (Message.receiver == receiver), (Message.sender == receiver) & (Message.receiver == current_user))).order_by(Message.timestamp.asc()).all()
    return render_template('messages.html', receiver=receiver, messages=messages, title=f"Chat with {receiver.username}")

# --- API Routes for Follower/Following Lists ---
@main.route('/api/<username>/followers')
@login_required
def get_followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    followers = user.followers.all()
    followers_data = [{'username': f.username, 'profile_pic': url_for('static', filename='profile_pics/' + f.profile_pic)} for f in followers]
    return jsonify(followers_data)

@main.route('/api/<username>/following')
@login_required
def get_following(username):
    user = User.query.filter_by(username=username).first_or_404()
    following = user.followed.all()
    following_data = [{'username': f.username, 'profile_pic': url_for('static', filename='profile_pics/' + f.profile_pic)} for f in following]
    return jsonify(following_data)

# --- Search Functionality ---
@main.route('/search')
@login_required
def search():
    return render_template('search.html', title='Search')

@main.route('/api/search_users')
@login_required
def search_users():
    query = request.args.get('query', '', type=str)
    if not query:
        return jsonify([])
    
    users = User.query.filter(User.username.ilike(f'%{query}%'), User.id != current_user.id).limit(10).all()
    users_data = [{'username': user.username, 'profile_pic': url_for('static', filename='profile_pics/' + user.profile_pic)} for user in users]
    return jsonify(users_data)

# --- Notification Routes ---
@main.route('/notifications')
@login_required
def notifications():
    notifications = current_user.notifications.order_by(Notification.timestamp.desc()).all()
    return render_template('notifications.html', title='Notifications', notifications=notifications)

@main.route('/api/notifications/mark_read', methods=['POST'])
@login_required
def mark_notifications_read():
    current_user.notifications.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'status': 'success'})
