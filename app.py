from flask import Flask, render_template, request, redirect, session, flash
from flask_session import Session
from cs50 import SQL
from werkzeug.security import generate_password_hash, check_password_hash

from helpers import apology, login_required

# NEW LANGCHAIN HUGGINGFACE IMPORTS
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

app = Flask(__name__)

# Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Configure database
db = SQL("sqlite:///skillsync.db")

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


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

# ---------------- AI STUDY ASSISTANT (HUGGING FACE INTERACTION) ---------------- #
@app.route("/ai_assistant", methods=["GET", "POST"])
@login_required
def ai_assistant():
    suggestion = None
    if request.method == "POST":
        subject = request.form.get("subject")
        hours = request.form.get("hours")
        difficulty = request.form.get("difficulty")

        if not subject or not hours or not difficulty:
            return apology("All input fields are required.")

        hf_token = os.environ.get("HUGGINGFACE_API_TOKEN")

        if hf_token:
            try:
                # 1. Initialize the Hugging Face Endpoint via LangChain
                # We use Llama-3-8B-Instruct as it understands complex system prompts perfectly
                repo_id = "deepseek-ai/DeepSeek-V3.2"
                
                llm = HuggingFaceEndpoint(
                    repo_id=repo_id,
                    huggingfacehub_api_token=hf_token,
                    max_new_tokens=700,
                    temperature=0.6,
                    top_p=0.9
                )
                
                # 2. Define the Complete, Descriptive System Prompt Template
                # We use Llama-3 specific special tokens (<|begin_of_text|>, etc.) so the model follows the structure perfectly
                template = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are 'SkillSync AI', an elite, deeply empathetic, humble, and highly technical student productivity coach. 
Your primary goal is to empower students by constructing actionable, optimized, and masterclass-grade study plans. 
Maintain a professional yet encouraging and humble tone. Address the student directly.

Structure your output cleanly using the following exact markdown layout:
### 🌟 Strategic Mindset
[Provide an empathetic, encouraging sentence recognizing the difficulty, followed by a tactical mental model like Spaced Repetition or Feynman Technique tailored to this specific subject]

### 📅 Masterclass Roadmap & Time Allocation
[Provide a hyper-specific breakdown showing exactly how to spend their hours per day logically split between theory, application, and debugging/revision]

### 🛠️ Step-by-Step Technical Execution Steps
[Deliver a specific 3-step blueprint detailing precisely what milestones to focus on first to unlock maximum comprehension without burning out]<|eot_id|><|start_header_id|>user<|end_header_id|>

I am a student working on '{subject}'. I have rated its current difficulty level as '{difficulty}' for myself, and I can commit exactly '{hours}' hours per day to mastering it. Please map out my personalized engineering roadmap strategy.<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

                prompt = PromptTemplate.from_template(template)
                
                # 3. Construct the LangChain Expression Language (LCEL) Chain
                chain = prompt | llm | StrOutputParser()
                
                # 4. Invoke the chain with user inputs
                suggestion = chain.invoke({
                    "subject": subject,
                    "difficulty": difficulty,
                    "hours": hours
                })
                    
            except Exception as e:
                # ROBUST RESILIENT FALLBACK: Triggers if Hugging Face goes down or rate-limits
                suggestion = (
                    "### 🌟 Strategic Mindset\n"
                    f"Mastering **{subject}** requires strategic patience. Even when material feels challenging, remember that engineering expertise is built block-by-block through consistent application.\n\n"
                    "### 📅 Masterclass Roadmap & Time Allocation\n"
                    f"Given your commitment of **{hours} hours/day**, map out your allocation into a strict 50/30/20 configuration:\n"
                    f"* **Theory & Documentation:** {float(hours)*0.5:.1f} Hours focusing on fundamental concepts.\n"
                    f"* **Active Code/Implementation:** {float(hours)*0.3:.1f} Hours wrestling directly with projects.\n"
                    f"* **Review & Error Diagnostics:** {float(hours)*0.2:.1f} Hours refactoring code and cleaning notes.\n\n"
                    "### 🛠️ Step-by-Step Technical Execution Steps\n"
                    "1. **Isolate the Core Architecture:** Break down large tasks into atomic operations. Write clear documentation alongside your implementation tracking.\n"
                    "2. **Implement Pomodoro Routines:** Work in focused 25-minute sprints with short diagnostic breaks to keep cognitive fatigue low.\n"
                    "3. **Log Progress Safely:** Keep clear error catalogs in your notes tab to reference whenever a systemic barrier patterns itself again."
                )
        else:
            suggestion = f"### System Notice\nHugging Face API Token missing. Please check your configuration parameters."

    return render_template("ai_assistant.html", suggestion=suggestion)


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