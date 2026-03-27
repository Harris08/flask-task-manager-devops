# 🗂️ Flask Task Manager — DevOps Project

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20S3%20%7C%20Lambda%20%7C%20SES-FF9900?logo=amazonaws)
![Apache](https://img.shields.io/badge/Apache2-Reverse%20Proxy-D22128?logo=apache)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql)
![CI/CD](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?logo=githubactions)
![CloudWatch](https://img.shields.io/badge/CloudWatch-Monitoring-FF4F8B?logo=amazonaws)

A full-stack **role-based Task Manager web application** built with Flask, featuring user authentication, manager/employee workflows, AWS SES email notifications, S3 file storage, and deployed on AWS using DevOps best practices — Docker, CI/CD, serverless functions, and real-time monitoring.

> 🔗 **Live App:** http://13.203.97.210
> 📦 **Repo:** https://github.com/Harris08/flask-task-manager-devops

---

## 🏗️ Architecture

```
Developer
    │
    ├── git push
    │       │
    │       ▼
    │   GitHub Actions (CI/CD)
    │       │
    │       ├── Checkout Code
    │       ├── Build Docker Image
    │       ├── Push to Docker Hub
    │       └── Deploy to EC2 via SSH
    │               ├── git pull origin main
    │               ├── Write .env from Secrets
    │               ├── docker-compose down
    │               ├── docker-compose pull
    │               └── docker-compose up -d --build
    │
    ▼
AWS EC2 (t2.micro) — Ubuntu 22.04
    │
    └── Docker Compose (app-network)
            │
            ├── Apache2 Container (Port 80) ← Reverse Proxy
            │       └── Proxy Pass → Flask
            │
            ├── Flask App Container (Port 5000)
            │       ├── User Authentication (Flask-Login)
            │       ├── Role-based Access (Manager / Employee)
            │       ├── Task CRUD + Assign / Approve / Redo workflow
            │       ├── Employee account creation with temp password
            │       ├── File upload → S3 (presigned URL download)
            │       ├── Password reset via email token
            │       └── 5 styled HTML email notifications via SES
            │
            └── MySQL 8.0 Container (Port 3306)
                    └── taskdb database (users + tasks tables)

AWS Services
    ├── S3 Bucket (hari-taskmanager-bucket)
    │       └── Stores uploaded files (tasks/ prefix)
    │
    ├── Lambda (task-file-processor)
    │       ├── Triggered by S3 PUT event
    │       └── Sends plain-text email via SES on upload
    │
    ├── SES (Simple Email Service)
    │       ├── Lambda: file upload notification
    │       └── Flask: welcome, task assigned, task approved,
    │               task redo, password reset emails
    │
    ├── CloudWatch
    │       └── Monitoring dashboard (CPU, Network, Lambda)
    │
    └── IAM
            └── Roles & policies for EC2, Lambda, S3, SES
```

---

## ✨ Features

- ✅ **User authentication** — login, logout, password change, forgot/reset password via SES email
- ✅ **Role-based access** — Manager and Employee dashboards with separate permissions
- ✅ **First-login password change** — employees must change temp password on first sign-in
- ✅ **Manager creates employees** — auto-generates temp password, sends welcome email via SES
- ✅ **Task assignment** — manager assigns tasks to specific employees with title, description, and optional file
- ✅ **Task workflow** — manager can approve tasks or send them back for redo
- ✅ **Employee task view** — employees see only their assigned tasks
- ✅ **Mark tasks as done** — employees can mark tasks complete; managers can delete tasks
- ✅ **File upload to S3** — both manager (on task creation) and employee (on their tasks)
- ✅ **Presigned URL download** — secure, time-limited file access from S3
- ✅ **5 styled HTML email notifications** — welcome, task assigned, task approved, task redo, password reset
- ✅ **Lambda email notification** — separate plain-text email triggered on S3 file upload
- ✅ **MySQL database** — persistent storage for users and tasks
- ✅ **Responsive UI** — built with Bootstrap 5, Bootstrap Icons, Google Fonts (DM Sans, Syne)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, Flask 3.0, Flask-Login |
| **Database** | MySQL 8.0 (via PyMySQL) |
| **Frontend** | HTML, Bootstrap 5, Bootstrap Icons, Jinja2, Google Fonts |
| **Auth** | Werkzeug (password hashing), Flask-Login (session management) |
| **Containerization** | Docker, Docker Compose |
| **Reverse Proxy** | Apache2 (httpd 2.4) |
| **Cloud Provider** | AWS (ap-south-1) |
| **File Storage** | AWS S3 |
| **Serverless** | AWS Lambda (Python 3.11) |
| **Email** | AWS SES (from Flask + Lambda) |
| **Monitoring** | AWS CloudWatch |
| **CI/CD** | GitHub Actions |
| **DB Admin** | TablePlus (SSH Tunnel) |

---

## 🚀 CI/CD Pipeline

```
git push (main) → GitHub Actions triggered
               │
               ├── 1. Checkout code
               ├── 2. Login to Docker Hub
               ├── 3. Build Docker image
               ├── 4. Push to Docker Hub
               └── 5. SSH into EC2
                       ├── git pull origin main
                       ├── Write .env from GitHub Secrets
                       ├── docker-compose down
                       ├── docker-compose pull
                       └── docker-compose up -d --build
```

**Pipeline runs in ~48 seconds** ⚡

---

## ☁️ AWS Infrastructure

| Service | Purpose | Region |
|---|---|---|
| EC2 t2.micro | Application server | ap-south-1 |
| S3 Bucket | File attachments storage | ap-south-1 |
| Lambda | Serverless file upload notifier | ap-south-1 |
| SES | Email notifications (5 from Flask + 1 from Lambda) | ap-south-1 |
| CloudWatch | Monitoring & alerting | ap-south-1 |
| IAM | Access management | Global |

---

## 📊 CloudWatch Monitoring Dashboard

The `flask-task-manager-dashboard` monitors:
- **CPU Utilization** — EC2 instance performance
- **NetworkIn / NetworkOut** — Traffic monitoring
- **Lambda Invocations** — Serverless function calls
- **Lambda Errors** — Error rate tracking

---

## 🗄️ Database Schema

```sql
CREATE TABLE users (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(100) NOT NULL,
    email               VARCHAR(150) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    role                ENUM('manager', 'employee') DEFAULT 'employee',
    is_first_login      BOOLEAN DEFAULT TRUE,
    reset_token         VARCHAR(255),
    reset_token_expires DATETIME,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tasks (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    assigned_to INT,
    created_by  INT,
    status      ENUM('pending', 'done', 'redo') DEFAULT 'pending',
    s3_file_key VARCHAR(500),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    FOREIGN KEY (created_by)  REFERENCES users(id)
);
```

---

## ⚙️ Local Setup

### Prerequisites
- Docker & Docker Compose
- AWS Account with S3, SES, Lambda configured
- AWS credentials

### 1. Clone the repo
```bash
git clone https://github.com/Harris08/flask-task-manager-devops.git
cd flask-task-manager-devops
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your values
```

```env
MYSQL_HOST=mysql
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=taskdb
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=your_bucket
AWS_REGION=ap-south-1
SES_FROM_EMAIL=your_email@gmail.com
SES_TO_EMAIL=your_email@gmail.com
```

### 3. Run with Docker Compose
```bash
docker-compose up -d
```

### 4. Access the app
```
http://localhost
```

---

## 🔐 Security Notes

- MySQL is **not exposed** to the public internet (internal Docker network only)
- S3 bucket is **private** — files accessed via presigned URLs only
- AWS credentials stored as **GitHub Secrets** (never hardcoded)
- TablePlus connects via **SSH tunnel** — no direct DB exposure
- Passwords hashed with **Werkzeug** (PBKDF2) — never stored in plain text
- Password reset tokens **expire after 30 minutes**
- First-login **forced password change** for new employees

---

## 📁 Project Structure

```
flask-task-manager-devops/
├── app/
│   ├── app.py                  # Flask application (auth, routes, SES emails)
│   ├── __init__.py             # Package init
│   ├── init.sql                # Database initialization
│   ├── templates/
│   │   ├── base.html           # Base layout template
│   │   ├── login.html          # Login page
│   │   ├── manager.html        # Manager dashboard
│   │   ├── employee.html       # Employee dashboard
│   │   ├── change_password.html # Change / reset password
│   │   ├── forgot-password.html # Forgot password page
│   │   └── index.html          # Landing / redirect page
│   └── static/                 # Static assets (CSS, JS, images)
├── apache2/
│   └── apache2.conf            # Apache reverse proxy config
├── lambda/
│   └── handler.py              # AWS Lambda function (S3 → SES notification)
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions CI/CD pipeline
├── screenshots/                # Project screenshots
├── docker-compose.yml          # Container orchestration (MySQL + Flask + Apache2)
├── Dockerfile                  # Flask app container (Python 3.11-slim)
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
└── LICENSE                     # MIT License
```

---

## 👨‍💻 Author

**Hari Krishnan**
- GitHub: [@Harris08](https://github.com/Harris08)
- Project: Flask Task Manager DevOps

---

## 📸 Screenshots

### Task Manager UI
> Add screenshot of the main UI here

### S3 Bucket
> Add screenshot of files in S3 here

### GitHub Actions CI/CD
> Add screenshot of green pipeline here

### CloudWatch Dashboard
> Add screenshot of monitoring dashboard here

### TablePlus Database View
> Add screenshot of TablePlus connected here

---

*Built as a DevOps portfolio project demonstrating end-to-end cloud deployment, containerization, CI/CD automation, role-based authentication, and AWS managed services.*
