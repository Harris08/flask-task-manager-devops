import os
import secrets
import string
import boto3
from botocore.exceptions import ClientError
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pymysql
from datetime import datetime, timedelta
import hashlib
import time

# ─────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'taskmanager-secret-2026')

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DB_HOST     = os.environ.get('MYSQL_HOST', 'mysql')
DB_USER     = os.environ.get('MYSQL_USER', 'root')
DB_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'password')
DB_NAME     = os.environ.get('MYSQL_DATABASE', 'taskdb')

AWS_REGION       = os.environ.get('AWS_REGION', 'ap-south-1')
S3_BUCKET        = os.environ.get('AWS_S3_BUCKET', 'hari-taskmanager-bucket')
SES_FROM_EMAIL   = os.environ.get('SES_FROM_EMAIL', 'haarisraja08@gmail.com')

# ─────────────────────────────────────────────
# FLASK-LOGIN
# ─────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to continue.'
login_manager.login_message_category = 'warning'


class User(UserMixin):
    def __init__(self, id, name, email, role, is_first_login):
        self.id             = id
        self.name           = name
        self.email          = email
        self.role           = role
        self.is_first_login = is_first_login


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, email, role, is_first_login FROM users WHERE id=%s", (user_id,))
            row = cur.fetchone()
            if row:
                return User(*row)
    finally:
        conn.close()
    return None


# ─────────────────────────────────────────────
# DATABASE HELPER
# ─────────────────────────────────────────────
def get_db():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


# ─────────────────────────────────────────────
# AWS HELPERS
# ─────────────────────────────────────────────
def get_s3():
    return boto3.client('s3', region_name=AWS_REGION)

def get_ses():
    return boto3.client('ses', region_name=AWS_REGION)


def upload_to_s3(file_obj, filename):
    """Upload file to S3, return the s3 key."""
    s3 = get_s3()
    timestamp = int(time.time())
    key = f"tasks/{timestamp}_{secure_filename(filename)}"
    s3.upload_fileobj(file_obj, S3_BUCKET, key)
    return key


def get_presigned_url(s3_key, expiry=3600):
    """Generate a presigned download URL."""
    s3 = get_s3()
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=expiry
        )
        return url
    except ClientError:
        return None


# ─────────────────────────────────────────────
# SES EMAIL HELPERS
# ─────────────────────────────────────────────
def send_email(to_email, subject, html_body):
    """Send email via AWS SES."""
    ses = get_ses()
    try:
        ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            }
        )
    except ClientError as e:
        print(f"[SES ERROR] {e.response['Error']['Message']}")


def email_welcome(name, email, temp_password):
    """Email 1: New employee created → send temp password."""
    html = f"""
    <div style="font-family:DM Sans,sans-serif;max-width:520px;margin:0 auto;background:#fff;border:1.5px solid #dbeafe;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);padding:24px 28px;">
        <h1 style="color:#fff;font-size:20px;margin:0;">🗂 Task Manager</h1>
      </div>
      <div style="padding:28px;">
        <h2 style="color:#0f172a;font-size:18px;margin-bottom:8px;">Welcome, {name}! 👋</h2>
        <p style="color:#334155;font-size:14px;line-height:1.6;">Your employee account has been created. Use the credentials below to sign in.</p>
        <div style="background:#f0f4ff;border:1.5px solid #dbeafe;border-radius:10px;padding:16px 20px;margin:20px 0;">
          <p style="margin:0 0 6px;font-size:13px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:.4px;">Login Credentials</p>
          <p style="margin:0 0 4px;font-size:14px;color:#0f172a;"><strong>Email:</strong> {email}</p>
          <p style="margin:0;font-size:14px;color:#0f172a;"><strong>Temporary Password:</strong> <code style="background:#dbeafe;padding:2px 8px;border-radius:5px;color:#1d4ed8;">{temp_password}</code></p>
        </div>
        <p style="color:#dc2626;font-size:13px;font-weight:600;">⚠ You will be required to change your password on first login.</p>
        <a href="http://13.203.97.210" style="display:inline-block;background:linear-gradient(135deg,#1d4ed8,#3b82f6);color:#fff;text-decoration:none;padding:10px 24px;border-radius:9px;font-weight:700;font-size:14px;margin-top:8px;">Sign In Now →</a>
      </div>
      <div style="background:#f8faff;border-top:1px solid #dbeafe;padding:14px 28px;font-size:12px;color:#94a3b8;">Task Manager © 2026 · Powered by AWS</div>
    </div>
    """
    send_email(email, "🗂 Welcome to Task Manager — Your Login Credentials", html)


