import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

# Load dataset
train_df = pd.read_csv("Training.csv")

# Separate features and target
X = train_df.drop("prognosis", axis=1)
y = train_df["prognosis"]

# Encode target labels (disease names → numbers)
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# Train model
model = RandomForestClassifier()
model.fit(X, y_encoded)

# Save model + label encoder
joblib.dump(model, "models/disease_model.pkl")
joblib.dump(le, "models/label_encoder.pkl")

print("Model trained and saved successfully!")