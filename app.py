# app.py

from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
import csv
from werkzeug.utils import secure_filename

# ✅ App setup
app = Flask(__name__)
app.secret_key = 'khayam123'

# ✅ Upload setup
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads folder if not exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ✅ Allowed file checker
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ✅ Database connector
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn
# ✅ Movies importer from CSV
def import_movies():
    conn = get_db()
    conn.execute('PRAGMA foreign_keys = OFF')  # Optional for initial inserts
    c = conn.cursor()

    try:
        with open('movies.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                c.execute('''
                    INSERT OR IGNORE INTO movies (id, title, year, country, genre, director, minutes, poster)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    int(row['id']),
                    row['title'],
                    int(row['year']),
                    row['country'],
                    row['genre'],
                    row['director'],
                    int(row['minutes']),
                    row['poster']
                ))
        conn.commit()
        print("✅ Movies imported successfully!")
    except Exception as e:
        print(f"❌ Error importing movies: {e}")
    finally:
        conn.close()
# Initialize the Database
def init_db():
    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON')
    c = conn.cursor()

    # --- USERS TABLE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            profile_pic TEXT DEFAULT ''
        )
    ''')

    # --- MOVIES TABLE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY,
            title TEXT,
            year INTEGER,
            country TEXT,
            genre TEXT,
            director TEXT,
            minutes INTEGER,
            poster TEXT
        )
    ''')

    # --- FRIENDS TABLE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            friend_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (friend_id) REFERENCES users(id)
        )
    ''')

    # --- FRIEND REQUESTS TABLE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    ''')

    # --- INTERESTS TABLE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            genre TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # --- WATCHLIST TABLE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            movie_id INTEGER,
            UNIQUE(user_id, movie_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (movie_id) REFERENCES movies(id)
        )
    ''')

    # --- FRIEND RECOMMENDATIONS TABLE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS friend_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommender_id INTEGER,
            friend_id INTEGER,
            movie_id INTEGER,
            FOREIGN KEY (recommender_id) REFERENCES users(id),
            FOREIGN KEY (friend_id) REFERENCES users(id),
            FOREIGN KEY (movie_id) REFERENCES movies(id)
        )
    ''')

    # --- MESSAGES TABLE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()
