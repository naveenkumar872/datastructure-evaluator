"""
Email utility module for sending submission reports to students
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Email configuration from environment variables
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', SMTP_USER)
SENDER_NAME = os.environ.get('SENDER_NAME', 'Data Structure Evaluator')


def is_email_configured():
    """Check if email settings are properly configured"""
    return bool(SMTP_USER and SMTP_PASSWORD)


def generate_report_html(student_name, submissions):
    """Generate HTML report for a student's submissions"""
    
    if not submissions:
        return None
    
    # Build submissions table rows
    rows_html = ""
    total_score = 0
    accepted_count = 0
    
    for sub in submissions:
        status_class = "color: #22c55e;" if sub['status'] == 'accepted' else "color: #ef4444;"
        status_text = "✓ Accepted" if sub['status'] == 'accepted' else "✗ Rejected"
        score = sub.get('score', 0)
        total_score += score
        if sub['status'] == 'accepted':
            accepted_count += 1
        
        rows_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{sub.get('problem_title', 'N/A')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{sub.get('filename', 'N/A')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; {status_class} font-weight: 600;">{status_text}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; font-weight: 600;">{score}/100</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{sub.get('submitted_at', 'N/A')}</td>
        </tr>
        """
    
    avg_score = total_score / len(submissions) if submissions else 0
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Submission Report</title>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px;">
        <div style="max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">📊 Submission Report</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Data Structure Evaluator</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px;">
                <p style="font-size: 16px; color: #374151;">Dear <strong>{student_name}</strong>,</p>
                <p style="font-size: 14px; color: #6b7280;">Here is your submission report summary:</p>
                
                <!-- Stats -->
                <div style="display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 150px; background: #f0fdf4; padding: 20px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 28px; font-weight: 700; color: #22c55e;">{len(submissions)}</div>
                        <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">Total Submissions</div>
                    </div>
                    <div style="flex: 1; min-width: 150px; background: #eff6ff; padding: 20px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 28px; font-weight: 700; color: #3b82f6;">{accepted_count}</div>
                        <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">Accepted</div>
                    </div>
                    <div style="flex: 1; min-width: 150px; background: #fef3c7; padding: 20px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 28px; font-weight: 700; color: #f59e0b;">{avg_score:.1f}</div>
                        <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">Avg Score</div>
                    </div>
                </div>
                
                <!-- Submissions Table -->
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px;">
                    <thead>
                        <tr style="background: #f9fafb;">
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; color: #374151;">Problem</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; color: #374151;">File</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; color: #374151;">Status</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; color: #374151;">Score</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; color: #374151;">Submitted</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                
                <p style="font-size: 12px; color: #9ca3af; margin-top: 30px; text-align: center;">
                    This is an automated report from Data Structure Evaluator.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


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
