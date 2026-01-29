# 🔥 Firebase Integration - Setup Guide

## Overview

Your API now supports **Firebase Firestore** for realtime database capabilities. This guide will help you set it up.

## ✨ Key Features

✅ **Realtime Database** - Automatic synchronization across clients  
✅ **Cloud Firestore** - Scalable NoSQL database  
✅ **WebSocket Support** - Realtime updates via WebSocket  
✅ **Automatic Sync** - Data syncs instantly across all clients  
✅ **Fallback Support** - Works with JSON if Firebase unavailable  
✅ **Batch Operations** - Efficient multi-record updates  
✅ **Query Support** - Filter by village, timestamp, severity  
✅ **Data Backup** - Automatic cloud backup

## 📋 Setup Steps

### Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Add project"
3. Enter project name (e.g., "Water Health API")
4. Enable Google Analytics (optional)
5. Click "Create project"

### Step 2: Enable Firestore

1. In Firebase Console, go to "Firestore Database"
2. Click "Create database"
3. Select region (choose closest to your location)
4. Start in **Test mode** (development)
5. Click "Create"

### Step 3: Create Service Account

1. Go to Project Settings (⚙️ icon)
2. Click "Service Accounts"
3. Click "Generate new private key"
4. Save as `firebase-credentials.json` in your project root
5. **IMPORTANT**: Add to `.gitignore` to keep it private

### Step 4: Configure Environment Variables

Create/Update `.env` file:

```bash
# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_DATABASE_URL=https://your-project-id.firebaseio.com
```

Get these values from:

- **PROJECT_ID**: Firebase Console > Project Settings
- **DATABASE_URL**: Firestore > Project Settings > Database URL

### Step 5: Install Firebase Admin SDK

```bash
pip install firebase-admin
```

### Step 6: Install Required Packages

```bash
pip install geopy requests websockets python-socketio
```

### Step 7: Create Firestore Collections (Optional)

Firebase auto-creates collections when you write data, but you can pre-create them:

1. In Firestore Console, click "Start Collection"
2. Create collections:
   - `raw_comments`
   - `structured_signals`
   - `alerts`

### Step 8: Update Firestore Security Rules

Go to Firestore > Rules and set:

**For Development** (Testing only):

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if true;
    }
  }
}
```

**For Production** (Secure):

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /raw_comments/{document=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
    match /structured_signals/{document=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
    match /alerts/{document=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

Click "Publish" to save rules.

## 🚀 Quick Start

### 1. Verify Setup

```bash
python -c "from firebase_config import firebase_db; print('✅ Firebase ready')"
```

### 2. Run the Server

```bash
uvicorn main:app --reload
```

### 3. Test Endpoints

#### Add Comment

```bash
curl -X POST http://localhost:8000/comments \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "village": "Lakhipur",
    "comment": "Water issue found",
    "gps_latitude": 25.1567,
    "gps_longitude": 90.5897
  }'
```

#### Get Comments

```bash
curl http://localhost:8000/comments
```

#### Process Comments

```bash
curl -X POST http://localhost:8000/process
```

#### Get Alerts

```bash
curl http://localhost:8000/alerts
```

### 4. Connect WebSocket (Realtime)

JavaScript example:

```javascript
// Realtime comment updates
const ws = new WebSocket("ws://localhost:8000/ws/comments");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("New comment:", data.data);
};

ws.send(JSON.stringify({ type: "ping" }));
```

## 📊 Firestore Collections Structure

### raw_comments

```
{
  "comment_id": "auto-generated-id",
  "user_id": 1,
  "village": "Lakhipur",
  "comment": "Water from well is cloudy...",
  "timestamp": "2026-01-29T12:00:00.000000",
  "gps_latitude": 25.1567,
  "gps_longitude": 90.5897
}
```

### structured_signals

```
{
  "comment_id": "auto-generated-id",
  "village": "Lakhipur",
  "water_source": "well",
  "symptoms": ["loose motion", "headache"],
  "severity": "medium",
  "timestamp": "2026-01-29T12:00:00.000000"
}
```

### alerts

```
{
  "alert_id": "auto-generated-id",
  "village": "Lakhipur",
  "severity": "high",
  "rule_triggered": "severity_cluster",
  "timestamp": "2026-01-29T12:00:00.000000",
  "generated_at": "2026-01-29T12:05:00.000000"
}
```

## 🔌 API Endpoints (New/Updated)

### Comments

- `GET /comments` - Get all comments
- `POST /comments` - Add new comment (with GPS support)
- `GET /comments/village/{village}` - Get comments by village
- `DELETE /comments/{comment_id}` - Delete comment
- `WS /ws/comments` - Realtime updates

### Signals

- `GET /signals` - Get all signals
- `GET /signals/village/{village}` - Get signals by village

### Alerts

- `GET /alerts?limit=100` - Get alerts
- `GET /alerts/village/{village}` - Get alerts by village
- `WS /ws/alerts` - Realtime alert updates

### Status

- `GET /health` - Health check with Firebase status
- `GET /status` - System status with statistics

## 📱 Mobile App Integration

### JavaScript/React

```javascript
import firebase from "firebase/app";
import "firebase/firestore";