def email_task_assigned(emp_name, emp_email, task_title, task_desc):
    """Email 2: Task assigned to employee."""
    html = f"""
    <div style="font-family:DM Sans,sans-serif;max-width:520px;margin:0 auto;background:#fff;border:1.5px solid #dbeafe;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);padding:24px 28px;">
        <h1 style="color:#fff;font-size:20px;margin:0;">🗂 Task Manager</h1>
      </div>
      <div style="padding:28px;">
        <h2 style="color:#0f172a;font-size:18px;margin-bottom:8px;">New Task Assigned 📋</h2>
        <p style="color:#334155;font-size:14px;">Hi <strong>{emp_name}</strong>, a new task has been assigned to you.</p>
        <div style="background:#f0f4ff;border:1.5px solid #dbeafe;border-radius:10px;padding:16px 20px;margin:20px 0;">
          <p style="margin:0 0 6px;font-size:13px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:.4px;">Task Details</p>
          <p style="margin:0 0 4px;font-size:15px;font-weight:700;color:#0f172a;">{task_title}</p>
          <p style="margin:0;font-size:13px;color:#64748b;">{task_desc or 'No description provided.'}</p>
        </div>
        <a href="http://13.203.97.210" style="display:inline-block;background:linear-gradient(135deg,#1d4ed8,#3b82f6);color:#fff;text-decoration:none;padding:10px 24px;border-radius:9px;font-weight:700;font-size:14px;">View My Tasks →</a>
      </div>
      <div style="background:#f8faff;border-top:1px solid #dbeafe;padding:14px 28px;font-size:12px;color:#94a3b8;">Task Manager © 2026 · Powered by AWS</div>
    </div>
    """
    send_email(emp_email, f"📋 New Task Assigned: {task_title}", html)


def email_task_approved(emp_name, emp_email, task_title):
    """Email 3: Task approved → well done."""
    html = f"""
    <div style="font-family:DM Sans,sans-serif;max-width:520px;margin:0 auto;background:#fff;border:1.5px solid #86efac;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#16a34a,#22c55e);padding:24px 28px;">
        <h1 style="color:#fff;font-size:20px;margin:0;">🗂 Task Manager</h1>
      </div>
      <div style="padding:28px;">
        <h2 style="color:#0f172a;font-size:18px;margin-bottom:8px;">Task Approved! 🎉</h2>
        <p style="color:#334155;font-size:14px;">Great work, <strong>{emp_name}</strong>! Your task has been reviewed and approved.</p>
        <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:10px;padding:16px 20px;margin:20px 0;">
          <p style="margin:0 0 4px;font-size:13px;color:#64748b;font-weight:600;text-transform:uppercase;">Approved Task</p>
          <p style="margin:0;font-size:15px;font-weight:700;color:#0f172a;">✅ {task_title}</p>
        </div>
        <p style="color:#16a34a;font-size:14px;font-weight:600;">Keep up the excellent work! 💪</p>
      </div>
      <div style="background:#f8faff;border-top:1px solid #dbeafe;padding:14px 28px;font-size:12px;color:#94a3b8;">Task Manager © 2026 · Powered by AWS</div>
    </div>
    """
    send_email(emp_email, f"✅ Task Approved: {task_title} — Well Done!", html)


