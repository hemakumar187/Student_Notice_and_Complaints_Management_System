from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- MONGODB CONNECTION ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["notice_system"]

students = db["students"]
admins = db["admins"]
notices = db["notices"]
complaints = db["complaints"]
feedbacks = db["feedbacks"]

# ---------------- DEFAULT ADMIN ----------------
if admins.count_documents({"email": "admin@gmail.com"}) == 0:
    admins.insert_one({
        "email": "admin@gmail.com",
        "password": generate_password_hash("admin123")
    })

# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    return render_template("home.html")  # Make sure home.html exists

# ---------------- STUDENT REGISTER ----------------
@app.route("/student_register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            return "Please fill all fields"

        # check if email already exists
        if students.find_one({"email": email}):
            return "Email already registered"

        students.insert_one({
            "name": name,
            "email": email,
            "password": generate_password_hash(password)
        })
        return redirect("/student_login")
    return render_template("student_register.html")

# ---------------- STUDENT LOGIN ----------------
@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            return "Please enter both email and password"

        student = students.find_one({"email": email})
        if student and check_password_hash(student["password"], password):
            session["student"] = email
            return redirect("/student_dashboard")
        else:
            return "Invalid Student Login"
    return render_template("student_login.html")

# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student_dashboard")
def student_dashboard():
    if "student" not in session:
        return redirect("/student_login")

    # fetch notices sorted by date descending
    all_notices = list(notices.find().sort("date", -1))
    for n in all_notices:
        if isinstance(n.get("date"), datetime):
            n["date_str"] = n["date"].strftime("%Y-%m-%d %H:%M")
        else:
            n["date_str"] = str(n.get("date"))
    return render_template("student_dashboard.html", notices=all_notices)

# ---------------- STUDENT COMPLAINT ----------------
@app.route("/student_complaint", methods=["GET", "POST"])
def student_complaint():
    if "student" not in session:
        return redirect("/student_login")
    if request.method == "POST":
        message = request.form.get("message")
        if not message:
            return "Please enter a message"
        complaints.insert_one({
            "email": session["student"],
            "message": message,
            "status": "Pending",
            "date": datetime.now()
        })
        return redirect("/student_dashboard")
    return render_template("student_complaint.html")

# ---------------- STUDENT FEEDBACK ----------------
@app.route("/student_feedback", methods=["GET", "POST"])
def student_feedback():
    if "student" not in session:
        return redirect("/student_login")
    if request.method == "POST":
        message = request.form.get("message")
        if not message:
            return "Please enter a message"
        feedbacks.insert_one({
            "student_email": session["student"],
            "message": message,
            "date": datetime.now()
        })
        return redirect("/student_dashboard")
    return render_template("student_feedback.html")

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            return "Please enter both email and password"

        admin = admins.find_one({"email": email})
        if admin and check_password_hash(admin["password"], password):
            session["admin"] = email
            return redirect("/admin_dashboard")
        else:
            return "Invalid Admin Login"
    return render_template("admin_login.html")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/admin_login")
    return render_template("admin_dashboard.html")

# ---------------- ADD NOTICE ----------------
@app.route("/add_notice", methods=["GET", "POST"])
def add_notice():
    if "admin" not in session:
        return redirect("/admin_login")
    if request.method == "POST":
        title = request.form.get("title")
        message = request.form.get("message")
        if not title or not message:
            return "Please enter both title and message"
        notices.insert_one({
            "title": title,
            "message": message,
            "date": datetime.now()
        })
        return redirect("/admin_dashboard")
    return render_template("add_notice.html")

# ---------------- VIEW ALL NOTICES (ADMIN) ----------------
@app.route("/view_notices_admin")
def view_notices_admin():
    if "admin" not in session:
        return redirect("/admin_login")
    all_notices = list(notices.find().sort("date", -1))
    for n in all_notices:
        if isinstance(n.get("date"), datetime):
            n["date_str"] = n["date"].strftime("%Y-%m-%d %H:%M")
        else:
            n["date_str"] = str(n.get("date"))
    return render_template("view_notices_admin.html", notices=all_notices)

# ---------------- DELETE NOTICE ----------------
@app.route("/delete_notice/<notice_id>")
def delete_notice(notice_id):
    if "admin" not in session:
        return redirect("/admin_login")
    notices.delete_one({"_id": ObjectId(notice_id)})
    return redirect("/view_notices_admin")

# ---------------- DELETE ALL NOTICES ----------------
@app.route("/delete_all_notices")
def delete_all_notices():
    if "admin" not in session:
        return redirect("/admin_login")
    notices.delete_many({})
    return redirect("/view_notices_admin")

# ---------------- VIEW COMPLAINTS ----------------
@app.route("/view_complaints")
def view_complaints():
    if "admin" not in session:
        return redirect("/admin_login")
    all_c = list(complaints.find().sort("date", -1))
    for c in all_c:
        if isinstance(c.get("date"), datetime):
            c["date_str"] = c["date"].strftime("%Y-%m-%d %H:%M")
        else:
            c["date_str"] = str(c.get("date"))
    return render_template("view_complaints.html", complaints=all_c)

# ---------------- UPDATE COMPLAINT STATUS ----------------
@app.route("/update_complaint/<complaint_id>")
def update_complaint(complaint_id):
    if "admin" not in session:
        return redirect("/admin_login")
    complaints.update_one(
        {"_id": ObjectId(complaint_id)},
        {"$set": {"status": "Resolved"}}
    )
    return redirect("/view_complaints")

# ---------------- VIEW FEEDBACK ----------------
@app.route("/view_feedback")
def view_feedback():
    if "admin" not in session:
        return redirect("/admin_login")
    all_f = list(feedbacks.find().sort("date", -1))
    for f in all_f:
        if isinstance(f.get("date"), datetime):
            f["date_str"] = f["date"].strftime("%Y-%m-%d %H:%M")
        else:
            f["date_str"] = str(f.get("date"))
    return render_template("view_feedback.html", feedbacks=all_f)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
