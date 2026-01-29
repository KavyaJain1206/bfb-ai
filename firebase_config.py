"""
Firebase Realtime Database Configuration
Setup for FastAPI integration with Firebase
"""

import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db, firestore
from typing import Optional, Dict, List, Any

load_dotenv()

# ============================================================
# FIREBASE INITIALIZATION
# ============================================================

# Option 1: Using Firebase Service Account JSON (Recommended)
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

# Option 2: Using Firebase Connection String
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

# Initialize Firebase
def init_firebase():
    """Initialize Firebase with credentials"""
    try:
        # Check if already initialized
        if firebase_admin._apps:
            return firebase_admin.get_app()
        
        # Option 1: Service Account JSON
        if os.path.exists(FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            app = firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_DATABASE_URL,
                'projectId': FIREBASE_PROJECT_ID
            })
            print("✅ Firebase initialized with service account")
            return app
        
        # Option 2: Default credentials (Google Cloud)
        app = firebase_admin.initialize_app(options={
            'databaseURL': FIREBASE_DATABASE_URL,
            'projectId': FIREBASE_PROJECT_ID
        })
        print("✅ Firebase initialized with default credentials")
        return app
    
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        raise

# Initialize on module load
try:
    firebase_app = init_firebase()
    FIREBASE_ENABLED = True
except Exception as e:
    print(f"⚠️  Firebase not available: {e}")
    FIREBASE_ENABLED = False
    firebase_app = None

# ============================================================
# FIRESTORE CLIENT (Recommended for new projects)
# ============================================================

