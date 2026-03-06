# Rural Health AI Platform

A comprehensive Flask-based healthcare application designed to bridge the gap between patients and healthcare professionals in rural areas. The platform leverages AI-powered diagnostics, appointment management, and telemedicine capabilities to provide accessible healthcare solutions.

## 🎯 Features

### User Features
- **User Authentication**: Secure signup and login system with password hashing
- **Health Profile Management**: Track age, language preferences, and chronic conditions
- **AI-Powered Disease Prediction**: Machine learning model to predict potential diseases based on symptoms
- **Symptom Analysis**: Log and track symptoms with personalized health recommendations
- **Doctor Consultations**: Browse and book appointments with verified healthcare professionals
- **Recovery Tracking**: Monitor health trends and recovery progress over time
- **Daily Health Reports**: Record daily health status and observations
- **Prescription Management**: Store and access prescription records
- **First Aid Assistant**: Upload injury images for AI-powered first aid guidance
- **Risk Assessment**: Get personalized risk scores and health alerts

### Doctor Features
- **Doctor Registration & Profile**: Register with specialization, experience, and hospital details
- **Appointment Management**: Manage availability and accept/decline consultation requests
- **Patient Consultations**: View and manage pending and accepted consultations
- **Patient History Access**: View patient health profiles and consultation history
- **Prescription Management**: Create and issue digital prescriptions
- **Real-time Notifications**: Receive alerts for consultation requests

### Administrator Features
- **Database Seeding**: Seed sample doctors and hospitals for testing
- **Multi-role Support**: Manage both user and doctor accounts
- **Location-based Healthcare**: Hospital finder with map integration

## 🛠️ Tech Stack

**Backend:**
- Flask - Web framework
- MongoDB - NoSQL database
- Flask-Login - User authentication management
- Werkzeug - Password hashing and security

**Machine Learning & AI:**
- Scikit-learn/Joblib - ML model serialization and prediction
- Google Gemini API - AI-powered health recommendations and first aid guidance
- PIL (Pillow) - Image processing for injury analysis

**Frontend:**
- HTML/CSS - UI rendering
- Flask Templates - Dynamic content rendering

**Database:**
- MongoDB - Collections for users, doctors, appointments, consultations, hospitals

## 📋 Prerequisites

- Python 3.8+
- MongoDB database (local or cloud instance)
- Google Gemini API key
- Flask and dependencies

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rural-health-ai
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```
   SECRET_KEY=your_secret_key_here
   MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   GEMINI_API_KEY=your_gemini_api_key
   GENAI_API_KEY=your_genai_api_key
   ```

5. **Prepare ML Models**
   Ensure these files exist in the `models/` directory:
   - `disease_model.pkl` - Trained disease prediction model
   - `label_encoder.pkl` - Label encoder for disease names

6. **Run the application**
   ```bash
   python app.py
   ```

   The application will be available at `http://localhost:5000`

## 📁 Project Structure

```
rural-health-ai/
├── app.py                          # Main Flask application
├── models/
│   ├── disease_model.pkl           # ML model for disease prediction
│   └── label_encoder.pkl           # Label encoder for predictions
├── templates/                      # HTML templates
│   ├── home.html
│   ├── signup.html
│   ├── login.html
│   ├── dashboard.html
│   ├── doctor_dashboard.html
│   └── ...
├── static/                         # Static assets (CSS, JS, images)
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (not in repo)
└── README.md                      # Project documentation
```

## 🗄️ Database Schema

### Users Collection
```json
{
  "_id": ObjectId,
  "name": String,
  "email": String,
  "password": String (hashed),
  "age": Integer,
  "language": String,
  "chronic_conditions": [String],
  "risk_history": [Object],
  "symptom_history": [Object],
  "recovery_trend": [Object],
  "prescriptions": [Object],
  "daily_reports": [Object]
}
```

### Doctors Collection
```json
{
  "_id": ObjectId,
  "name": String,
  "email": String,
  "password": String (hashed),
  "specialization": String,
  "experience": Integer,
  "hospital": String,
  "location": String,
  "fee": Integer,
  "available_slots": [String],
  "is_available": Boolean
}
```

### Appointments Collection
```json
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "doctor_id": ObjectId,
  "date": String,
  "time": String,
  "status": String (Pending/Confirmed/Completed),
  "notes": String
}
```

### Consultations Collection
```json
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "doctor_id": ObjectId,
  "status": String (Pending/Accepted/Completed),
  "consultation_date": DateTime,
  "prescription": String,
  "notes": String
}
```

