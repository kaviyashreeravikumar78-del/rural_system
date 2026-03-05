from flask import Flask, render_template, redirect, request, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import joblib
import numpy as np
from bson import ObjectId
from pymongo import MongoClient
from google import genai 
from datetime import datetime
from PIL import Image
import uuid
from flask_login import login_required, current_user, LoginManager, UserMixin, login_user

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# ===========================
# USER MODEL
# ===========================
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id']) 
        self.email = user_data.get('email')
        self.name = user_data.get('name')
        self.role = user_data.get('role', 'user')

# ===========================
# MONGODB CONNECTION
# ===========================
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["rural_health_ai"]

users_collection = db["users"]
doctors_collection = db["doctors"]
appointments_collection = db["appointments"]
consultations_collection = db["consultations"]
hospitals_collection = db["hospitals"]

# ===========================
# GENAI CLIENT
# ===========================
genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ===========================
# ML MODEL
# ===========================
model = joblib.load("models/disease_model.pkl")
label_encoder = joblib.load("models/label_encoder.pkl")

# ===========================
# FLASK-LOGIN SETUP
# ===========================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    # Try to find user in users collection
    user_data = users_collection.find_one({"_id": ObjectId(user_id)})
    if user_data:
        user_data['role'] = 'user'
        return User(user_data)
    
    # Try to find in doctors collection
    doctor_data = doctors_collection.find_one({"_id": ObjectId(user_id)})
    if doctor_data:
        doctor_data['role'] = 'doctor'
        return User(doctor_data)
    
    return None

# ===========================
# HOME
# ===========================
@app.route('/')
def home():
    return render_template('home.html')

# ===========================
# SIGNUP (USER & DOCTOR)
# ===========================
@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user_type = request.form.get("user_type")
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        
        if user_type == "user":
            age = request.form.get("age")
            language = request.form.get("language")
            chronic = request.form.get("chronic")

            if users_collection.find_one({"email": email}):
                flash("Email already registered!")
                return redirect(url_for("signup"))

            hashed_password = generate_password_hash(password)

            user_data = {
                "name": name,
                "email": email,
                "password": hashed_password,
                "age": int(age),
                "language": language,
                "chronic_conditions": chronic.split(",") if chronic else [],
                "risk_history": [],
                "symptom_history": [],
                "recovery_trend": [],
                "prescriptions": [],
                "daily_reports": []
            }

            users_collection.insert_one(user_data)
            flash("Signup successful! Please login.")
            return redirect(url_for("login"))
        
        elif user_type == "doctor":
            specialization = request.form.get("specialization")
            experience = request.form.get("experience")
            hospital = request.form.get("hospital")
            location = request.form.get("location")
            fee = request.form.get("fee")
            
            if doctors_collection.find_one({"email": email}):
                flash("Email already registered!")
                return redirect(url_for("signup"))
            
            hashed_password = generate_password_hash(password)
            
            doctor_data = {
                "name": name,
                "email": email,
                "password": hashed_password,
                "specialization": specialization,
                "experience": int(experience),
                "hospital": hospital,
                "location": location,
                "fee": int(fee),
                "available_slots": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM", "4:00 PM"],
                "is_available": True
            }
            
            doctors_collection.insert_one(doctor_data)
            flash("Doctor registration successful! Please login.")
            return redirect(url_for("login"))

    return render_template("signup.html")

# ===========================
# LOGIN (USER & DOCTOR)
# ===========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_type = request.form.get("user_type")
        email = request.form.get("email")
        password = request.form.get("password")

        if user_type == "user":
            user = users_collection.find_one({"email": email})

            if user and check_password_hash(user["password"], password):
                session["user_id"] = str(user["_id"])
                session["user_name"] = user["name"]
                session["language"] = user["language"]
                session["user_type"] = "user"
                
                # Login for Flask-Login
                user_obj = User(user)
                login_user(user_obj)

                flash("Login successful!")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid email or password")
                return redirect(url_for("login"))
        
        elif user_type == "doctor":
            doctor = doctors_collection.find_one({"email": email})
            
            if doctor and check_password_hash(doctor["password"], password):
                session["doctor_id"] = str(doctor["_id"])
                session["doctor_name"] = doctor["name"]
                session["user_type"] = "doctor"
                
                # Login for Flask-Login
                doctor['role'] = 'doctor'
                doctor_obj = User(doctor)
                login_user(doctor_obj)
                
                flash("Doctor login successful!")
                return redirect(url_for("doctor_dashboard"))
            else:
                flash("Invalid email or password")
                return redirect(url_for("login"))

    return render_template("login.html")