import_movies()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO users (username, email, password) 
                VALUES (?, ?, ?)
            ''', (username, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists!"
        finally:
            conn.close()

        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                            (username, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/dashboard')
        else:
            error = "❌ Invalid Username or Password!"
            return render_template('login.html', error=error)

    return render_template('login.html')

# ✅ Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    users = conn.execute('SELECT * FROM users WHERE id != ?', (user_id,)).fetchall()
    friends = conn.execute('''
        SELECT u.* FROM users u
        JOIN friends f ON u.id = f.friend_id
        WHERE f.user_id = ?
    ''', (user_id,)).fetchall()
    conn.close()

    return render_template('dashboard.html', users=users, friends=friends)

# ✅ Add Friend Route
@app.route('/send_friend_request/<int:receiver_id>')
def send_friend_request(receiver_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    # Prevent duplicate friend requests
    existing = conn.execute('''
        SELECT * FROM friend_requests 
        WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
    ''', (user_id, receiver_id)).fetchone()

    if not existing:
        conn.execute('''
            INSERT INTO friend_requests (sender_id, receiver_id) 
            VALUES (?, ?)
        ''', (user_id, receiver_id))
        conn.commit()

    conn.close()
    return redirect('/dashboard')

# ✅ Friend Requests Route
@app.route('/friend_requests')
def friend_requests():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    requests = conn.execute('''
        SELECT fr.id, u.username, u.id AS sender_id
        FROM friend_requests fr
        JOIN users u ON fr.sender_id = u.id
        WHERE fr.receiver_id = ? AND fr.status = 'pending'
    ''', (user_id,)).fetchall()

    conn.close()
    return render_template('friend_requests.html', requests=requests)

# ✅ Accept Friend Request Route
@app.route('/accept_request/<int:request_id>/<int:sender_id>')
def accept_request(request_id, sender_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    receiver_id = session['user_id']

    # ✅ Update the friend request status to accepted
    conn.execute('''
        UPDATE friend_requests 
        SET status = 'accepted' 
        WHERE id = ?
    ''', (request_id,))

    # ✅ Insert friendship in both directions
    conn.execute('''
        INSERT INTO friends (user_id, friend_id) 
        VALUES (?, ?)
    ''', (receiver_id, sender_id))

    conn.execute('''
        INSERT INTO friends (user_id, friend_id) 
        VALUES (?, ?)
    ''', (sender_id, receiver_id))

    conn.commit()
    conn.close()
    
    return redirect('/dashboard')

# ✅ Logout Route
@app.route('/logout')
def logout():
    session.clear()  # Clear the session to logout user
    return redirect('/login')

# ✅ Home Route
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')  # If already logged in, go to dashboard
    return redirect('/login')          # Else go to login

# ✅ Interests Route
@app.route('/interests', methods=['GET', 'POST'])
def interests():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    if request.method == 'POST':
        selected_genres = request.form.getlist('genres')

        # ✅ Clear existing interests first
        conn.execute('DELETE FROM interests WHERE user_id = ?', (user_id,))

        # ✅ Insert new selected genres
        for genre in selected_genres:
            conn.execute('INSERT INTO interests (user_id, genre) VALUES (?, ?)', (user_id, genre))

        conn.commit()
        conn.close()
        return redirect('/dashboard')

    # ✅ Fetch current user interests
    genres = ['Action', 'Comedy', 'Drama', 'Horror', 'Romantic', 'Sci-Fi', 'Thriller']
    user_interests = conn.execute('SELECT genre FROM interests WHERE user_id = ?', (user_id,)).fetchall()
    user_interests = [row['genre'] for row in user_interests]

    conn.close()
    return render_template('interests.html', genres=genres, user_interests=user_interests)
# ✅ Recommend Movie to Friend Route
@app.route('/recommend/<int:friend_id>', methods=['GET', 'POST'])
def recommend(friend_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    if request.method == 'POST':
        movie_id = request.form['movie_id']
        conn.execute('''
            INSERT INTO friend_recommendations (recommender_id, friend_id, movie_id) 
            VALUES (?, ?, ?)
        ''', (user_id, friend_id, movie_id))
        conn.commit()
        conn.close()
        return redirect('/dashboard')

    # Fetch movies and friend's info
    movies = conn.execute('SELECT * FROM movies').fetchall()
    friend = conn.execute('SELECT * FROM users WHERE id = ?', (friend_id,)).fetchone()

    conn.close()
    return render_template('recommend.html', friend=friend, movies=movies)

# ✅ My Recommendations Route
@app.route('/my_recommendations')
def my_recommendations():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    # ✅ Join friend_recommendations with users and movies
    recommendations = conn.execute('''
        SELECT fr.id, u.username AS recommender, m.title, m.genre, m.poster
        FROM friend_recommendations fr
        JOIN users u ON fr.recommender_id = u.id
        JOIN movies m ON fr.movie_id = m.id
        WHERE fr.friend_id = ?
    ''', (user_id,)).fetchall()

    conn.close()
    return render_template('my_recommendations.html', recommendations=recommendations)

# ✅ Chat with Friend Route
@app.route('/chat/<int:friend_id>', methods=['GET', 'POST'])
def chat(friend_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    if request.method == 'POST':
        message = request.form['message']
        conn.execute('''
            INSERT INTO messages (sender_id, receiver_id, message)
            VALUES (?, ?, ?)
        ''', (user_id, friend_id, message))
        conn.commit()
        conn.close()
        return redirect(f'/chat/{friend_id}')

    # GET Request
    friend = conn.execute('SELECT username FROM users WHERE id = ?', (friend_id,)).fetchone()

    messages = conn.execute('''
        SELECT m.*, u.username AS sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY m.timestamp ASC
    ''', (user_id, friend_id, friend_id, user_id)).fetchall()

    conn.close()
    return render_template('chat.html', friend=friend, friend_id=friend_id, messages=messages)

# ✅ Profile Route (Correct)
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    if request.method == 'POST':
        new_email = request.form['email']

        conn.execute('''
            UPDATE users
            SET email = ?
            WHERE id = ?
        ''', (new_email, user_id))
        conn.commit()
        conn.close()
        return redirect('/dashboard')

    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

# ✅ Interest-Based Recommendations Route
@app.route('/my_interest_recommendations')
def my_interest_recommendations():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    user_interests = conn.execute('''
        SELECT genre
        FROM interests
        WHERE user_id = ?
    ''', (user_id,)).fetchall()

    genres = [row['genre'] for row in user_interests]

    if not genres:
        conn.close()
        return render_template('recommendations_by_interest.html', movies=[])

    placeholders = ','.join('?' for _ in genres)
    query = f'''
        SELECT DISTINCT title, genre, poster
        FROM movies
        WHERE genre IN ({placeholders})
        ORDER BY title ASC
    '''
    movies = conn.execute(query, genres).fetchall()

    conn.close()
    return render_template('recommendations_by_interest.html', movies=movies)

# ✅ Save to Watchlist Route
@app.route('/save_to_watchlist/<string:movie_title>', methods=['POST'])
def save_to_watchlist(movie_title):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    # ✅ Find movie by title
    movie = conn.execute('SELECT id FROM movies WHERE title = ?', (movie_title,)).fetchone()

    if movie:
        movie_id = movie['id']

        # ✅ Check if already exists in watchlist
        exists = conn.execute('''
            SELECT * FROM watchlist
            WHERE user_id = ? AND movie_id = ?
        ''', (user_id, movie_id)).fetchone()

        if not exists:
            conn.execute('''
                INSERT INTO watchlist (user_id, movie_id)
                VALUES (?, ?)
            ''', (user_id, movie_id))
            conn.commit()

    conn.close()
    return redirect(request.referrer or '/dashboard')

# ✅ Favorites Route
@app.route('/favorites')
def favorites():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    movies = conn.execute('''
        SELECT m.title, m.genre, m.poster
        FROM watchlist w
        JOIN movies m ON w.movie_id = m.id
        WHERE w.user_id = ?
    ''', (user_id,)).fetchall()

    conn.close()
    return render_template('favorites.html', movies=movies)

# ✅ Watchlist Route (alias of favorites)
@app.route('/watchlist')
def watchlist():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    movies = conn.execute('''
        SELECT m.title, m.genre, m.poster
        FROM watchlist w
        JOIN movies m ON w.movie_id = m.id
        WHERE w.user_id = ?
    ''', (user_id,)).fetchall()

    conn.close()
    return render_template('favorites.html', movies=movies)

# ✅ Combined (User + Friend Interests) Recommendations
@app.route('/combined_recommendations')
def combined_recommendations():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    # ✅ Get user interests
    user_interests = conn.execute('''
        SELECT genre
        FROM interests
        WHERE user_id = ?
    ''', (user_id,)).fetchall()
    user_genres = [row['genre'] for row in user_interests]

    # ✅ Get friend IDs
    friend_ids = conn.execute('''
        SELECT friend_id
        FROM friends
        WHERE user_id = ?
    ''', (user_id,)).fetchall()
    friend_ids = [row['friend_id'] for row in friend_ids]

    # ✅ Get friends' interests
    friend_genres = []
    if friend_ids:
        placeholders = ','.join('?' for _ in friend_ids)
        rows = conn.execute(f'''
            SELECT DISTINCT genre
            FROM interests
            WHERE user_id IN ({placeholders})
        ''', friend_ids).fetchall()
        friend_genres = [row['genre'] for row in rows]

    # ✅ Merge and deduplicate genres
    all_genres = list(set(user_genres + friend_genres))

    # ✅ Fetch movies based on combined interests
    if all_genres:
        placeholders = ','.join('?' for _ in all_genres)
        query = f'''
            SELECT DISTINCT title, genre, poster
            FROM movies
            WHERE genre IN ({placeholders})
            ORDER BY title ASC
        '''
        movies = conn.execute(query, all_genres).fetchall()
    else:
        movies = []

    conn.close()
    return render_template('combined_recommendations.html', movies=movies)

# ✅ Home Route
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('index.html')

# ✅ Upload Folder Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ Check Allowed File Extensions (for Profile Pic Uploads)
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ✅ Upload Profile Picture Route
@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if 'user_id' not in session:
        return redirect('/login')

    if 'profile_pic' not in request.files:
        return redirect('/profile')

    file = request.files['profile_pic']

    if file.filename == '':
        return redirect('/profile')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        conn = get_db()
        conn.execute('''
            UPDATE users
            SET profile_pic = ?
            WHERE id = ?
        ''', (filename, session['user_id']))
        conn.commit()
        conn.close()

    return redirect('/profile')

# Change Password Route
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    user_id = session['user_id']

    # Get form data
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    # Fetch user's current password from DB
    user = conn.execute('SELECT password FROM users WHERE id = ?', (user_id,)).fetchone()

    if not user:
        return "User not found", 404

    # 1. Check if the old password is correct
    if current_password != user['password']:
        return "❌ Current password is incorrect!"

    # 2. Check if new passwords match
    if new_password != confirm_password:
        return "❌ New passwords do not match!"

    # 3. Update password
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, user_id))
    conn.commit()

    return redirect('/profile')

if __name__ == "__main__":
    app.run(debug=True)
