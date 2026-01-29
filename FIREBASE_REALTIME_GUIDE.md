# 🔥 Firebase Realtime API - Complete Implementation Guide

## 📊 System Architecture with Firebase

```
┌─────────────────────────────────────────────────────────────┐
│            COMMUNITY WATER HEALTH API v2.0                  │
│           (Firebase Realtime Integration)                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            FastAPI Application                        │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │  REST Endpoints          WebSocket Channels          │  │
│  │  ├─ POST /comments    ├─ WS /ws/comments            │  │
│  │  ├─ GET /comments     ├─ WS /ws/alerts              │  │
│  │  ├─ POST /process     └─ Real-time Sync             │  │
│  │  ├─ GET /signals                                     │  │
│  │  ├─ GET /alerts       Gemini AI Integration         │  │
│  │  └─ GET /status       └─ Smart Signal Processing    │  │
│  │                                                       │  │
│  └─────────────────────────┬──────────────────────────┘  │
│                            │                              │
│                    ┌───────▼────────┐                     │
│                    │ firebase_config.py │                  │
│                    │ (Firebase Client)  │                  │
│                    └───────┬────────┘                     │
│                            │                              │
│        ┌───────────────────┼───────────────────┐         │
│        │                   │                   │         │
│        ▼                   ▼                   ▼         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │   Firestore  │  │  Firestore   │  │  Firestore    │ │
│  │  Collection: │  │ Collection:  │  │ Collection:   │ │
│  │raw_comments  │  │structured_   │  │   alerts      │ │
│  │              │  │   signals    │  │               │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
│        │                   │                   │         │
│        └───────────────────┼───────────────────┘         │
│                            │                              │
│                  ┌─────────▼──────────┐                   │
│                  │  Firebase Cloud    │                   │
│                  │  (Realtime Sync)   │                   │
│                  └────────────────────┘                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Automatic Fallback to JSON if Firebase Unavailable │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 What Changed in v2.0

### Before (v1.0 - JSON Only)

```
Comments → API → Save to JSON → Read from JSON → Respond
(No realtime sync, File I/O overhead)
```

### After (v2.0 - Firebase Realtime)

```
Comments → API → Save to Firestore → Instant Cloud Sync → WebSocket Broadcast
(Realtime sync, Automatic backup, Scalable)
```

## 🚀 Installation (Quick Start)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Firebase Project

Visit [Firebase Console](https://console.firebase.google.com) and:

- Create new project
- Enable Firestore database
- Generate service account credentials
- Download JSON key

### 3. Setup Environment

```bash
# Copy template and update with your values
cp .env.template .env

# Edit .env with:
# - GEMINI_API_KEY
# - FIREBASE_PROJECT_ID
# - FIREBASE_DATABASE_URL
# - FIREBASE_CREDENTIALS_PATH (firebase-credentials.json)
```

### 4. Place Credentials

```bash
# Copy downloaded JSON key to project root
cp ~/Downloads/your-project-key.json firebase-credentials.json
```

### 5. Update .gitignore

```bash
# Already done - verify this is in .gitignore:
echo "firebase-credentials.json" >> .gitignore
```

### 6. Run Server

```bash
uvicorn main:app --reload
```

### 7. Verify Setup

```bash
# Check Firebase connection
curl http://localhost:8000/health