# ===========================
# LOGOUT
# ===========================
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully")
    return redirect(url_for("login"))

# ===========================
# DASHBOARD (USER)
# ===========================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session or session.get("user_type") != "user":
        return redirect(url_for("login"))

    return render_template("dashboard.html",
                           name=session.get("user_name"),
                           language=session.get("language"))

# ===========================
# DOCTOR DASHBOARD
# ===========================
@app.route("/doctor-dashboard")
def doctor_dashboard():
    if "doctor_id" not in session or session.get("user_type") != "doctor":
        return redirect(url_for("login"))
    
    # Get pending consultation requests
    pending_requests = list(consultations_collection.find({
        "doctor_id": ObjectId(session["doctor_id"]),
        "status": "Pending"
    }))
    
    # Get accepted consultations
    accepted_consultations = list(consultations_collection.find({
        "doctor_id": ObjectId(session["doctor_id"]),
        "status": "Accepted"
    }))
    
    # Get user details for each consultation
    for consult in pending_requests + accepted_consultations:
        user = users_collection.find_one({"_id": consult["user_id"]})
        consult["user_details"] = user
    
    return render_template("doctor_dashboard.html",
                          name=session.get("doctor_name"),
                          pending_requests=pending_requests,
                          accepted_consultations=accepted_consultations)

# ===========================
# SYMPTOM REPORT
# ===========================
@app.route("/report", methods=["GET", "POST"])
def report():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        selected_symptoms = request.form.getlist("symptoms")

        symptom_list = model.feature_names_in_
        input_data = [1 if symptom in selected_symptoms else 0 for symptom in symptom_list]
        input_array = np.array(input_data).reshape(1, -1)

        prediction = model.predict(input_array)
        probabilities = model.predict_proba(input_array)

        disease = label_encoder.inverse_transform(prediction)[0]
        base_probability = max(probabilities[0]) * 100

        user = users_collection.find_one({"_id": ObjectId(session["user_id"])})

        age = user.get("age", 25)
        chronic_conditions = user.get("chronic_conditions", [])

        risk_score = base_probability

        if age > 60:
            risk_score += 15
        elif age < 12:
            risk_score += 10

        if len(chronic_conditions) > 0:
            risk_score += 20

        risk_score = min(risk_score, 100)

        if risk_score < 40:
            risk_level = "Low"
        elif risk_score < 75:
            risk_level = "Moderate"
        else:
            risk_level = "High"

        ai_recommendation = generate_ai_recommendation(
            user=user,
            disease=disease,
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            selected_symptoms=selected_symptoms
        )

        users_collection.update_one(
            {"_id": ObjectId(session["user_id"])},
            {
                "$push": {
                    "risk_history": {
                        "disease": disease,
                        "risk_score": risk_score
                    },
                    "symptom_history": selected_symptoms,
                    "ai_recommendations": {
                        "disease": disease,
                        "recommendation": ai_recommendation
                    }
                }
            }
        )

        return render_template("result.html",
                       disease=disease,
                       risk_score=round(risk_score, 2),
                       risk_level=risk_level,
                       ai_recommendation=ai_recommendation)

    return render_template("report.html", symptoms=model.feature_names_in_)

# ===========================
# DOCTORS LIST (For Consultation)
# ===========================
@app.route("/doctors")
def doctors():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Get only available doctors
    doctors = list(doctors_collection.find({"is_available": True}))
    
    # Vary availability randomly for different users
    import random
    for doctor in doctors:
        doctor["is_available_now"] = random.choice([True, True, True, False])
    
    return render_template("doctors.html", doctors=doctors)

