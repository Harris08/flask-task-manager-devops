from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import boto3
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

s3 = boto3.client(
    's3',
    region_name=os.getenv('AWS_REGION', 'ap-south-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

BUCKET = os.getenv('AWS_S3_BUCKET')

def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "mysql"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "rootpass"),
        database=os.getenv("MYSQL_DATABASE", "taskdb")
    )

@app.route("/")
def index():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = cursor.fetchall()
    db.close()
    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
def add_task():
    title       = request.form.get("title")
    description = request.form.get("description")
    created_by  = request.form.get("created_by", "Anonymous")
    file        = request.files.get("file")
    s3_file_key = None

    if file and file.filename != "":
        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_file_key = f"tasks/{timestamp}_{file.filename}"
        s3.upload_fileobj(file, BUCKET, s3_file_key)

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, description, created_by, s3_file_key) VALUES (%s, %s, %s, %s)",
        (title, description, created_by, s3_file_key)
    )
    db.commit()
    db.close()
    return redirect(url_for("index"))

@app.route("/download/<int:task_id>")
def download_file(task_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT s3_file_key FROM tasks WHERE id = %s", (task_id,))
    task = cursor.fetchone()
    db.close()

    if task and task["s3_file_key"]:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET, 'Key': task["s3_file_key"]},
            ExpiresIn=300
        )
        from flask import redirect as flask_redirect
        return flask_redirect(url)
    return "No file attached", 404

@app.route("/delete/<int:task_id>")
def delete_task(task_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT s3_file_key FROM tasks WHERE id = %s", (task_id,))
    task = cursor.fetchone()

    if task and task["s3_file_key"]:
        s3.delete_object(Bucket=BUCKET, Key=task["s3_file_key"])

    cursor = db.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    db.commit()
    db.close()
    return redirect(url_for("index"))

@app.route("/complete/<int:task_id>")
def complete_task(task_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE tasks SET status='complete' WHERE id = %s",
        (task_id,)
    )
    db.commit()
    db.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)