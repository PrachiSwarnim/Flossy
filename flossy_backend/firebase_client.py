import firebase_admin
from firebase_admin import credentials, messaging

# Initialize Firebase app once globally
cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred)
