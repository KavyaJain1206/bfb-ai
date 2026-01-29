# Firebase Update - Visual Guide & Checklists

## 🎨 Visual Flow - How It Works Now

```
┌──────────────────────────────────────────────────────────┐
│                  CLIENT (Mobile/Web/Desktop)             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────┐      ┌──────────────────────┐ │
│  │  Submit Comment     │      │  Listen to Updates   │ │
│  │  with GPS coords    │      │  via WebSocket       │ │
│  └────────────┬────────┘      └──────────────┬───────┘ │
│               │                              │          │
└───────────────┼──────────────────────────────┼──────────┘
                │                              │
                │ HTTP POST                    │ WebSocket
                │ /comments                    │ /ws/comments
                │                              │
┌───────────────▼──────────────────────────────▼──────────┐
│            FastAPI Backend (main.py)                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  firebase_config.py                             │   │
│  │  ├─ Save comment to Firestore                  │   │
│  │  ├─ Process with Gemini AI                     │   │
│  │  ├─ Generate alerts from rules.py              │   │
│  │  └─ Send realtime updates via WebSocket        │   │
│  └──────────────────┬────────────────────────────┘   │
│                     │                                  │
└─────────────────────┼──────────────────────────────────┘
                      │
          ┌───────────┴──────────────┐
          │                          │
          ▼                          ▼
    ┌──────────────┐          ┌──────────────┐
    │  Firestore   │          │  JSON Files  │
    │  Database    │          │  (Fallback)  │
    │  (Primary)   │          │              │
    └──────────────┘          └──────────────┘
          │                          │
          └───────────┬──────────────┘
                      │
          ┌───────────▼────────────┐
          │  Google Cloud Backup   │
          │  (Daily automatic)     │
          └────────────────────────┘
```

## 📋 Setup Checklist

### Phase 1: Firebase Project Setup (10 min)

- [ ] Go to https://console.firebase.google.com
- [ ] Click "Create project"
- [ ] Enter project name
- [ ] Enable Google Analytics (optional)
- [ ] Wait for project creation (1-2 min)
- [ ] Go to Firestore Database
- [ ] Click "Create database"
- [ ] Select test mode (for development)
- [ ] Choose nearest region
- [ ] Wait for database creation

### Phase 2: Service Account Setup (10 min)

- [ ] In Firebase Console, click Settings (⚙️)
- [ ] Select "Service Accounts"
- [ ] Click "Generate New Private Key"
- [ ] Save file as `firebase-credentials.json`
- [ ] Place in your project root directory
- [ ] Add `firebase-credentials.json` to `.gitignore`
- [ ] Note your Project ID
- [ ] Note your Database URL

### Phase 3: Local Configuration (5 min)

- [ ] Copy `.env.template` to `.env`
- [ ] Edit `.env` with your Firebase values:
  - `FIREBASE_PROJECT_ID=your-project-id`
  - `FIREBASE_DATABASE_URL=https://your-project-id.firebaseio.com`
  - `FIREBASE_CREDENTIALS_PATH=firebase-credentials.json`
- [ ] Add your `GEMINI_API_KEY`

### Phase 4: Dependencies (5 min)

- [ ] Run: `pip install -r requirements.txt`
- [ ] Verify Firebase installed: `pip show firebase-admin`
- [ ] Check for errors

### Phase 5: Run & Test (5 min)

- [ ] Run: `uvicorn main:app --reload`
- [ ] Verify: `curl http://localhost:8000/health`
- [ ] Should show: `"firebase_enabled": true`

## 🎯 Action Plan (Copy & Paste)

### Command 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Command 2: Setup Environment

```bash
# Copy template
cp .env.template .env

# Edit .env (use your editor)
# nano .env    (Linux/Mac)
# code .env    (VS Code)
# notepad .env (Windows)
```

### Command 3: Place Credentials

```bash
# Copy your Firebase JSON
cp ~/Downloads/your-project-key.json firebase-credentials.json

# Verify it's ignored
cat .gitignore | grep firebase-credentials.json
```

### Command 4: Run Server

```bash
uvicorn main:app --reload
```

### Command 5: Test

```bash
# Health check
curl http://localhost:8000/health

# Add comment
curl -X POST http://localhost:8000/comments \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"village":"Lakhipur","comment":"Test"}'

# Get comments
curl http://localhost:8000/comments
```

## 🔍 Verification Steps

### ✅ Check 1: Server Running

```bash
curl http://localhost:8000/health
```

**Expected**: `{"status":"ok","firebase_enabled":true,...}`

### ✅ Check 2: Firebase Connected

```bash
curl http://localhost:8000/status
```

**Expected**: Shows Firestore database with stats

### ✅ Check 3: Add Comment

