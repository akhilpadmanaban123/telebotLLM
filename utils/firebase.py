import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase(service_account_key_path):
    """
    Initialize Firebase Admin SDK with the service account key.
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_key_path)
        firebase_admin.initialize_app(cred)

def get_firestore_client():
    """
    Return a Firestore client instance.
    """
    return firestore.client()
