from flask import Flask, render_template, request, redirect, session, flash
from flask_session import Session
from cs50 import SQL
from werkzeug.security import generate_password_hash, check_password_hash

from helpers import apology, login_required

app = Flask(__name__)

# Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Configure database
db = SQL("sqlite:///skillsync.db")


# ---------------- HOME ---------------- #

@app.route("/")
def index():
    return render_template("index.html")


# ---------------- ABOUT ---------------- #

@app.route("/about")
def about():
    return render_template("about.html")


# ---------------- REGISTER ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():

    session.clear()

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Validation
        if not username:
            return apology("must provide username")

        if not password:
            return apology("must provide password")

        if not confirmation:
            return apology("must confirm password")

        if password != confirmation:
            return apology("passwords do not match")

        # Check if username exists
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?",
            username
        )

        if len(rows) != 0:
            return apology("username already exists")

        # Hash password
        hash_password = generate_password_hash(password)

        # Insert user
        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            username,
            hash_password
        )

        flash("Registered successfully!")

        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear()

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Validation
        if not username:
            return apology("must provide username")

        if not password:
            return apology("must provide password")

        # Query database
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?",
            username
        )

        # Check username/password
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password")

        # Remember user
        session["user_id"] = rows[0]["id"]

        flash("Logged in successfully!")

        return redirect("/dashboard")

    return render_template("login.html")


# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully!")

    return redirect("/")


# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
@login_required
def dashboard():

    user_id = session["user_id"]

    # Get tasks
    tasks = db.execute(
        """
        SELECT * FROM tasks
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        user_id
    )

    # Get notes
    notes = db.execute(
        """
        SELECT * FROM notes
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        user_id
    )

    total_tasks = len(tasks)

    completed_tasks = len(
        [task for task in tasks if task["completed"] == 1]
    )

    return render_template(
        "dashboard.html",
        tasks=tasks,
        notes=notes,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks
    )


# ---------------- TASKS PAGE ---------------- #

@app.route("/tasks")
@login_required
def tasks():

    tasks = db.execute(
        """
        SELECT * FROM tasks
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        session["user_id"]
    )

    return render_template(
        "tasks.html",
        tasks=tasks
    )

# ---------------- ADD TASK ---------------- #

@app.route("/add_task", methods=["POST"])
@login_required
def add_task():

    task = request.form.get("task")
    subject = request.form.get("subject")
    deadline = request.form.get("deadline")

    if not task:
        return apology("must provide task")

    if not subject:
        return apology("must provide subject")

    db.execute(
        """
        INSERT INTO tasks
        (user_id, task, subject, deadline)
        VALUES (?, ?, ?, ?)
        """,
        session["user_id"],
        task,
        subject,
        deadline
    )

    flash("Task added successfully!")

    return redirect("/dashboard")


# ---------------- COMPLETE TASK ---------------- #

@app.route("/complete_task/<int:task_id>")
@login_required
def complete_task(task_id):

    db.execute(
        """
        UPDATE tasks
        SET completed = 1
        WHERE id = ? AND user_id = ?
        """,
        task_id,
        session["user_id"]
    )

    flash("Task completed!")

    return redirect("/dashboard")


# ---------------- DELETE TASK ---------------- #

@app.route("/delete_task/<int:task_id>")
@login_required
def delete_task(task_id):

    db.execute(
        """
        DELETE FROM tasks
        WHERE id = ? AND user_id = ?
        """,
        task_id,
        session["user_id"]
    )

    flash("Task deleted!")

    return redirect("/dashboard")


# ---------------- NOTES PAGE ---------------- #

@app.route("/notes")
@login_required
def notes():

    notes = db.execute(
        """
        SELECT * FROM notes
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        session["user_id"]
    )

    return render_template(
        "notes.html",
        notes=notes
    )

    
# ---------------- ADD NOTE ---------------- #

@app.route("/add_note", methods=["POST"])
@login_required
def add_note():

    title = request.form.get("title")
    content = request.form.get("content")

    if not title:
        return apology("must provide note title")

    if not content:
        return apology("must provide note content")

    db.execute(
        """
        INSERT INTO notes
        (user_id, title, content)
        VALUES (?, ?, ?)
        """,
        session["user_id"],
        title,
        content
    )

    flash("Note added successfully!")

    return redirect("/dashboard")


# ---------------- DELETE NOTE ---------------- #

@app.route("/delete_note/<int:note_id>")
@login_required
def delete_note(note_id):

    db.execute(
        """
        DELETE FROM notes
        WHERE id = ? AND user_id = ?
        """,
        note_id,
        session["user_id"]
    )

    flash("Note deleted!")

    return redirect("/dashboard")


# ---------------- AI ASSISTANT ---------------- #

@app.route("/ai_assistant", methods=["GET", "POST"])
@login_required
def ai_assistant():

    suggestion = None

    if request.method == "POST":

        subject = request.form.get("subject")
        hours = request.form.get("hours")
        difficulty = request.form.get("difficulty")

        if not subject:
            return apology("must provide subject")

        if not hours:
            return apology("must provide study hours")

        if not difficulty:
            return apology("must provide difficulty")

        hours = int(hours)

        # Rule-based AI logic

        if difficulty == "Hard" and hours < 2:

            suggestion = (
                f"{subject} seems difficult for you. "
                "Increase study hours and use Pomodoro technique."
            )

        elif difficulty == "Medium":

            suggestion = (
                f"Stay consistent in {subject} "
                "and revise daily for better retention."
            )

        elif difficulty == "Easy":

            suggestion = (
                f"You are doing well in {subject}. "
                "Focus on practice and mock questions."
            )

        else:

            suggestion = (
                "Maintain a balanced study routine."
            )

    return render_template(
        "ai_assistant.html",
        suggestion=suggestion
    )


# ---------------- ANALYTICS ---------------- #

@app.route("/analytics")
@login_required
def analytics():

    user_id = session["user_id"]

    tasks = db.execute(
        """
        SELECT * FROM tasks
        WHERE user_id = ?
        """,
        user_id
    )

    total_tasks = len(tasks)

    completed_tasks = len(
        [task for task in tasks if task["completed"] == 1]
    )

    return render_template(
        "analytics.html",
        total_tasks=total_tasks,
        completed_tasks=completed_tasks
    )


# ---------------- RUN APP ---------------- #

if __name__ == "__main__":
    app.run(debug=True)