# ===========================
# REQUEST CONSULTATION
# ===========================
@app.route("/request-consultation/<doctor_id>", methods=["POST"])
def request_consultation(doctor_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    message = request.form.get("message")
    
    doctor = doctors_collection.find_one({"_id": ObjectId(doctor_id)})
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    
    consultation_data = {
        "user_id": ObjectId(session["user_id"]),
        "user_name": user["name"],
        "user_email": user["email"],
        "user_age": user["age"],
        "user_chronic": user.get("chronic_conditions", []),
        "doctor_id": ObjectId(doctor_id),
        "doctor_name": doctor["name"],
        "message": message,
        "status": "Pending",
        "requested_at": datetime.now(),
        "chat_messages": []
    }
    
    consultations_collection.insert_one(consultation_data)
    flash("Consultation request sent successfully!")
    return redirect(url_for("my_consultations"))

# ===========================
# MY CONSULTATIONS (USER)
# ===========================
@app.route("/my-consultations")
def my_consultations():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    consultations = list(consultations_collection.find({
        "user_id": ObjectId(session["user_id"])
    }))
    
    return render_template("my_consultations.html", consultations=consultations)

# ===========================
# ACCEPT/REJECT CONSULTATION (DOCTOR)
# ===========================
@app.route("/respond-consultation/<consultation_id>/<action>")
def respond_consultation(consultation_id, action):
    if "doctor_id" not in session:
        return redirect(url_for("login"))
    
    if action == "accept":
        consultations_collection.update_one(
            {"_id": ObjectId(consultation_id)},
            {"$set": {"status": "Accepted", "accepted_at": datetime.now()}}
        )
        flash("Consultation accepted!")
    elif action == "reject":
        consultations_collection.update_one(
            {"_id": ObjectId(consultation_id)},
            {"$set": {"status": "Rejected", "rejected_at": datetime.now()}}
        )
        flash("Consultation rejected!")
    
    return redirect(url_for("doctor_dashboard"))

# ===========================
# VIDEO CONSULTATION
# ===========================
@app.route('/video-consultation/<consultation_id>')
@login_required
def video_consultation(consultation_id):
    """
    Start a video consultation session
    """
    # Fetch consultation to ensure it exists and user has access
    consult = consultations_collection.find_one({"_id": ObjectId(consultation_id)})
    
    if not consult:
        flash("Consultation not found.")
        if session.get("user_type") == "user":
            return redirect(url_for('my_consultations'))
        else:
            return redirect(url_for('doctor_dashboard'))
    
    # Check if consultation is accepted
    if consult.get("status") != "Accepted":
        flash("This consultation has not been accepted yet.")
        if session.get("user_type") == "user":
            return redirect(url_for('my_consultations'))
        else:
            return redirect(url_for('doctor_dashboard'))
    
    # Verify user has access to this consultation
    user_type = session.get("user_type")
    if user_type == "user":
        if str(consult["user_id"]) != session.get("user_id"):
            flash("Unauthorized access")
            return redirect(url_for("my_consultations"))
    elif user_type == "doctor":
        if str(consult["doctor_id"]) != session.get("doctor_id"):
            flash("Unauthorized access")
            return redirect(url_for("doctor_dashboard"))
    
    # Use the consultation ID as the room name so both parties join the same call
    room_name = f"RuralCare-{consultation_id}"
    display_name = current_user.name
    
    return render_template('video_call.html', 
                           room_name=room_name, 
                           display_name=display_name,
                           consultation_id=consultation_id,
                           user_type=user_type)

# ===========================
# END VIDEO CONSULTATION
# ===========================
@app.route('/end-video-consultation/<consultation_id>', methods=["POST"])
@login_required
def end_video_consultation(consultation_id):
    """
    Mark consultation as completed after video call
    """
    consult = consultations_collection.find_one({"_id": ObjectId(consultation_id)})
    
    if not consult:
        return jsonify({"success": False, "message": "Consultation not found"}), 404
    
    # Update consultation status
    consultations_collection.update_one(
        {"_id": ObjectId(consultation_id)},
        {"$set": {
            "status": "Completed",
            "completed_at": datetime.now()
        }}
    )
    
    return jsonify({"success": True, "message": "Consultation marked as completed"})

# ===========================
# CHAT WITH DOCTOR/USER
# ===========================
@app.route("/chat/<consultation_id>", methods=["GET", "POST"])
def chat(consultation_id):
    consultation = consultations_collection.find_one({"_id": ObjectId(consultation_id)})
    
    if not consultation:
        flash("Consultation not found")
        return redirect(url_for("dashboard"))
    
    # Check authorization
    if session.get("user_type") == "user":
        if str(consultation["user_id"]) != session.get("user_id"):
            flash("Unauthorized access")
            return redirect(url_for("dashboard"))
    elif session.get("user_type") == "doctor":
        if str(consultation["doctor_id"]) != session.get("doctor_id"):
            flash("Unauthorized access")
            return redirect(url_for("doctor_dashboard"))
    
    if request.method == "POST":
        message = request.form.get("message")
        sender_type = session.get("user_type")
        sender_name = session.get("user_name") if sender_type == "user" else session.get("doctor_name")
        
        chat_message = {
            "sender": sender_name,
            "sender_type": sender_type,
            "message": message,
            "timestamp": datetime.now()
        }
        
        consultations_collection.update_one(
            {"_id": ObjectId(consultation_id)},
            {"$push": {"chat_messages": chat_message}}
        )
        
        return redirect(url_for("chat", consultation_id=consultation_id))
    
    # Get updated consultation with messages
    consultation = consultations_collection.find_one({"_id": ObjectId(consultation_id)})
    
    return render_template("chat.html", consultation=consultation)

# ===========================
# FIND HOSPITAL MAP
# ===========================
@app.route("/find-hospital")
def find_hospital():
    return render_template("map.html")

# ===========================
# GET HOSPITALS (API for map)
# ===========================
@app.route("/api/hospitals")
def get_hospitals():
    hospitals = list(hospitals_collection.find())
    
    # Convert ObjectId to string
    for hospital in hospitals:
        hospital["_id"] = str(hospital["_id"])
    
    return jsonify(hospitals)

# ===========================
# BOOK HOSPITAL APPOINTMENT
# ===========================
@app.route("/book-hospital/<hospital_id>", methods=["GET", "POST"])
def book_hospital_appointment(hospital_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    hospital = hospitals_collection.find_one({"_id": ObjectId(hospital_id)})
    
    if not hospital:
        flash("Hospital not found!")
        return redirect(url_for("find_hospital"))

    if request.method == "POST":
        date = request.form.get("date")
        time = request.form.get("time")
        department = request.form.get("department")
        reason = request.form.get("reason")

        # Prevent double booking
        existing = appointments_collection.find_one({
            "hospital_id": ObjectId(hospital_id),
            "date": date,
            "time": time,
            "status": "Booked"
        })

        if existing:
            flash("Slot already booked! Choose another time.")
            return redirect(url_for("book_hospital_appointment", hospital_id=hospital_id))

        appointments_collection.insert_one({
            "user_id": ObjectId(session["user_id"]),
            "hospital_id": ObjectId(hospital_id),
            "hospital_name": hospital["name"],
            "hospital_contact": hospital["contact"],
            "hospital_address": hospital["address"],
            "department": department,
            "reason": reason,
            "date": date,
            "time": time,
            "status": "Booked",
            "booked_at": datetime.now(),
            "appointment_type": "hospital"
        })

        flash("Hospital Appointment Booked Successfully!")
        return redirect(url_for("my_appointments"))

    return render_template("book_hospital.html", hospital=hospital, now=datetime.now())

# ===========================
# VIEW MY APPOINTMENTS
# ===========================
@app.route("/my-appointments")
def my_appointments():
    if "user_id" not in session:
        return redirect(url_for("login"))

    appointments = list(appointments_collection.find({
        "user_id": ObjectId(session["user_id"])
    }))

    return render_template("my_appointments.html", appointments=appointments)

# ===========================
# CANCEL APPOINTMENT
# ===========================
@app.route("/cancel/<appointment_id>")
def cancel_appointment(appointment_id):
    appointments_collection.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {"status": "Cancelled"}}
    )

    flash("Appointment Cancelled")
    return redirect(url_for("my_appointments"))

