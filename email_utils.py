"""
Email utility module for sending submission reports to students
"""

import smtplib
import os
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Email configuration from environment variables
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SENDER_EMAIL = SMTP_USER
SENDER_NAME = 'Data Structure Evaluator'


def is_email_configured():
    """Check if email settings are properly configured"""
    return bool(SMTP_USER and SMTP_PASSWORD)


def format_evaluation_html(text):
    """Convert evaluation text to formatted HTML (same as admin panel)"""
    if not text:
        return '<p style="color: #6b7280;">No evaluation available</p>'
    
    # Escape HTML
    text = html.escape(text)
    
    # Convert **bold** to <strong>
    import re
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #4f46e5;">\1</strong>', text)
    
    # Convert headers
    text = re.sub(r'^## (.*)$', r'<h4 style="color: #1e293b; margin: 16px 0 8px 0; font-size: 16px;">\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.*)$', r'<h5 style="color: #475569; margin: 12px 0 6px 0; font-size: 14px;">\1</h5>', text, flags=re.MULTILINE)
    
    # Convert bullet points
    text = re.sub(r'^- (.*)$', r'<div style="padding-left: 16px; margin: 4px 0;">• \1</div>', text, flags=re.MULTILINE)
    
    # Highlight scores
    text = re.sub(r'(\d+)/100', r'<span style="color: #10b981; font-weight: 600;">\1/100</span>', text)
    
    # Highlight PASS/FAIL
    text = text.replace('PASS', '<span style="background: #d1fae5; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: 600;">✓ PASS</span>')
    text = text.replace('FAIL', '<span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-weight: 600;">✗ FAIL</span>')
    
    # Convert newlines to paragraphs
    paragraphs = text.split('\n')
    text = ''.join(f'<p style="margin: 4px 0; line-height: 1.6;">{p}</p>' if p.strip() and not p.strip().startswith('<') else p for p in paragraphs)
    
    return text