## 🔐 Authentication & Security

- **Password Security**: All passwords are hashed using Werkzeug's `generate_password_hash()`
- **Session Management**: Flask sessions track user and doctor logins
- **Login Protection**: Routes are protected with `@login_required` decorator
- **User Types**: Separate collections and authentication flows for users and doctors

## 🤖 AI Features

### Disease Prediction
The application uses a trained ML model to predict potential diseases based on:
- Selected symptoms
- User age and health profile
- Chronic conditions history
- Past symptom patterns

### AI-Powered Recommendations
Google Gemini API generates personalized health guidance including:
- Customized health recommendations
- Preventive measures
- Lifestyle advice
- Medical attention guidance

### First Aid Assistant
Image-based first aid assistance that analyzes injuries and provides:
- Injury type assessment
- First aid instructions
- Things to avoid
- When to seek professional help

## 🎯 Key Routes

### Authentication
- `GET/POST /` - Home page
- `GET/POST /signup` - User and doctor registration
- `GET/POST /login` - User and doctor login
- `GET /logout` - Logout

### User Dashboard
- `GET /dashboard` - User dashboard
- `POST /get-dashboard-data` - Get personalized dashboard data
- `POST /predict-disease` - Predict disease from symptoms
- `POST /get-ai-recommendation` - Get AI health recommendations
- `POST /get-hospitals` - Find nearby hospitals
- `POST /upload-daily-report` - Submit daily health report

### Doctor Features
- `GET /doctor-dashboard` - Doctor dashboard
- `POST /get-doctor-consultations` - Get pending/accepted consultations
- `POST /accept-consultation` - Accept consultation request
- `POST /decline-consultation` - Decline consultation request
- `POST /submit-prescription` - Issue prescription to patient

### Appointments
- `POST /book-appointment` - Book doctor appointment
- `POST /get-available-doctors` - Get doctors by specialization
- `POST /get-appointments` - Get user appointments

### Health Tracking
- `POST /upload-report` - Upload health report with image
- `POST /get-injury-first-aid` - Get first aid guidance for injuries
- `POST /add-symptom` - Add symptom to tracking

### Admin Utilities
- `GET /seed-doctors` - Seed sample doctor data
- `GET /seed-hospitals` - Seed sample hospital data

## 📊 Sample Data

The application includes endpoints to seed sample data for testing:
- **Sample Doctors**: Cardiologist, General Physician, Dermatologist, Neurologist
- **Sample Hospitals**: Major hospitals in Chennai, Bangalore, and Hyderabad with coordinates for map display

Login credentials for sample doctor: `priya@hospital.com` / `doctor123`

## 🔍 Key Functions

### `generate_ai_recommendation(user, disease, risk_score, risk_level, symptoms)`
Generates AI-powered personalized health recommendations using Google Gemini.

### `generate_first_aid(image)`
Analyzes injury images and provides first aid guidance.

### User Loader (`load_user`)
Loads user objects for Flask-Login, checking both users and doctors collections.

## 📱 Mobile Compatibility

The application is designed to be responsive and accessible on mobile devices, making it suitable for rural areas with limited internet connectivity.

## ⚠️ Important Notes

- **Medical Disclaimer**: This application provides general health guidance and should NOT replace professional medical consultation.
- **Data Privacy**: User health data is stored securely; ensure HTTPS in production.
- **API Keys**: Never commit `.env` file with API keys to version control.
- **ML Model**: Ensure trained models are available before running the app.

## 🛠️ Development

### Running in Debug Mode
```bash
python app.py
```

### Database Seeding
Visit these URLs to seed sample data:
- `http://localhost:5000/seed-doctors`
- `http://localhost:5000/seed-hospitals`

## 📦 Requirements

See `requirements.txt` for all dependencies:
- flask
- python-dotenv
- pymongo
- google-genai
- pillow
- scikit-learn
- flask-login
- werkzeug

## 🚀 Deployment

For production deployment:
1. Set `debug=False` in `app.run()`
2. Use a production WSGI server (Gunicorn, uWSGI)
3. Configure proper environment variables
4. Enable HTTPS/SSL
5. Set up proper database backups
6. Configure CORS if needed

## 📝 Future Enhancements

- Real-time video consultations
- Multi-language support enhancement
- Pharmacy integration
- Insurance claim management
- Mobile app (iOS/Android)
- Advanced analytics dashboard
- Integration with government health schemes

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support & Contact

For issues, questions, or suggestions, please reach out to the development team or open an issue in the repository.

---

**Last Updated**: 2024
**Version**: 1.0.0