# ===========================
# DOCTOR - ADD PRESCRIPTION
# ===========================
@app.route("/add-prescription/<consultation_id>", methods=["GET", "POST"])
def add_prescription(consultation_id):
    if "doctor_id" not in session or session.get("user_type") != "doctor":
        return redirect(url_for("login"))
    
    consultation = consultations_collection.find_one({"_id": ObjectId(consultation_id)})
    
    if not consultation:
        flash("Consultation not found")
        return redirect(url_for("doctor_dashboard"))
    
    if request.method == "POST":
        diagnosis = request.form.get("diagnosis")
        medications = request.form.getlist("medication_name[]")
        dosages = request.form.getlist("dosage[]")
        frequencies = request.form.getlist("frequency[]")
        durations = request.form.getlist("duration[]")
        
        exercises = request.form.getlist("exercise_name[]")
        exercise_durations = request.form.getlist("exercise_duration[]")
        exercise_frequencies = request.form.getlist("exercise_frequency[]")
        
        diet_instructions = request.form.get("diet_instructions")
        precautions = request.form.get("precautions")
        follow_up_days = request.form.get("follow_up_days")
        
        # Build medications list
        medications_list = []
        for i in range(len(medications)):
            if medications[i]:
                medications_list.append({
                    "name": medications[i],
                    "dosage": dosages[i],
                    "frequency": frequencies[i],
                    "duration": durations[i]
                })
        
        # Build exercises list
        exercises_list = []
        for i in range(len(exercises)):
            if exercises[i]:
                exercises_list.append({
                    "name": exercises[i],
                    "duration": exercise_durations[i],
                    "frequency": exercise_frequencies[i]
                })
        
        prescription_data = {
            "diagnosis": diagnosis,
            "medications": medications_list,
            "exercises": exercises_list,
            "diet_instructions": diet_instructions,
            "precautions": precautions,
            "follow_up_days": int(follow_up_days) if follow_up_days else 7,
            "prescribed_date": datetime.now(),
            "doctor_name": session.get("doctor_name")
        }
        
        # Update consultation with prescription
        consultations_collection.update_one(
            {"_id": ObjectId(consultation_id)},
            {"$set": {"prescription": prescription_data}}
        )
        
        # Add prescription to user's profile
        users_collection.update_one(
            {"_id": consultation["user_id"]},
            {
                "$push": {
                    "prescriptions": {
                        "consultation_id": ObjectId(consultation_id),
                        "diagnosis": diagnosis,
                        "doctor_name": session.get("doctor_name"),
                        "date": datetime.now(),
                        "medications": medications_list,
                        "exercises": exercises_list,
                        "diet_instructions": diet_instructions
                    }
                }
            }
        )
        
        flash("Prescription added successfully!")
        return redirect(url_for("doctor_dashboard"))
    
    user = users_collection.find_one({"_id": consultation["user_id"]})
    
    return render_template("add_prescription.html", consultation=consultation, user=user)

