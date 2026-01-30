
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
from create_auth_db import (
    validate_user, get_user_role, save_submission, 
    get_all_submissions, get_submission_detail, 
    get_all_students, get_student_submissions,
    get_submissions_by_time_range, get_all_submissions_with_content
)
from evaluator import evaluate_uploaded_content, find_similar_submissions
import os
import re
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')

# Ensure uploads directory exists
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ============================================
# Page Routes
# ============================================

@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login.html')
def login_html():
    return render_template('login.html')


@app.route('/index.html')
def index_html():
    # Only students can access this page
    if 'username' not in session:
        return redirect('/login.html')
    if session.get('role') == 'admin':
        return redirect('/admin.html')
    return render_template('index.html')


@app.route('/admin.html')
def admin_html():
    # Only admins can access this page
    if 'username' not in session or session.get('role') != 'admin':
        return redirect('/login.html')
    return render_template('admin.html')


# ============================================
# Authentication Routes
# ============================================

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = validate_user(username, password)
    if user:
        session['username'] = user['username']
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['name'] = user.get('name', user['username'])
        return jsonify({
            'success': True, 
            'role': user['role']
        }), 200
    else:
        return jsonify({
            'success': False, 
            'message': 'Invalid username or password'
        }), 401


@app.route('/auth-check')
def auth_check():
    if 'username' in session:
        return '', 200
    return '', 401


@app.route('/admin-check')
def admin_check():
    if 'username' in session and session.get('role') == 'admin':
        return '', 200
    return '', 401


@app.route('/get-user-info')
def get_user_info():
    if 'username' in session:
        return jsonify({
            'username': session.get('name', session['username']),
            'role': session.get('role', 'student')
        })
    return jsonify({}), 401


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login.html')


# ============================================
# File Upload & Evaluation (Student)
# ============================================

def extract_score_from_evaluation(evaluation_text):
    """Extract overall score from evaluation text"""
    if not evaluation_text:
        return 0
    
    # Try to find patterns like "Overall Score: 85/100" or "Overall: 85"
    patterns = [
        r'Overall\s*Score[:\s]*(\d+)',
        r'Overall[:\s]*(\d+)',
        r'\*\*Overall\s*Score\*\*[:\s]*(\d+)',
        r'(\d+)/100',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, evaluation_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return 50  # Default score if not found


@app.route('/upload-c', methods=['POST'])
def upload_c_file():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if 'cfile' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    
    file = request.files['cfile']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
    if not file.filename.lower().endswith('.c'):
        return jsonify({'success': False, 'message': 'Only .c files allowed'}), 400
    
    # Get the problem statement from request
    problem_statement = request.form.get('problem', 'Check Array is Sorted')
    
    # Decode file content directly from memory
    file_content = file.read().decode('utf-8', errors='ignore')
    filename = secure_filename(file.filename)
    
    # Evaluate the file using Groq LLM
    evaluation_result = evaluate_uploaded_content(file_content, problem_statement)
    
    # Determine status based on evaluation
    score = 0
    status = 'rejected'
    evaluation_text = None
    
    if evaluation_result['success']:
        evaluation_text = evaluation_result['evaluation']
        score = extract_score_from_evaluation(evaluation_text)
        
        # Check for PASS/FAIL in evaluation or score threshold
        if 'PASS' in evaluation_text.upper() or score >= 60:
            status = 'accepted'
        else:
            status = 'rejected'
    
    # Save submission to database
    save_submission(
        user_id=session.get('user_id', 0),
        username=session['username'],
        problem_title=problem_statement.split('\n')[0][:100],
        filename=filename,
        file_content=file_content,
        status=status,
        evaluation=evaluation_text,
        score=score
    )
    
    # Return status and score to student
    return jsonify({
        'success': True,
        'status': status,
        'score': score,
        'message': 'Submitted successfully!' if status == 'accepted' else 'Submission rejected.'
    }), 200



# ============================================
# Admin API Routes
# ============================================

@app.route('/api/admin/reset-submissions', methods=['POST'])
def api_admin_reset_submissions():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        from create_auth_db import reset_all_submissions
        reset_all_submissions()
        return jsonify({'success': True, 'message': 'All submissions deleted.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/students')
def api_admin_students():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify([]), 401
    
    students = get_all_students()
    return jsonify(students)


@app.route('/api/admin/submissions')
def api_admin_submissions():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify([]), 401
    
    username = request.args.get('username')
    
    if username:
        submissions = get_student_submissions(username)
    else:
        submissions = get_all_submissions()
    
    return jsonify(submissions)


@app.route('/api/admin/submission/<int:submission_id>')
def api_admin_submission_detail(submission_id):
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({}), 401
    
    submission = get_submission_detail(submission_id)
    if submission:
        return jsonify(submission)
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/admin/submission/<int:submission_id>/similar')
def api_admin_similar_submissions(submission_id):
    """Find submissions with similar code to the given submission"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify([]), 401
    
    submission = get_submission_detail(submission_id)
    if not submission or not submission.get('file_content'):
        return jsonify([]), 404
    
    # Get all submissions for comparison
    all_submissions = get_all_submissions_with_content()
    
    # Find similar submissions (excluding the current one)
    similar = find_similar_submissions(
        submission['file_content'], 
        all_submissions, 
        current_submission_id=submission_id,
        threshold=70.0
    )
    
    return jsonify(similar)


# ============================================
# Static Files
# ============================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


@app.route('/<path:filename>')
def serve_static_file(filename):
    static_folder = os.path.join(os.getcwd(), 'static')
    return send_from_directory(static_folder, filename)


# ============================================
# Run Server
# ============================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)