def generate_submission_report_html(student_name, submission):
    """Generate HTML report for a single submission (matches admin panel View Report)"""
    
    if not submission:
        return None
    
    status = submission.get('status', 'pending')
    score = submission.get('score', 0)
    ai_score = submission.get('ai_score', 0)
    problem_title = submission.get('problem_title', 'N/A')
    filename = submission.get('filename', 'N/A')
    file_content = submission.get('file_content', 'No code available')
    evaluation = submission.get('evaluation', 'No evaluation available')
    submitted_at = submission.get('submitted_at', 'N/A')
    similar_students = submission.get('similar_students', [])
    
    # Status styling
    status_bg = "#d1fae5" if status == 'accepted' else "#fee2e2"
    status_color = "#166534" if status == 'accepted' else "#991b1b"
    status_text = "✓ Accepted" if status == 'accepted' else "✗ Rejected"
    
    # AI score styling
    ai_color = "#dc2626" if ai_score >= 70 else "#f59e0b" if ai_score >= 40 else "#22c55e"
    ai_label = "Likely AI" if ai_score >= 70 else "Uncertain" if ai_score >= 40 else "Likely Human"
    
    # Escape code content
    code_escaped = html.escape(file_content)
    
    # Format evaluation
    evaluation_html = format_evaluation_html(evaluation)
    
    # Build plagiarism warning section (only if there are matches)
    plagiarism_html = ""
    if similar_students:
        similar_list = ""
        for s in similar_students:
            similar_list += f"""
            <div style="padding: 8px 12px; background: white; border-radius: 4px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #92400e;">{html.escape(s.get('name', 'Unknown'))}</strong>
                    <span style="color: #78716c; font-size: 12px; margin-left: 8px;">{html.escape(s.get('username', ''))}</span>
                </div>
                <div style="font-weight: 600; color: {'#dc2626' if s.get('similarity', 0) >= 90 else '#f59e0b'};">
                    {s.get('similarity', 0)}% match
                </div>
            </div>
            """
        
        plagiarism_html = f"""
        <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
            <div style="font-weight: 600; color: #92400e; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                ⚠️ Students with Similar Code
            </div>
            <div style="max-height: 150px; overflow-y: auto;">
                {similar_list}
            </div>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Submission Report</title>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px;">
        <div style="max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; padding: 24px; text-align: center;">
                <h1 style="margin: 0; font-size: 22px;">📊 Submission Report</h1>
                <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 14px;">Data Structure Evaluator</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 24px;">
                <p style="font-size: 15px; color: #374151; margin-bottom: 20px;">Dear <strong>{html.escape(student_name)}</strong>,</p>
                
                <!-- Submission Info Grid -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
                    <div style="background: #f8fafc; padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Problem</div>
                        <div style="font-weight: 600; color: #1e293b; margin-top: 4px;">{html.escape(problem_title)}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">File</div>
                        <div style="font-weight: 600; color: #1e293b; margin-top: 4px;">{html.escape(filename)}</div>
                    </div>
                    <div style="background: #f8fafc; padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Status</div>
                        <div style="margin-top: 4px;">
                            <span style="background: {status_bg}; color: {status_color}; padding: 4px 10px; border-radius: 4px; font-weight: 600; font-size: 13px;">{status_text}</span>
                        </div>
                    </div>
                    <div style="background: #f8fafc; padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Score</div>
                        <div style="font-weight: 700; font-size: 20px; color: #1e293b; margin-top: 4px;">{score}/100</div>
                    </div>
                </div>
                
                <!-- AI Detection & Submitted -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; background: #f1f5f9; padding: 16px; border-radius: 8px;">
                    <div>
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">🤖 AI Detection</div>
                        <div>
                            <span style="color: {ai_color}; font-weight: 700; font-size: 18px;">{ai_score}%</span>
                            <span style="font-size: 12px; color: #64748b; margin-left: 8px;">{ai_label}</span>
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">📅 Submitted</div>
                        <div style="font-weight: 600; color: #1e293b;">{submitted_at}</div>
                    </div>
                </div>
                
                <!-- Plagiarism Warning (only shown if matches exist) -->
                {plagiarism_html}
                
                <!-- Code Preview -->
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">💻 Submitted Code</div>
                    <pre style="background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px; font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; font-family: 'Consolas', 'Monaco', monospace; max-height: 300px; line-height: 1.5;">{code_escaped}</pre>
                </div>
                
                <!-- Evaluation Report -->
                <div style="background: linear-gradient(135deg, #f8fafc, #f1f5f9); padding: 20px; border-radius: 8px; border-left: 4px solid #4f46e5;">
                    <div style="font-size: 14px; font-weight: 600; color: #1e293b; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                        🔒 AI Evaluation Report
                    </div>
                    <div style="font-size: 13px; color: #374151; line-height: 1.7;">
                        {evaluation_html}
                    </div>
                </div>
                
                <p style="font-size: 11px; color: #9ca3af; margin-top: 24px; text-align: center; border-top: 1px solid #e5e7eb; padding-top: 16px;">
                    This is an automated report from Data Structure Evaluator.<br>
                    Please do not reply to this email.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


def generate_report_html(student_name, submissions):
    """Generate HTML report for a student's submissions (summary view)"""
    
    if not submissions:
        return None
    
    # If only one submission, use the detailed report
    if len(submissions) == 1:
        return generate_submission_report_html(student_name, submissions[0])
    
    # Build submissions with detailed info
    submissions_html = ""
    accepted_count = 0
    
    for i, sub in enumerate(submissions, 1):
        status = sub.get('status', 'pending')
        score = sub.get('score', 0)
        ai_score = sub.get('ai_score', 0)
        problem_title = sub.get('problem_title', 'N/A')
        filename = sub.get('filename', 'N/A')
        file_content = sub.get('file_content', 'No code available')
        evaluation = sub.get('evaluation', 'No evaluation available')
        similar_students = sub.get('similar_students', [])
        
        if status == 'accepted':
            accepted_count += 1
        
        status_bg = "#d1fae5" if status == 'accepted' else "#fee2e2"
        status_color = "#166534" if status == 'accepted' else "#991b1b"
        status_text = "✓ Accepted" if status == 'accepted' else "✗ Rejected"
        
        ai_color = "#dc2626" if ai_score >= 70 else "#f59e0b" if ai_score >= 40 else "#22c55e"
        ai_label = "Likely AI" if ai_score >= 70 else "Uncertain" if ai_score >= 40 else "Likely Human"
        
        code_escaped = html.escape(file_content)[:500] + ('...' if len(file_content) > 500 else '')
        evaluation_html = format_evaluation_html(evaluation)
        
        # Build plagiarism warning for this submission (only if matches exist)
        plagiarism_html = ""
        if similar_students:
            similar_items = ""
            for s in similar_students:
                similar_items += f"""
                <span style="display: inline-block; background: white; padding: 4px 8px; border-radius: 4px; margin: 2px; font-size: 11px;">
                    <strong>{html.escape(s.get('name', 'Unknown'))}</strong> 
                    <span style="color: {'#dc2626' if s.get('similarity', 0) >= 90 else '#f59e0b'}; font-weight: 600;">{s.get('similarity', 0)}%</span>
                </span>
                """
            plagiarism_html = f"""
            <div style="padding: 12px 16px; background: #fef3c7; border-bottom: 1px solid #e5e7eb;">
                <div style="font-size: 11px; color: #92400e; font-weight: 600; margin-bottom: 6px;">⚠️ Similar Code Detected:</div>
                <div>{similar_items}</div>
            </div>
            """
        
        submissions_html += f"""
        <div style="background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 16px; overflow: hidden;">
            <!-- Submission Header -->
            <div style="background: #f8fafc; padding: 12px 16px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div>
                    <span style="font-weight: 600; color: #1e293b;">#{i} {html.escape(problem_title)}</span>
                    <span style="color: #64748b; font-size: 12px; margin-left: 8px;">{html.escape(filename)}</span>
                </div>
                <span style="background: {status_bg}; color: {status_color}; padding: 4px 10px; border-radius: 4px; font-weight: 600; font-size: 12px;">{status_text}</span>
            </div>
            
            <!-- Stats Row -->
            <div style="display: flex; gap: 20px; padding: 12px 16px; border-bottom: 1px solid #e5e7eb; flex-wrap: wrap;">
                <div>
                    <span style="font-size: 11px; color: #64748b;">Score:</span>
                    <span style="font-weight: 700; color: #1e293b; margin-left: 4px;">{score}/100</span>
                </div>
                <div>
                    <span style="font-size: 11px; color: #64748b;">AI Detection:</span>
                    <span style="font-weight: 600; color: {ai_color}; margin-left: 4px;">{ai_score}%</span>
                    <span style="font-size: 11px; color: #64748b; margin-left: 4px;">({ai_label})</span>
                </div>
            </div>
            
            <!-- Plagiarism Warning (only if matches) -->
            {plagiarism_html}
            
            <!-- Code Preview -->
            <div style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb;">
                <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">Code Preview:</div>
                <pre style="background: #1e293b; color: #e2e8f0; padding: 10px; border-radius: 6px; font-size: 11px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; font-family: 'Consolas', 'Monaco', monospace; max-height: 150px;">{code_escaped}</pre>
            </div>
            
            <!-- Evaluation -->
            <div style="padding: 12px 16px; background: #fafafa;">
                <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">Evaluation:</div>
                <div style="font-size: 12px; color: #374151; line-height: 1.6;">
                    {evaluation_html}
                </div>
            </div>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Submission Report</title>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px;">
        <div style="max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; padding: 24px; text-align: center;">
                <h1 style="margin: 0; font-size: 22px;">📊 Submission Report</h1>
                <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 14px;">Data Structure Evaluator</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 24px;">
                <p style="font-size: 15px; color: #374151;">Dear <strong>{html.escape(student_name)}</strong>,</p>
                <p style="font-size: 13px; color: #6b7280; margin-top: 8px;">Here is your complete submission report:</p>
                
                <!-- Summary Stats -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 20px 0;">
                    <div style="text-align: center; padding: 16px; background: #f0fdf4; border-radius: 8px;">
                        <div style="font-size: 24px; font-weight: 700; color: #22c55e;">{len(submissions)}</div>
                        <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">Submissions</div>
                    </div>
                    <div style="text-align: center; padding: 16px; background: #eff6ff; border-radius: 8px;">
                        <div style="font-size: 24px; font-weight: 700; color: #3b82f6;">{accepted_count}</div>
                        <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">Accepted</div>
                    </div>
                </div>
                
                <!-- Submissions List -->
                <div style="margin-top: 24px;">
                    {submissions_html}
                </div>
                
                <p style="font-size: 11px; color: #9ca3af; margin-top: 24px; text-align: center; border-top: 1px solid #e5e7eb; padding-top: 16px;">
                    This is an automated report from Data Structure Evaluator.<br>
                    Please do not reply to this email.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


def send_report_email(to_email, student_name, submissions):
    """Send a report email to a student"""
    
    if not is_email_configured():
        return {'success': False, 'message': 'Email not configured. Set SMTP_USER and SMTP_PASSWORD environment variables.'}
    
    if not to_email:
        return {'success': False, 'message': 'No email address provided'}
    
    if not submissions:
        return {'success': False, 'message': 'No submissions to report'}
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 Your Submission Report - Data Structure Evaluator"
        msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg['To'] = to_email
        
        # Generate HTML content
        html_content = generate_report_html(student_name, submissions)
        
        # Plain text fallback
        text_content = f"""