# Test adding comment
curl -X POST http://localhost:8000/comments \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"village":"Lakhipur","comment":"Water issue"}'
```

## 📊 Database Collections

### 1. raw_comments

Stores all community water health reports

```json
{
  "user_id": 1,
  "village": "Lakhipur",
  "comment": "Water from well is cloudy...",
  "timestamp": "2026-01-29T12:00:00.000000",
  "gps_latitude": 25.1567,
  "gps_longitude": 90.5897
}
```

**Indexes Created:**

- village (for filtering by location)
- timestamp (for time-based queries)

### 2. structured_signals

AI-processed signals extracted by Gemini

```json
{
  "comment_id": "abc123",
  "village": "Lakhipur",
  "water_source": "well",
  "symptoms": ["loose motion", "headache"],
  "severity": "medium",
  "timestamp": "2026-01-29T12:00:00.000000"
}
```

**Indexes Created:**

- village + severity (for alert filtering)
- timestamp (for trend analysis)

### 3. alerts

Generated alerts from rule engine

```json
{
  "alert_id": "alert123",
  "village": "Lakhipur",
  "severity": "high",
  "rule_triggered": "severity_cluster",
  "symptom_count": 5,
  "signal_count": 12,
  "generated_at": "2026-01-29T12:05:00.000000"
}
```

**Indexes Created:**

- village + generated_at (for village timeline)
- severity (for dashboard filtering)

## 🔌 API Endpoints

### Status

```
GET /health           → {"status": "ok", "firebase_enabled": true}
GET /status          → {"status": "online", "database": "Firestore", "statistics": {...}}
```

### Comments (CRUD)

```
POST /comments                    → Add new comment
GET /comments                     → Get all comments (realtime)
GET /comments/village/{village}   → Get comments by village
DELETE /comments/{comment_id}     → Delete comment
```

### Signals

```
GET /signals                      → Get all structured signals
GET /signals/village/{village}    → Get signals by village
```

### Alerts

```
GET /alerts                       → Generate and get all alerts
GET /alerts/village/{village}     → Get alerts for specific village
```

### WebSocket (Realtime)

```
WS /ws/comments    → Realtime comment stream
WS /ws/alerts      → Realtime alert stream
```

## 💻 Code Examples

### Python - Add Comment with GPS

```python
import requests
import json

response = requests.post('http://localhost:8000/comments', json={
    "user_id": 1,
    "village": "Lakhipur",
    "comment": "Water from well tastes metallic",
    "gps_latitude": 25.1567,
    "gps_longitude": 90.5897
})

result = response.json()
print(f"Comment ID: {result['comment_id']}")
print(f"Database: {result['database']}")  # Will show "Firestore"
```

### JavaScript - Realtime WebSocket Listener

```javascript
// Connect to realtime comment stream
const ws = new WebSocket("ws://localhost:8000/ws/comments");

ws.onopen = () => {
  console.log("Connected to comment stream");
  // Keep connection alive
  setInterval(() => {
    ws.send(JSON.stringify({ type: "ping" }));
  }, 30000);
};

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`${update.type}: ${update.data.village}`);

  // Update UI in realtime
  displayComment(update.data);
};

ws.onerror = (error) => console.error("WebSocket error:", error);
ws.onclose = () => console.log("Disconnected from stream");
```

### React - Realtime Component

```jsx
import { useEffect, useState } from "react";