def email_task_redo(emp_name, emp_email, task_title):
    """Email 4: Task sent for redo → correction needed."""
    html = f"""
    <div style="font-family:DM Sans,sans-serif;max-width:520px;margin:0 auto;background:#fff;border:1.5px solid #fda4af;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#dc2626,#9f1239);padding:24px 28px;">
        <h1 style="color:#fff;font-size:20px;margin:0;">🗂 Task Manager</h1>
      </div>
      <div style="padding:28px;">
        <h2 style="color:#0f172a;font-size:18px;margin-bottom:8px;">Correction Needed 🔄</h2>
        <p style="color:#334155;font-size:14px;">Hi <strong>{emp_name}</strong>, your manager has reviewed your task and requested corrections.</p>
        <div style="background:#fff1f2;border:1.5px solid #fda4af;border-radius:10px;padding:16px 20px;margin:20px 0;">
          <p style="margin:0 0 4px;font-size:13px;color:#9f1239;font-weight:600;text-transform:uppercase;">Task Needs Redo</p>
          <p style="margin:0;font-size:15px;font-weight:700;color:#0f172a;">🔄 {task_title}</p>
        </div>
        <p style="color:#64748b;font-size:13px;">Please log in, review the task, and resubmit after making corrections.</p>
        <a href="http://13.203.97.210" style="display:inline-block;background:linear-gradient(135deg,#dc2626,#9f1239);color:#fff;text-decoration:none;padding:10px 24px;border-radius:9px;font-weight:700;font-size:14px;margin-top:8px;">View Task →</a>
      </div>
      <div style="background:#f8faff;border-top:1px solid #dbeafe;padding:14px 28px;font-size:12px;color:#94a3b8;">Task Manager © 2026 · Powered by AWS</div>
    </div>
    """
    send_email(emp_email, f"🔄 Correction Needed: {task_title}", html)


def email_password_reset(email, reset_url):
    """Password reset email."""
    html = f"""
    <div style="font-family:DM Sans,sans-serif;max-width:520px;margin:0 auto;background:#fff;border:1.5px solid #dbeafe;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);padding:24px 28px;">
        <h1 style="color:#fff;font-size:20px;margin:0;">🗂 Task Manager</h1>
      </div>
      <div style="padding:28px;">
        <h2 style="color:#0f172a;font-size:18px;margin-bottom:8px;">Reset Your Password 🔑</h2>
        <p style="color:#334155;font-size:14px;">Click the button below to reset your password. This link expires in <strong>30 minutes</strong>.</p>
        <a href="{reset_url}" style="display:inline-block;background:linear-gradient(135deg,#1d4ed8,#3b82f6);color:#fff;text-decoration:none;padding:12px 28px;border-radius:9px;font-weight:700;font-size:14px;margin:20px 0;">Reset Password →</a>
        <p style="color:#94a3b8;font-size:12px;">If you did not request this, ignore this email. Your password won't change.</p>
      </div>
      <div style="background:#f8faff;border-top:1px solid #dbeafe;padding:14px 28px;font-size:12px;color:#94a3b8;">Task Manager © 2026 · Powered by AWS SES</div>
    </div>
    """
    send_email(email, "🔑 Reset Your Task Manager Password", html)


# ─────────────────────────────────────────────
# RANDOM PASSWORD GENERATOR
# ─────────────────────────────────────────────
def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$"
    return ''.join(secrets.choice(chars) for _ in range(length))