Dear {student_name},

Here is your submission report from Data Structure Evaluator.

Total Submissions: {len(submissions)}
Accepted: {sum(1 for s in submissions if s['status'] == 'accepted')}

Please check your email client with HTML support for the full report.

Best regards,
Data Structure Evaluator
        """
        
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        return {'success': True, 'message': f'Report sent to {to_email}'}
    
    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'message': 'SMTP authentication failed. Check credentials.'}
    except smtplib.SMTPException as e:
        return {'success': False, 'message': f'SMTP error: {str(e)}'}
    except Exception as e:
        return {'success': False, 'message': f'Error sending email: {str(e)}'}


def send_bulk_reports(submissions_by_student):
    """
    Send reports to multiple students.
    submissions_by_student: dict with key=register_no, value={'email': str, 'name': str, 'submissions': list}
    """
    results = {
        'sent': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }
    
    for register_no, data in submissions_by_student.items():
        email = data.get('email')
        name = data.get('name', register_no)
        subs = data.get('submissions', [])
        
        if not email:
            results['skipped'] += 1
            results['details'].append({
                'student': name,
                'status': 'skipped',
                'reason': 'No email address'
            })
            continue
        
        if not subs:
            results['skipped'] += 1
            results['details'].append({
                'student': name,
                'status': 'skipped',
                'reason': 'No submissions'
            })
            continue
        
        result = send_report_email(email, name, subs)
        
        if result['success']:
            results['sent'] += 1
            results['details'].append({
                'student': name,
                'email': email,
                'status': 'sent'
            })
        else:
            results['failed'] += 1
            results['details'].append({
                'student': name,
                'email': email,
                'status': 'failed',
                'reason': result['message']
            })
    
    return results
