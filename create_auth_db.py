
import sqlite3
import hashlib
import os
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Check for DATABASE_URL for Postgres connection
DATABASE_URL = os.environ.get('DATABASE_URL')
IS_POSTGRES = bool(DATABASE_URL)

if IS_POSTGRES:
    import psycopg2

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def get_db_connection():
    """Get database connection (SQLite or Postgres)"""
    if IS_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect('auth.db')

def get_placeholder():
    """Return the correct query placeholder"""
    return '%s' if IS_POSTGRES else '?'


def create_database():
    """Create database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Different syntax for AUTOINCREMENT/SERIAL and TIMESTAMP
    if IS_POSTGRES:
        id_type = "SERIAL PRIMARY KEY"
        timestamp_default = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    else:
        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        timestamp_default = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"

    # Create the users table with role field
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {id_type},
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            created_at {timestamp_default},
            name TEXT
        )
    ''')

    # Create submissions table
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS submissions (
            id {id_type},
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            problem_title TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_content TEXT,
            status TEXT DEFAULT 'pending',
            evaluation TEXT,
            score INTEGER DEFAULT 0,
            submitted_at {timestamp_default},
            evaluated_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Insert sample admin user - handled carefully to avoid duplicates
    ph = get_placeholder()
    
    # Check if admin exists first to avoid unique constraint violation in a cleaner way for both DBs
    cursor.execute(f"SELECT id FROM users WHERE username = {ph}", ('admin',))
    if not cursor.fetchone():
        cursor.execute(f'INSERT INTO users (username, password, role, name) VALUES ({ph}, {ph}, {ph}, {ph})', 
                       ('admin', hash_password('admin123'), 'admin', 'Administrator'))

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    print("Database check/creation completed.")


def validate_user(username, password):
    """Validate user credentials and return user info including role"""
    conn = get_db_connection()
    cursor = conn.cursor()

    ph = get_placeholder()
    hashed_pw = hash_password(password)
    cursor.execute(f'SELECT id, username, role, name FROM users WHERE username = {ph} AND password = {ph}', 
                   (username, hashed_pw))
    user = cursor.fetchone()
    conn.close()

    if user:
        return {'id': user[0], 'username': user[1], 'role': user[2], 'name': user[3] if user[3] else user[1]}
    return None


def get_user_role(username):
    """Get the role of a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    cursor.execute(f'SELECT role FROM users WHERE username = {ph}', (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'student'


def save_submission(user_id, username, problem_title, filename, file_content, status, evaluation, score):
    """Save a student submission to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    cursor.execute(f'''
        INSERT INTO submissions (user_id, username, problem_title, filename, file_content, status, evaluation, score, evaluated_at)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}) RETURNING id
    ''' if IS_POSTGRES else f'''
        INSERT INTO submissions (user_id, username, problem_title, filename, file_content, status, evaluation, score, evaluated_at)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    ''', (user_id, username, problem_title, filename, file_content, status, evaluation, score, datetime.now()))
    
    if IS_POSTGRES:
        submission_id = cursor.fetchone()[0]
    else:
        submission_id = cursor.lastrowid
        
    conn.commit()
    conn.close()
    return submission_id


def get_all_submissions():
    """Get all submissions for admin view"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Join on username instead of user_id because user_id might change if users are re-imported
    cursor.execute('''
        SELECT s.id, u.username, s.problem_title, s.filename, s.status, s.score, s.submitted_at, u.name 
        FROM submissions s
        JOIN users u ON s.username = u.username
        ORDER BY s.submitted_at DESC
    ''')
    submissions = cursor.fetchall()
    conn.close()
    
    return [{
        'id': s[0],
        'username': s[7] if s[7] else s[1], # Use name if available
        'register_no': s[1],
        'problem_title': s[2],
        'filename': s[3],
        'status': s[4],
        'score': s[5],
        'submitted_at': s[6]
    } for s in submissions]


def get_submission_detail(submission_id):
    """Get full details of a single submission"""
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    # Note: Fetching columns by name or index. 
    # To be safe across DBs, let's explicitly list columns or handle index carefully
    # Postgres returns raw tuples similar to sqlite
    cursor.execute(f'''
        SELECT s.id, s.user_id, s.username, s.problem_title, s.filename, s.file_content, s.status, s.evaluation, s.score, s.submitted_at, s.evaluated_at, u.name 
        FROM submissions s 
        JOIN users u ON s.username = u.username 
        WHERE s.id = {ph}
    ''', (submission_id,))
    s = cursor.fetchone()
    conn.close()
    
    if s:
        # Columns mapped to indices:
        # 0:id, 1:user_id, 2:username, 3:problem_title, 4:filename, 5:file_content, 
        # 6:status, 7:evaluation, 8:score, 9:submitted_at, 10:evaluated_at, 11:name
        return {
            'id': s[0],
            'user_id': s[1],
            'username': s[11] if s[11] else s[2], # Name from users table
            'register_no': s[2], # Username from submissions table
            'problem_title': s[3],
            'filename': s[4],
            'file_content': s[5],
            'status': s[6],
            'evaluation': s[7],
            'score': s[8],
            'submitted_at': s[9],
            'evaluated_at': s[10]
        }
    return None


def get_all_students():
    """Get all students for admin view"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, created_at, name FROM users WHERE role = 'student' ORDER BY username")
    students = cursor.fetchall()
    conn.close()
    
    return [{'id': s[0], 'username': s[3] if s[3] else s[1], 'register_no': s[1], 'created_at': s[2]} for s in students]


def get_student_submissions(username):
    """Get all submissions for a specific student"""
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    cursor.execute(f'''
        SELECT s.id, s.problem_title, s.filename, s.status, s.score, s.submitted_at, u.name, u.username
        FROM submissions s
        JOIN users u ON s.username = u.username
        WHERE s.username = {ph}
        ORDER BY s.submitted_at DESC
    ''', (username,))
    submissions = cursor.fetchall()
    conn.close()
    
    return [{
        'id': s[0],
        'username': s[6] if s[6] else s[7], # name
        'register_no': s[7], # username (reg no)
        'problem_title': s[1],
        'filename': s[2],
        'status': s[3],
        'score': s[4],
        'submitted_at': s[5]
    } for s in submissions]

# ADMIN: Reset all submissions
def reset_all_submissions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM submissions')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()