function CommentsStream() {
  const [comments, setComments] = useState([]);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/comments");

    ws.onmessage = (event) => {
      const { type, data } = JSON.parse(event.data);

      if (type === "ADDED") {
        setComments((prev) => [...prev, data]);
      } else if (type === "REMOVED") {
        setComments((prev) => prev.filter((c) => c.id !== data.id));
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div>
      {comments.map((comment) => (
        <div key={comment.id} className="comment">
          <h3>{comment.village}</h3>
          <p>{comment.comment}</p>
          <small>{new Date(comment.timestamp).toLocaleString()}</small>
        </div>
      ))}
    </div>
  );
}
```

### Python - Query and Filter

```python
from firebase_config import firebase_db

# Get comments by village
lakhipur_comments = firebase_db.db.collection('raw_comments')\
    .where('village', '==', 'Lakhipur')\
    .stream()

for doc in lakhipur_comments:
    data = doc.to_dict()
    print(f"{data['village']}: {data['comment']}")

# Get high-severity alerts
high_alerts = firebase_db.db.collection('alerts')\
    .where('severity', '==', 'high')\
    .order_by('generated_at', direction='DESCENDING')\
    .limit(10)\
    .stream()
```

## 🔄 Data Flow

```
1. User submits comment with GPS
   ↓
2. FastAPI validates input
   ↓
3. Save to Firestore raw_comments
   ↓
4. /process endpoint triggers
   ↓
5. Gemini AI processes comment
   ↓
6. Save to Firestore structured_signals
   ↓
7. Rule engine generates alerts
   ↓
8. Save to Firestore alerts
   ↓
9. WebSocket clients get realtime updates
   ↓
10. Dashboard/Mobile app reflects changes instantly
```

## 🔒 Security Implementation

### Firestore Rules (Production)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /raw_comments/{document=**} {
      allow read: if true;
      allow create: if request.auth != null;
      allow update, delete: if false;
    }

    match /structured_signals/{document=**} {
      allow read: if true;
      allow write: if false;
    }

    match /alerts/{document=**} {
      allow read: if true;
      allow write: if false;
    }
  }
}
```

### Authentication (Optional)

```python
# In main.py, add authentication
from fastapi import Depends, HTTPException, status
from firebase_admin import auth

async def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401)

    try:
        token = authorization.split(' ')[1]
        decoded = auth.verify_id_token(token)
        return decoded['uid']
    except:
        raise HTTPException(status_code=401)

@app.post("/comments")
def add_comment(comment: NewComment, user_id: str = Depends(verify_token)):
    # Only authenticated users can add
    ...
```

## 📈 Monitoring

### Firebase Console Dashboard

- Real-time usage metrics
- Query performance analysis
- Storage breakdown
- Read/write operation counts

### Custom Metrics Endpoint

```python
@app.get("/metrics")
def get_metrics():
    stats = firebase_db.get_statistics()
    return {
        "total_comments": stats['total_comments'],
        "total_signals": stats['total_signals'],
        "total_alerts": stats['total_alerts'],
        "collection_sizes": {
            "raw_comments": stats['total_comments'],
            "structured_signals": stats['total_signals'],
            "alerts": stats['total_alerts']
        }
    }
```

## 🔄 Data Migration

### Migrate from JSON to Firebase

```bash
# Run migration script
python -c "
from firebase_config import migrate_json_to_firebase
migrate_json_to_firebase('data/raw_community_comments_final.json', 'raw_comments')
"
```

### Backup Firebase to JSON

```bash
# Create backup before making changes
python -c "
from firebase_config import backup_firebase_to_json
backup_firebase_to_json('raw_comments', 'backup_`date +%Y%m%d`.json')
"
```

## 🆘 Troubleshooting

| Problem                       | Solution                                               |
| ----------------------------- | ------------------------------------------------------ |
| `Firebase not initialized`    | Check .env has correct paths and credentials exist     |
| `Permission denied`           | Update Firestore security rules, enable authentication |
| `WebSocket connection failed` | Check port 8000 is open, CORS enabled                  |
| `Quota exceeded`              | Check Firebase pricing plan, reduce write frequency    |
| `Slow queries`                | Create indexes in Firestore console                    |

## 📚 Files Overview

| File                        | Purpose                               |
| --------------------------- | ------------------------------------- |
| `main.py`                   | FastAPI app with Firebase integration |
| `firebase_config.py`        | Firebase client and utilities         |
| `requirements.txt`          | All Python dependencies               |
| `.env.template`             | Environment variable template         |
| `FIREBASE_SETUP.md`         | Detailed setup instructions           |
| `firebase-credentials.json` | Service account key (not in repo)     |

## ✅ Deployment Checklist

- [ ] Firebase project created
- [ ] Firestore database enabled
- [ ] Service account credentials downloaded
- [ ] Environment variables configured
- [ ] Credentials file in .gitignore
- [ ] All dependencies installed
- [ ] Server starts without errors
- [ ] Can add comments (check Firestore console)
- [ ] WebSocket connects
- [ ] Realtime updates work
- [ ] Backups configured
- [ ] Security rules set to production
- [ ] Monitoring enabled

## 🎉 Next Steps

1. **Verify Setup**

   ```bash
   curl http://localhost:8000/health
   ```

2. **Check Firebase Console**
   - Go to Firestore > Data
   - Add a test comment via API
   - Verify it appears in console

3. **Test Realtime**
   - Open WebSocket to `/ws/comments`
   - Add comment from another terminal
   - Verify instant update in WebSocket

4. **Configure Mobile App**
   - Use Firebase SDK for mobile
   - Connect to same Firestore database
   - Realtime sync works across all clients

5. **Monitor Performance**
   - Check Firebase console metrics
   - Monitor query latency
   - Set up alerts for quota

## 📞 Support Resources

- [Firebase Console](https://console.firebase.google.com)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Admin SDK Docs](https://firebase.google.com/docs/admin/setup)
- [Security Rules Guide](https://firebase.google.com/docs/firestore/security/start)

---

**Version**: 2.0 (Firebase Realtime)  
**Status**: ✅ Production Ready  
**Database**: Google Cloud Firestore  
**Sync**: Realtime via WebSocket  
**Fallback**: JSON (automatic)  
**Last Updated**: January 29, 2026