# ─────────────────────────────────────────────
# ROUTES — AUTH
# ─────────────────────────────────────────────
@app.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        if current_user.role == 'manager':
            return redirect(url_for('manager_dashboard'))
        return redirect(url_for('employee_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, email, password_hash, role, is_first_login FROM users WHERE email=%s", (email,))
                row = cur.fetchone()
        finally:
            conn.close()

        if not row or not check_password_hash(row['password_hash'], password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

        user = User(row['id'], row['name'], row['email'], row['role'], row['is_first_login'])
        login_user(user)

        if user.is_first_login:
            return redirect(url_for('change_password'))

        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_pw  = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        if len(new_pw) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('change_password.html')

        if new_pw != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('change_password.html')

        hashed = generate_password_hash(new_pw)
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET password_hash=%s, is_first_login=FALSE WHERE id=%s",
                    (hashed, current_user.id)
                )
            conn.commit()
        finally:
            conn.close()

        flash('Password updated successfully! Welcome aboard.', 'success')
        return redirect(url_for('index'))

    return render_template('change_password.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email=%s", (email,))
                row = cur.fetchone()

            if row:
                # Generate token
                token = secrets.token_urlsafe(32)
                expires = datetime.utcnow() + timedelta(minutes=30)
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET reset_token=%s, reset_token_expires=%s WHERE email=%s",
                        (token, expires, email)
                    )
                conn.commit()

                reset_url = url_for('reset_password', token=token, _external=True)
                email_password_reset(email, reset_url)
        finally:
            conn.close()

        # Always show success (don't reveal if email exists)
        return render_template('forgot_password.html', sent=True, sent_email=email)

    return render_template('forgot_password.html', sent=False)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM users WHERE reset_token=%s AND reset_token_expires > %s",
                (token, datetime.utcnow())
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        flash('Reset link is invalid or has expired.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_pw  = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        if len(new_pw) < 8 or new_pw != confirm:
            flash('Passwords must match and be at least 8 characters.', 'error')
            return render_template('change_password.html')

        hashed = generate_password_hash(new_pw)
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET password_hash=%s, reset_token=NULL, reset_token_expires=NULL WHERE reset_token=%s",
                    (hashed, token)
                )
            conn.commit()
        finally:
            conn.close()

        flash('Password reset successfully. Please sign in.', 'success')
        return redirect(url_for('login'))

    return render_template('change_password.html')


# ─────────────────────────────────────────────
# ROUTES — MANAGER DASHBOARD
# ─────────────────────────────────────────────
@app.route('/manager')
@login_required
def manager_dashboard():
    if current_user.role != 'manager':
        flash('Access denied.', 'error')
        return redirect(url_for('employee_dashboard'))

    if current_user.is_first_login:
        return redirect(url_for('change_password'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.*, u.name AS assigned_name
                FROM tasks t
                LEFT JOIN users u ON t.assigned_to = u.id
                ORDER BY t.id DESC
            """)
            tasks = cur.fetchall()

            cur.execute("SELECT id, name, email FROM users WHERE role='employee' ORDER BY name")
            employees = cur.fetchall()
    finally:
        conn.close()

    return render_template('manager.html', tasks=tasks, employees=employees)


@app.route('/add-task', methods=['POST'])
@login_required
def add_task():
    if current_user.role != 'manager':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    assigned_to = request.form.get('assigned_to')
    file        = request.files.get('file')

    if not title or not assigned_to:
        flash('Title and assigned employee are required.', 'error')
        return redirect(url_for('manager_dashboard'))

    s3_key = None
    if file and file.filename:
        try:
            s3_key = upload_to_s3(file, file.filename)
        except Exception as e:
            flash(f'File upload failed: {str(e)}', 'warning')

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks (title, description, assigned_to, created_by, status, s3_file_key)
                VALUES (%s, %s, %s, %s, 'pending', %s)
            """, (title, description, assigned_to, current_user.id, s3_key))
        conn.commit()

        # Get employee email for notification
        with conn.cursor() as cur:
            cur.execute("SELECT name, email FROM users WHERE id=%s", (assigned_to,))
            emp = cur.fetchone()

        if emp:
            email_task_assigned(emp['name'], emp['email'], title, description)
    finally:
        conn.close()

    flash(f'Task "{title}" assigned successfully!', 'success')
    return redirect(url_for('manager_dashboard'))


@app.route('/approve-task/<int:task_id>')
@login_required
def approve_task(task_id):
    if current_user.role != 'manager':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT t.title, u.name, u.email FROM tasks t JOIN users u ON t.assigned_to=u.id WHERE t.id=%s", (task_id,))
            row = cur.fetchone()

        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET status='done' WHERE id=%s", (task_id,))
        conn.commit()

        if row:
            email_task_approved(row['name'], row['email'], row['title'])
    finally:
        conn.close()

    flash('Task approved! Employee notified.', 'success')
    return redirect(url_for('manager_dashboard'))


@app.route('/redo-task/<int:task_id>')
@login_required
def redo_task(task_id):
    if current_user.role != 'manager':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT t.title, u.name, u.email FROM tasks t JOIN users u ON t.assigned_to=u.id WHERE t.id=%s", (task_id,))
            row = cur.fetchone()

        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET status='redo' WHERE id=%s", (task_id,))
        conn.commit()

        if row:
            email_task_redo(row['name'], row['email'], row['title'])
    finally:
        conn.close()

    flash('Task sent back for redo. Employee notified.', 'warning')
    return redirect(url_for('manager_dashboard'))


@app.route('/delete-task/<int:task_id>')
@login_required
def delete_task(task_id):
    if current_user.role != 'manager':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT s3_file_key FROM tasks WHERE id=%s", (task_id,))
            row = cur.fetchone()

        # Delete from S3 if exists
        if row and row['s3_file_key']:
            try:
                get_s3().delete_object(Bucket=S3_BUCKET, Key=row['s3_file_key'])
            except Exception:
                pass

        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
        conn.commit()
    finally:
        conn.close()

    flash('Task deleted.', 'info')
    return redirect(url_for('manager_dashboard'))


@app.route('/create-employee', methods=['POST'])
@login_required
def create_employee():
    if current_user.role != 'manager':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    name  = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()

    if not name or not email:
        flash('Name and email are required.', 'error')
        return redirect(url_for('manager_dashboard'))

    temp_password = generate_temp_password()
    hashed        = generate_password_hash(temp_password)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                flash('An account with this email already exists.', 'error')
                return redirect(url_for('manager_dashboard'))

            cur.execute("""
                INSERT INTO users (name, email, password_hash, role, is_first_login)
                VALUES (%s, %s, %s, 'employee', TRUE)
            """, (name, email, hashed))
        conn.commit()
    finally:
        conn.close()

    email_welcome(name, email, temp_password)
    flash(f'Employee "{name}" created! Login credentials sent to {email}.', 'success')
    return redirect(url_for('manager_dashboard'))


# ─────────────────────────────────────────────
# ROUTES — EMPLOYEE DASHBOARD
# ─────────────────────────────────────────────
@app.route('/employee')
@login_required
def employee_dashboard():
    if current_user.role != 'employee':
        flash('Access denied.', 'error')
        return redirect(url_for('manager_dashboard'))

    if current_user.is_first_login:
        return redirect(url_for('change_password'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM tasks
                WHERE assigned_to = %s
                ORDER BY id DESC
            """, (current_user.id,))
            tasks = cur.fetchall()
    finally:
        conn.close()

    return render_template('employee.html', tasks=tasks)


@app.route('/complete-task/<int:task_id>')
@login_required
def complete_task(task_id):
    if current_user.role != 'employee':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Verify task belongs to this employee
            cur.execute("SELECT id FROM tasks WHERE id=%s AND assigned_to=%s", (task_id, current_user.id))
            if not cur.fetchone():
                flash('Task not found.', 'error')
                return redirect(url_for('employee_dashboard'))

            cur.execute("UPDATE tasks SET status='done' WHERE id=%s", (task_id,))
        conn.commit()
    finally:
        conn.close()

    flash('Task marked as done! Awaiting manager approval.', 'success')
    return redirect(url_for('employee_dashboard'))


@app.route('/upload/<int:task_id>', methods=['POST'])
@login_required
def upload_file(task_id):
    if current_user.role != 'employee':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    file = request.files.get('file')
    if not file or not file.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('employee_dashboard'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM tasks WHERE id=%s AND assigned_to=%s", (task_id, current_user.id))
            if not cur.fetchone():
                flash('Task not found.', 'error')
                return redirect(url_for('employee_dashboard'))

        try:
            s3_key = upload_to_s3(file, file.filename)
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'error')
            return redirect(url_for('employee_dashboard'))

        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET s3_file_key=%s WHERE id=%s", (s3_key, task_id))
        conn.commit()
    finally:
        conn.close()

    flash('File uploaded successfully!', 'success')
    return redirect(url_for('employee_dashboard'))


@app.route('/download/<int:task_id>')
@login_required
def download_file(task_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT s3_file_key, assigned_to FROM tasks WHERE id=%s", (task_id,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row or not row['s3_file_key']:
        flash('No file attached to this task.', 'error')
        return redirect(url_for('index'))

    # Employees can only download their own task files
    if current_user.role == 'employee' and row['assigned_to'] != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('employee_dashboard'))

    url = get_presigned_url(row['s3_file_key'])
    if not url:
        flash('Could not generate download link.', 'error')
        return redirect(url_for('index'))

    return redirect(url)


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)