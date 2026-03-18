from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def get_db():
    conn = sqlite3.connect("assignments.db")
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)

@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS tasks "
    "(id INTEGER PRIMARY KEY, subject TEXT, description TEXT, due_date TEXT, done INTEGER DEFAULT 0)")
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    conn.close()


    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
def add_tasks():
    subject = request.form['subject']
    description = request.form['description']
    due_date = request.form['due_date']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (subject, description, due_date, done) VALUES (?, ?, ?, ?)",
                   (subject, description, due_date, 0))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/complete", methods=["POST"])
def complete_task():
        conn = get_db()
        cursor = conn.cursor()
        task_id = request.form['id']
        cursor.execute("UPDATE tasks SET done = ? WHERE id =?",
                   ( 1, task_id))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

@app.route("/delete", methods= ['POST'])
def delete_task():
    conn = get_db()
    cursor = conn.cursor()
    task_id = request.form['id']
    cursor.execute("DELETE FROM tasks WHERE id =?",
                   (task_id, ))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


def format_task(tasks):
    task_list=[]
    for task in tasks:
        if task["done"] == 0:
            task_list.append(f"{task['subject']} - {task['description']} - due {task['due_date']}"
            )
    return "\n".join(task_list)


def get_study_advice(tasks):
    chat = client.chats.create(model="gemini-2.5-flash")

    formatted_tasks = format_task(tasks)

    response1 = chat.send_message(
        f"""Check these assignments:
{formatted_tasks}

From pending tasks, determine which is most important based on workload and due date.
Plain text, max 3 sentences."""
    )

    response2 = chat.send_message(
        "What is the best way to approach the task in the time available? Max 3 sentences, plain text only."
    )

    return response1.text, response2.text

@app.route("/analyse")
def analyse():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    priority, strategy = get_study_advice(tasks)

    return render_template("index.html", tasks= tasks, priority=priority, strategy = strategy)

if __name__ == "__main__":
    app.run(debug=True)