const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  projectId: "your-project-id",
  databaseURL: "https://your-project-id.firebaseio.com",
};

const app = firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();

// Realtime listener
db.collection("comments").onSnapshot((snapshot) => {
  snapshot.docChanges().forEach((change) => {
    if (change.type === "added") {
      console.log("New comment:", change.doc.data());
    }
  });
});
```

### Python

```python
from firebase_config import firebase_db

# Get comments
comments = firebase_db.get_raw_comments()

# Get comments by village
docs = firebase_db.db.collection('raw_comments')\
    .where('village', '==', 'Lakhipur')\
    .stream()

# Listen to changes
def on_snapshot(doc, changes, read_time):
    for change in changes:
        print(f'{change.type}: {change.document.id}')

listener = firebase_db.db.collection('raw_comments').on_snapshot(on_snapshot)
```

## 🔒 Security Best Practices

1. **Keep credentials private**

   ```bash
   echo "firebase-credentials.json" >> .gitignore
   ```

2. **Use environment variables**

   ```python
   # Never hardcode credentials
   cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
   ```

3. **Enable Firebase Authentication**
   - In Firebase Console > Authentication
   - Enable sign-in methods (Email, Google, Phone)
   - Update Firestore rules for user-based access

4. **Set up Firestore Rules**
   - Allow read for public data
   - Require authentication for writes
   - Validate data structure

5. **Enable API Key Restrictions**
   - Firebase Console > APIs & Services
   - Restrict API keys to specific services

## 🆘 Troubleshooting

### "Firebase not initialized"

- Check `firebase-credentials.json` exists
- Verify environment variables in `.env`
- Restart the server

### "Permission denied" error

- Update Firestore security rules
- Check authentication is enabled
- Verify user has write permission

### "Quota exceeded"

- Check Firebase pricing plan
- Monitor usage in Firebase Console
- Set up alerts for quota limits

### WebSocket connection fails

- Check firewall allows WebSocket (port 8000)
- Verify CORS is enabled
- Check browser console for errors

## 📈 Monitoring & Analytics

### Firebase Console

- **Firestore Dashboard**: Real-time data usage
- **Realtime Database**: Connection monitoring
- **Analytics**: User engagement metrics
- **Performance**: Query performance analysis

### Custom Metrics

```python
from firebase_config import firebase_db

# Get statistics
stats = firebase_db.get_statistics()
print(f"Comments: {stats['total_comments']}")
print(f"Signals: {stats['total_signals']}")
print(f"Alerts: {stats['total_alerts']}")
```

## 🔄 Data Migration

### Migrate from JSON to Firebase

```bash
# Using provided utility
python -c "from firebase_config import migrate_json_to_firebase; migrate_json_to_firebase('data/raw_community_comments_final.json', 'raw_comments')"
```

### Backup Firebase to JSON

```bash
# Backup all collections
python -c "from firebase_config import backup_firebase_to_json; backup_firebase_to_json('raw_comments', 'backup_comments.json')"
```

## 💰 Pricing

**Firestore Free Tier:**

- 1 GB storage
- 50,000 read operations/day
- 20,000 write operations/day
- 20,000 delete operations/day

**After Free Tier:**

- $0.06 per 100,000 reads
- $0.18 per 100,000 writes
- $0.02 per 100,000 deletes

## 🎯 Next Steps

1. ✅ Create Firebase project
2. ✅ Enable Firestore
3. ✅ Generate service account key
4. ✅ Update `.env` file
5. ✅ Install Firebase SDK
6. ✅ Test endpoints
7. ✅ Set up security rules
8. ✅ Migrate data (if needed)
9. ✅ Deploy to production

## 📚 Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [Firestore Best Practices](https://firebase.google.com/docs/firestore/best-practices)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Firestore Security Rules](https://firebase.google.com/docs/firestore/security/start)

## ✅ Verification Checklist

- [ ] Firebase project created
- [ ] Firestore database enabled
- [ ] Service account key generated
- [ ] Environment variables set in `.env`
- [ ] Firebase Admin SDK installed
- [ ] `firebase-credentials.json` in project root
- [ ] `firebase-credentials.json` in `.gitignore`
- [ ] Firestore security rules configured
- [ ] Test endpoint responds
- [ ] WebSocket connection works
- [ ] Data appears in Firestore Console

## 🎉 You're Ready!

Your API now has Firebase realtime database support. Start using it with:

```bash
uvicorn main:app --reload
```

---

**Status**: ✅ Setup Complete  
**Database**: Firestore (Cloud)  
**Sync**: Realtime  
**Fallback**: JSON (automatic)