class FirestoreDB:
    """Firestore Realtime Database client"""
    
    def __init__(self):
        if not FIREBASE_ENABLED:
            raise RuntimeError("Firebase not initialized")
        self.db = firestore.client()
    
    # RAW COMMENTS
    def add_raw_comment(self, comment_data: Dict) -> str:
        """Add new raw comment and return document ID"""
        doc_ref = self.db.collection('raw_comments').document()
        doc_ref.set(comment_data)
        return doc_ref.id
    
    def get_raw_comments(self) -> List[Dict]:
        """Get all raw comments with realtime listener support"""
        docs = self.db.collection('raw_comments').stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    def get_raw_comment(self, comment_id: str) -> Optional[Dict]:
        """Get single raw comment by ID"""
        doc = self.db.collection('raw_comments').document(comment_id).get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None
    
    def update_raw_comment(self, comment_id: str, data: Dict) -> bool:
        """Update raw comment"""
        self.db.collection('raw_comments').document(comment_id).update(data)
        return True
    
    def delete_raw_comment(self, comment_id: str) -> bool:
        """Delete raw comment"""
        self.db.collection('raw_comments').document(comment_id).delete()
        return True
    
    # STRUCTURED SIGNALS
    def add_structured_signal(self, signal_data: Dict) -> str:
        """Add new structured signal"""
        doc_ref = self.db.collection('structured_signals').document()
        doc_ref.set(signal_data)
        return doc_ref.id
    
    def get_structured_signals(self) -> List[Dict]:
        """Get all structured signals"""
        docs = self.db.collection('structured_signals').stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    def get_structured_signal(self, signal_id: str) -> Optional[Dict]:
        """Get single structured signal"""
        doc = self.db.collection('structured_signals').document(signal_id).get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None
    
    def update_structured_signal(self, signal_id: str, data: Dict) -> bool:
        """Update structured signal"""
        self.db.collection('structured_signals').document(signal_id).update(data)
        return True
    
    # ALERTS
    def add_alert(self, alert_data: Dict) -> str:
        """Add new alert"""
        doc_ref = self.db.collection('alerts').document()
        doc_ref.set(alert_data)
        return doc_ref.id
    
    def get_alerts(self, limit: int = 100) -> List[Dict]:
        """Get alerts with optional limit"""
        docs = self.db.collection('alerts')\
            .order_by('generated_at', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    def get_alerts_by_village(self, village: str) -> List[Dict]:
        """Get alerts for specific village"""
        docs = self.db.collection('alerts')\
            .where('village', '==', village)\
            .order_by('generated_at', direction=firestore.Query.DESCENDING)\
            .stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    def delete_old_alerts(self, days: int = 30) -> int:
        """Delete alerts older than specified days"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        docs = self.db.collection('alerts')\
            .where('generated_at', '<', cutoff.isoformat())\
            .stream()
        
        batch = self.db.batch()
        count = 0
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
        batch.commit()
        return count
    
    # STATISTICS
    def get_statistics(self) -> Dict[str, int]:
        """Get overall statistics"""
        return {
            'total_comments': len(self.get_raw_comments()),
            'total_signals': len(self.get_structured_signals()),
            'total_alerts': len(self.get_alerts())
        }
    
    def add_listener(self, collection: str, callback):
        """Add realtime listener to collection"""
        self.db.collection(collection).on_snapshot(callback)
    
    def query_by_timestamp(self, collection: str, start: str, end: str) -> List[Dict]:
        """Query records by timestamp range"""
        docs = self.db.collection(collection)\
            .where('timestamp', '>=', start)\
            .where('timestamp', '<=', end)\
            .stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    def batch_write(self, operations: List[tuple]) -> bool:
        """Batch write operations: (action, collection, doc_id, data)"""
        batch = self.db.batch()
        for action, collection, doc_id, data in operations:
            ref = self.db.collection(collection).document(doc_id)
            if action == 'set':
                batch.set(ref, data)
            elif action == 'update':
                batch.update(ref, data)
            elif action == 'delete':
                batch.delete(ref)
        batch.commit()
        return True


# ============================================================
# REALTIME DATABASE CLIENT (Alternative)
# ============================================================

class RealtimeDB:
    """Firebase Realtime Database client (JSON-based)"""
    
    def __init__(self):
        if not FIREBASE_ENABLED:
            raise RuntimeError("Firebase not initialized")
        self.db = db.reference()
    
    def add_raw_comment(self, comment_data: Dict) -> str:
        """Add raw comment and return ID"""
        ref = self.db.child('raw_comments').push(comment_data)
        return ref.key
    
    def get_raw_comments(self) -> List[Dict]:
        """Get all raw comments"""
        ref = self.db.child('raw_comments').get()
        if ref.val():
            return [{'id': k, **v} for k, v in ref.val().items()]
        return []
    
    def get_raw_comment(self, comment_id: str) -> Optional[Dict]:
        """Get single raw comment"""
        ref = self.db.child('raw_comments').child(comment_id).get()
        if ref.val():
            return {'id': comment_id, **ref.val()}
        return None
    
    def add_structured_signal(self, signal_data: Dict) -> str:
        """Add structured signal"""
        ref = self.db.child('structured_signals').push(signal_data)
        return ref.key
    
    def get_structured_signals(self) -> List[Dict]:
        """Get all structured signals"""
        ref = self.db.child('structured_signals').get()
        if ref.val():
            return [{'id': k, **v} for k, v in ref.val().items()]
        return []
    
    def add_alert(self, alert_data: Dict) -> str:
        """Add alert"""
        ref = self.db.child('alerts').push(alert_data)
        return ref.key
    
    def get_alerts(self) -> List[Dict]:
        """Get all alerts"""
        ref = self.db.child('alerts').get()
        if ref.val():
            return [{'id': k, **v} for k, v in ref.val().items()]
        return []


# ============================================================
# SINGLETON INSTANCES
# ============================================================

# Use Firestore (recommended)
if FIREBASE_ENABLED:
    try:
        firebase_db = FirestoreDB()
        print("✅ Firestore client ready")
    except Exception as e:
        print(f"⚠️  Firestore not available: {e}")
        firebase_db = None
else:
    firebase_db = None


# ============================================================
# MIGRATION UTILITIES
# ============================================================

def migrate_json_to_firebase(json_file_path: str, collection_name: str):
    """Migrate JSON file data to Firebase Firestore"""
    if not firebase_db:
        raise RuntimeError("Firebase not available")
    
    import json
    
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    batch = firebase_db.db.batch()
    for item in data:
        doc_ref = firebase_db.db.collection(collection_name).document()
        batch.set(doc_ref, item)
    batch.commit()
    
    print(f"✅ Migrated {len(data)} records to {collection_name}")
    return len(data)


def backup_firebase_to_json(collection_name: str, output_file: str):
    """Backup Firebase collection to JSON file"""
    if not firebase_db:
        raise RuntimeError("Firebase not available")
    
    import json
    
    docs = firebase_db.db.collection(collection_name).stream()
    data = [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"✅ Backed up {len(data)} records to {output_file}")
    return len(data)