```bash
curl -X POST http://localhost:8000/comments \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "village": "Lakhipur",
    "comment": "Water test comment"
  }'
```

**Expected**: Returns `comment_id` and `"database": "Firestore"`

### ✅ Check 4: Read from Firebase

```bash
curl http://localhost:8000/comments
```

**Expected**: JSON array with your comment

### ✅ Check 5: Check Firestore Console

1. Go to Firebase Console
2. Click "Firestore Database"
3. Click "Data"
4. Expand "raw_comments" collection
5. **Expected**: Your comment appears in real-time!

## 🌐 WebSocket Test (Realtime)

### Using Node.js

```bash
npm install ws
```

```javascript
const WebSocket = require("ws");
const ws = new WebSocket("ws://localhost:8000/ws/comments");

ws.on("open", () => {
  console.log("Connected");
  ws.send(JSON.stringify({ type: "ping" }));
});

ws.on("message", (msg) => {
  const data = JSON.parse(msg);
  console.log("Received:", data.type, data.data.village);
});
```

### Using Python

```python
import asyncio
import websockets
import json

async def listen():
    uri = "ws://localhost:8000/ws/comments"
    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            print(f"New {data['type']}: {data['data']['village']}")

asyncio.run(listen())
```

### Using Browser JavaScript

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/comments");

ws.onmessage = (event) => {
  const { type, data } = JSON.parse(event.data);
  console.log(`${type}: ${data.village}`);
};

// Keep connection alive
setInterval(() => {
  ws.send(JSON.stringify({ type: "ping" }));
}, 30000);
```

## 📊 Monitoring Dashboard

### Firebase Console

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Click "Firestore Database"
4. Monitor:
   - **Data**: View your collections
   - **Usage**: Read/write statistics
   - **Indexes**: View created indexes

### Firestore Collections

- **raw_comments**: All user-submitted comments
- **structured_signals**: AI-processed signals
- **alerts**: Generated alerts

### Useful Firestore Queries

```javascript
// Get comments from Lakhipur
db.collection("raw_comments").where("village", "==", "Lakhipur").get();

// Get high-severity alerts
db.collection("alerts")
  .where("severity", "==", "high")
  .orderBy("generated_at", "desc")
  .limit(10)
  .get();

// Get comments in last 7 days
const week_ago = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
db.collection("raw_comments")
  .where("timestamp", ">=", week_ago.toISOString())
  .get();
```

## 🔐 Security Rules Update

### Step 1: Go to Firestore Rules

1. Firebase Console → Firestore Database
2. Click "Rules" tab
3. Clear existing rules

### Step 2: Paste Production Rules

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

### Step 3: Publish

Click "Publish" button

## 🆘 Quick Troubleshooting

### Issue: "Firebase not enabled"

```bash
# Check credentials file exists
ls firebase-credentials.json

# Check .env has correct values
cat .env | grep FIREBASE
```

### Issue: "Permission denied"

```bash
# Go to Firebase Console > Firestore > Rules
# Check rules allow your operations
# For development, use test mode rules (allow all)
```

### Issue: "WebSocket connection failed"

```bash
# Check server is running
curl http://localhost:8000/health

# Check firewall allows port 8000
netstat -an | grep 8000

# Check WebSocket URL is correct
# Should be: ws://localhost:8000/ws/comments
```

### Issue: "No data appears in Firestore"

```bash
# Check credentials have write permissions
# Verify service account is added to project
# Check IAM roles in Firebase Console
```

## 📞 Getting Help

| Resource        | Link                                                |
| --------------- | --------------------------------------------------- |
| Firebase Docs   | https://firebase.google.com/docs                    |
| Firestore Guide | https://firebase.google.com/docs/firestore          |
| Admin SDK       | https://firebase.google.com/docs/admin/setup        |
| Community       | https://stackoverflow.com/questions/tagged/firebase |

## ✨ You're Ready!

### Final Checklist

- [ ] Firebase project created ✓
- [ ] Credentials downloaded ✓
- [ ] `.env` configured ✓
- [ ] Dependencies installed ✓
- [ ] Server running ✓
- [ ] Health check passes ✓
- [ ] Data in Firestore ✓
- [ ] WebSocket works ✓

### Next Actions

1. **Read**: [FIREBASE_SETUP.md](FIREBASE_SETUP.md) for detailed steps
2. **Read**: [FIREBASE_REALTIME_GUIDE.md](FIREBASE_REALTIME_GUIDE.md) for complete guide
3. **Integrate**: Add Firebase SDK to your app
4. **Deploy**: Push to production
5. **Monitor**: Track usage in Firebase Console

---

**Status**: ✅ Ready for Production  
**Database**: Google Cloud Firestore  
**Sync**: Real-time  
**Support**: Full documentation provided

Good luck! 🚀
