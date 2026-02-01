
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
    ai_score = 0
    
    if evaluation_result['success']:
        evaluation_text = evaluation_result['evaluation']
        score = extract_score_from_evaluation(evaluation_text)
        ai_score = evaluation_result.get('ai_score', 0)  # Get AI detection score
        
        # Check for PASS/FAIL in evaluation or score threshold
        if 'PASS' in evaluation_text.upper() or score >= 60:
            status = 'accepted'
        else:
            status = 'rejected'
    
    # Save submission to database with AI score
    save_submission(
        user_id=session.get('user_id', 0),
        username=session['username'],
        problem_title=problem_statement.split('\n')[0][:100],
        filename=filename,
        file_content=file_content,
        status=status,
        evaluation=evaluation_text,
        score=score,
        ai_score=ai_score  # Now properly saving the AI detection score
    )
    
    # Return status and score to student
    return jsonify({
        'success': True,
        'status': status,
        'score': score,
        'message': 'Submitted successfully!' if status == 'accepted' else 'Submission rejected.'
    }), 200


# ============================================
# Student API Routes
# ============================================

@app.route('/api/student/my-submissions')
def api_student_submissions():
    """Get all submissions for the currently logged-in student"""
    if 'username' not in session:
        return jsonify([]), 401
    
    # Get the logged-in student's username (register number)
    username = session['username']
    submissions = get_student_submissions(username)
    
    return jsonify(submissions)


@app.route('/api/student/submission/<int:submission_id>')
def api_student_submission_detail(submission_id):
    """Get details of a specific submission (only if it belongs to the current student)"""
    if 'username' not in session:
        return jsonify({}), 401
    
    submission = get_submission_detail(submission_id)
    
    # Verify this submission belongs to the current user
    if submission and submission.get('register_no') == session['username']:
        return jsonify(submission)
    
    return jsonify({'error': 'Not found or unauthorized'}), 404


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


@app.route('/api/admin/send-reports/preview', methods=['POST'])
def api_admin_send_reports_preview():
    """Preview which students will receive reports based on time range"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    time_range = data.get('timeRange', 'all')  # 1h, 6h, 24h, 7d, 30d, all
    
    # Get submissions based on time range
    submissions = get_submissions_by_time_range(time_range)
    
    # Group by student
    students_data = {}
    for sub in submissions:
        reg_no = sub.get('register_no') or sub.get('username')
        if reg_no not in students_data:
            students_data[reg_no] = {
                'name': sub.get('name', sub.get('username', reg_no)),
                'email': sub.get('email', ''),
                'register_no': reg_no,
                'submissions': []
            }
        students_data[reg_no]['submissions'].append(sub)
    
    # Build preview list
    preview = []
    for reg_no, data in students_data.items():
        preview.append({
            'register_no': reg_no,
            'name': data['name'],
            'email': data['email'] or 'No email',
            'has_email': bool(data['email']),
            'submission_count': len(data['submissions']),
            'accepted': sum(1 for s in data['submissions'] if s['status'] == 'accepted'),
            'avg_score': sum(s.get('score', 0) for s in data['submissions']) / len(data['submissions']) if data['submissions'] else 0
        })
    
    # Sort by name
    preview.sort(key=lambda x: x['name'])
    
    return jsonify({
        'total_students': len(preview),
        'with_email': sum(1 for p in preview if p['has_email']),
        'without_email': sum(1 for p in preview if not p['has_email']),
        'total_submissions': len(submissions),
        'students': preview
    })


@app.route('/api/admin/send-reports', methods=['POST'])
def api_admin_send_reports():
    """Send reports to students based on time range"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    from email_utils import send_bulk_reports, is_email_configured
    
    if not is_email_configured():
        return jsonify({
            'success': False,
            'message': 'Email not configured. Set SMTP_USER and SMTP_PASSWORD in environment variables.'
        }), 400
    
    data = request.get_json()
    time_range = data.get('timeRange', 'all')
    
    # Get submissions based on time range
    submissions = get_submissions_by_time_range(time_range)
    
    if not submissions:
        return jsonify({
            'success': False,
            'message': 'No submissions found for the selected time range.'
        }), 400
    
    # Get all submissions for similarity checking
    all_submissions = get_all_submissions_with_content()
    
    # Add similarity info to each submission
    for sub in submissions:
        if sub.get('file_content'):
            similar = find_similar_submissions(
                sub['file_content'],
                all_submissions,
                current_submission_id=sub.get('id'),
                threshold=70.0
            )
            sub['similar_students'] = similar
        else:
            sub['similar_students'] = []
    
    # Group by student for bulk sending
    students_data = {}
    for sub in submissions:
        reg_no = sub.get('register_no') or sub.get('username')
        if reg_no not in students_data:
            students_data[reg_no] = {
                'name': sub.get('name', sub.get('username', reg_no)),
                'email': sub.get('email', ''),
                'submissions': []
            }
        students_data[reg_no]['submissions'].append(sub)
    
    # Send bulk reports
    results = send_bulk_reports(students_data)
    
    return jsonify({
        'success': True,
        'sent': results['sent'],
        'failed': results['failed'],
        'skipped': results['skipped'],
        'details': results['details']
    })


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