# ===========================
# USER - VIEW PRESCRIPTION
# ===========================
@app.route("/view-prescription/<consultation_id>")
def view_prescription(consultation_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    consultation = consultations_collection.find_one({"_id": ObjectId(consultation_id)})
    
    if not consultation or str(consultation["user_id"]) != session["user_id"]:
        flash("Prescription not found")
        return redirect(url_for("my_consultations"))
    
    return render_template("view_prescription.html", consultation=consultation)

# ===========================
# USER - DAILY HEALTH REPORT
# ===========================
@app.route("/daily-report", methods=["GET", "POST"])
def daily_report():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    
    if request.method == "POST":
        report_date = request.form.get("report_date")
        medications_taken = request.form.getlist("medications_taken")
        exercises_done = request.form.getlist("exercises_done")
        symptoms = request.form.get("symptoms")
        pain_level = request.form.get("pain_level")
        mood = request.form.get("mood")
        water_intake = request.form.get("water_intake")
        sleep_hours = request.form.get("sleep_hours")
        notes = request.form.get("notes")
        
        report_data = {
            "date": datetime.strptime(report_date, "%Y-%m-%d"),
            "medications_taken": medications_taken,
            "exercises_done": exercises_done,
            "symptoms": symptoms,
            "pain_level": int(pain_level) if pain_level else 0,
            "mood": mood,
            "water_intake": int(water_intake) if water_intake else 0,
            "sleep_hours": float(sleep_hours) if sleep_hours else 0,
            "notes": notes,
            "submitted_at": datetime.now()
        }
        
        users_collection.update_one(
            {"_id": ObjectId(session["user_id"])},
            {"$push": {"daily_reports": report_data}}
        )
        
        flash("Daily report submitted successfully!")
        return redirect(url_for("daily_report"))
    
    # GET request logic
    prescriptions = user.get("prescriptions", [])
    daily_reports = user.get("daily_reports", [])
    
    # Check if a report was already submitted today
    today_dt = datetime.now().date()
    today_report = next((r for r in daily_reports if r["date"].date() == today_dt), None)
    
    # Prepare date strings for template
    current_date_val = datetime.now().strftime('%Y-%m-%d')
    display_date = datetime.now().strftime('%B %d, %Y')
    
    return render_template("daily_report.html", 
                          user=user, 
                          prescriptions=prescriptions,
                          daily_reports=daily_reports,
                          today_report=today_report,
                          current_date_val=current_date_val,
                          display_date=display_date)

# ===========================
# USER - DAILY REMINDERS & NOTIFICATIONS
# ===========================
@app.route("/my-reminders")
def my_reminders():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    
    prescriptions = user.get("prescriptions", [])
    daily_reports = user.get("daily_reports", [])
    
    # Get today's completed tasks
    today = datetime.now().date()
    today_report = None
    for report in daily_reports:
        report_date = report["date"]
        if isinstance(report_date, datetime):
            if report_date.date() == today:
                today_report = report
                break
    
    # Prepare date strings for template
    display_date = datetime.now().strftime("%B %d, %Y")
    input_date = datetime.now().strftime("%Y-%m-%d")
    
    return render_template("my_reminders.html", 
                          user=user,
                          prescriptions=prescriptions,
                          daily_reports=daily_reports,
                          today_report=today_report,
                          display_date=display_date,
                          input_date=input_date)

# ===========================
# DOCTOR - VIEW PATIENT REPORTS
# ===========================
@app.route("/view-patient-reports/<user_id>")
def view_patient_reports(user_id):
    if "doctor_id" not in session or session.get("user_type") != "doctor":
        return redirect(url_for("login"))
    
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        flash("Patient not found")
        return redirect(url_for("doctor_dashboard"))
    
    daily_reports = user.get("daily_reports", [])
    prescriptions = user.get("prescriptions", [])
    
    # Sort reports by date (newest first)
    daily_reports = sorted(daily_reports, key=lambda x: x["date"], reverse=True)
    
    return render_template("view_patient_reports.html", 
                          user=user,
                          daily_reports=daily_reports,
                          prescriptions=prescriptions)

# ===========================
# FIRST AID
# ===========================
@app.route("/first_aid")
def first_aid():
    return render_template("first_aid.html")

@app.route("/analyze_first_aid", methods=["POST"])
def analyze_first_aid():
    image_file = request.files["image"]
    image = Image.open(image_file)
    result = generate_first_aid(image)
    return render_template("first_aid_result.html", result=result)

# ===========================
# SEED DOCTORS
# ===========================
@app.route("/seed-doctors")
def seed_doctors():
    if doctors_collection.count_documents({}) > 0:
        return "Doctors already seeded!"

    doctors_collection.insert_many([
        {
            "name": "Dr. Priya Sharma",
            "email": "priya@hospital.com",
            "password": generate_password_hash("doctor123"),
            "specialization": "Cardiologist",
            "experience": 8,
            "fee": 500,
            "hospital": "Chennai Heart Clinic",
            "location": "Chennai",
            "available_slots": ["10:00 AM", "11:00 AM", "2:00 PM"],
            "is_available": True
        },
        {
            "name": "Dr. Arun Kumar",
            "email": "arun@hospital.com",
            "password": generate_password_hash("doctor123"),
            "specialization": "General Physician",
            "experience": 5,
            "fee": 300,
            "hospital": "City Care Hospital",
            "location": "Chennai",
            "available_slots": ["9:00 AM", "1:00 PM", "4:00 PM"],
            "is_available": True
        },
        {
            "name": "Dr. Meena Patel",
            "email": "meena@hospital.com",
            "password": generate_password_hash("doctor123"),
            "specialization": "Dermatologist",
            "experience": 6,
            "fee": 400,
            "hospital": "Skin Wellness Center",
            "location": "Bangalore",
            "available_slots": ["10:30 AM", "3:00 PM"],
            "is_available": True
        },
        {
            "name": "Dr. Rajesh Singh",
            "email": "rajesh@hospital.com",
            "password": generate_password_hash("doctor123"),
            "specialization": "Neurologist",
            "experience": 12,
            "fee": 800,
            "hospital": "Neuro Care Institute",
            "location": "Hyderabad",
            "available_slots": ["11:00 AM", "1:30 PM"],
            "is_available": True
        }
    ])

    return "Doctors seeded successfully! Login credentials: email: priya@hospital.com, password: doctor123"

# ===========================
# SEED HOSPITALS
# ===========================
@app.route("/seed-hospitals")
def seed_hospitals():
    if hospitals_collection.count_documents({}) > 0:
        return "Hospitals already seeded!"
    
    hospitals_collection.insert_many([
        {
            "name": "Apollo Hospital",
            "type": "Multi-specialty",
            "contact": "+91-44-28293333",
            "latitude": 13.0569,
            "longitude": 80.2425,
            "address": "Greams Road, Chennai",
            "city": "Chennai"
        },
        {
            "name": "Government General Hospital",
            "type": "Government",
            "contact": "+91-44-25305000",
            "latitude": 13.0878,
            "longitude": 80.2785,
            "address": "Park Town, Chennai",
            "city": "Chennai"
        },
        {
            "name": "MIOT International",
            "type": "Multi-specialty",
            "contact": "+91-44-42002000",
            "latitude": 13.0338,
            "longitude": 80.2316,
            "address": "Manapakkam, Chennai",
            "city": "Chennai"
        },
        {
            "name": "Fortis Malar Hospital",
            "type": "Private",
            "contact": "+91-44-42892222",
            "latitude": 13.0604,
            "longitude": 80.2548,
            "address": "Adyar, Chennai",
            "city": "Chennai"
        },
        {
            "name": "Primary Health Centre",
            "type": "Government",
            "contact": "+91-44-27471234",
            "latitude": 13.1200,
            "longitude": 80.2900,
            "address": "Tiruvottiyur, Chennai",
            "city": "Chennai"
        },
        {
            "name": "Kauvery Hospital",
            "type": "Private",
            "contact": "+91-44-40004000",
            "latitude": 13.0475,
            "longitude": 80.2379,
            "address": "Alwarpet, Chennai",
            "city": "Chennai"
        },
        {
            "name": "Global Hospital",
            "type": "Multi-specialty",
            "contact": "+91-44-44777000",
            "latitude": 13.0067,
            "longitude": 80.2206,
            "address": "Perumbakkam, Chennai",
            "city": "Chennai"
        },
        {
            "name": "Community Health Centre",
            "type": "Government",
            "contact": "+91-44-26531000",
            "latitude": 13.1500,
            "longitude": 80.2000,
            "address": "Ponneri, Chennai",
            "city": "Chennai"
        }
    ])
    
    return "Hospitals seeded successfully!"

# ===========================
# HELPER FUNCTIONS
# ===========================
def generate_ai_recommendation(user, disease, risk_score, risk_level, selected_symptoms):
    prompt = f"""
You are a professional medical assistant AI.

Your role is to provide SAFE, BASIC health guidance based on the user's health profile and current symptoms.

-----------------------------------
USER PROFILE
-----------------------------------
- Age: {user.get('age')}
- Chronic Conditions: {user.get('chronic_conditions')}
- Past Risk History: {user.get('risk_history')}
- Past Symptoms History: {user.get('symptom_history')}

-----------------------------------
CURRENT HEALTH ANALYSIS
-----------------------------------
- Predicted Disease: {disease}
- Risk Score: {risk_score}%
- Risk Level: {risk_level}
- Current Symptoms: {selected_symptoms}

-----------------------------------
INSTRUCTIONS
-----------------------------------
Based on the information above, generate personalized health guidance.

Follow these rules:
- Use simple language
- Provide only safe and general medical advice
- Do NOT make strong medical claims
- Do NOT diagnose definitively
- Encourage consulting a doctor when necessary

-----------------------------------
RESPONSE FORMAT (IMPORTANT)
-----------------------------------

Return the response in this structured format:

1. Personalized Recommendations
- Point 1
- Point 2
- Point 3

2. Preventive Steps
- Point 1
- Point 2
- Point 3

3. Lifestyle Advice
- Point 1
- Point 2
- Point 3

4. Medical Attention Guidance
- Explain if the user should:
  * Monitor symptoms
  * Visit a doctor soon
  * Seek urgent care

Keep the response short, clear, and practical.
"""

    response = genai_client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt
    )

    return response.text

def generate_first_aid(image):
    prompt = """
You are a medical first aid assistant.

Analyze the injury shown in the image.

Provide:

1. Injury Type (Possible)
2. First Aid Steps
3. Things to Avoid
4. When to See a Doctor

Rules:
- Only basic first aid
- No complex medical diagnosis
- Keep instructions simple
"""

    genai_client_alt = genai.Client(api_key=os.getenv("GENAI_API_KEY"))
    
    response = genai_client_alt.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[prompt, image]
    )

    return response.text

# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run(debug=True)