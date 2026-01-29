import json
import os
import time
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import Optional, List
from google import genai

# 🔗 IMPORT RULE ENGINE & FIREBASE
from rules import run_all_rules
from firebase_config import firebase_db, FIREBASE_ENABLED

# -------------------------------------------------
# ENV + GEMINI CLIENT SETUP
# -------------------------------------------------
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY not found in .env")

client = genai.Client(
    api_key=API_KEY,
    http_options={"api_version": "v1"}
)

MODEL_NAME = "gemini-2.5-flash"

# -------------------------------------------------
# FASTAPI SETUP
# -------------------------------------------------
app = FastAPI(
    title="Community Water Health Early Warning API (Firebase Realtime)",
    description="AI-powered early warning system with Firebase Firestore realtime database",
    version="2.0"
)

# Fallback JSON storage (if Firebase unavailable)
DATA_DIR = "data"
RAW_FILE = f"{DATA_DIR}/raw_community_comments_FINAL.json"
STRUCTURED_FILE = f"{DATA_DIR}/structured_signals.json"
ALERT_FILE = f"{DATA_DIR}/alerts.json"

os.makedirs(DATA_DIR, exist_ok=True)

# -------------------------------------------------
# UTILS - JSON Fallback
# -------------------------------------------------
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def extract_json(text: str):
    """Safely extract and parse JSON from Gemini response."""
    if not text or not isinstance(text, str):
        raise ValueError("Empty or invalid response from Gemini")
    
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {text[:100]}")
    
    json_str = text[start:end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {str(e)}. Raw: {json_str[:200]}")

# -------------------------------------------------
# DATA MODELS
# -------------------------------------------------
class NewComment(BaseModel):
    user_id: int
    village: str
    comment: str
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    
    class Config:
        pass
    
    def validate_input(self):
        """Basic input validation."""
        if not self.comment or not self.comment.strip():
            raise ValueError("Comment cannot be empty")
        if not self.village or not self.village.strip():
            raise ValueError("Village cannot be empty")
        if len(self.comment) > 5000:
            raise ValueError("Comment exceeds maximum length")
        return True


class CommentResponse(BaseModel):
    comment_id: str
    user_id: int
    village: str
    comment: str
    timestamp: str
    full_location: Optional[dict] = None
    gps_data: Optional[dict] = None


# -------------------------------------------------
# HEALTH CHECK + STATUS
# -------------------------------------------------
@app.get("/health")
def health():
    """Health check with Firebase status"""
    return {
        "status": "ok",
        "firebase_enabled": FIREBASE_ENABLED,
        "database": "Firestore" if FIREBASE_ENABLED else "JSON"
    }


@app.get("/status")
def get_status():
    """Get system status and database info"""
    if FIREBASE_ENABLED and firebase_db:
        try:
            stats = firebase_db.get_statistics()
            return {
                "status": "online",
                "database": "Firestore (Realtime)",
                "statistics": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "database": "Firebase unavailable"
            }
    else:
        data = {
            "comments": len(load_json(RAW_FILE, [])),
            "signals": len(load_json(STRUCTURED_FILE, [])),
            "alerts": len(load_json(ALERT_FILE, {}).get('alerts', []))
        }
        return {
            "status": "online",
            "database": "JSON (Fallback)",
            "statistics": data
        }

# -------------------------------------------------
# GET RAW COMMENTS (Firebase or JSON)
# -------------------------------------------------
@app.get("/comments", response_model=List[CommentResponse])
def get_comments():
    """Get all raw comments from Firebase or JSON"""
    if FIREBASE_ENABLED and firebase_db:
        try:
            return firebase_db.get_raw_comments()
        except Exception as e:
            print(f"Firebase error: {e}. Falling back to JSON")
            return load_json(RAW_FILE, [])
    return load_json(RAW_FILE, [])

# -------------------------------------------------
# GET RAW COMMENTS (Firebase or JSON)
# -------------------------------------------------
@app.get("/comments", response_model=List[CommentResponse])
def get_comments():
    """Get all raw comments from Firebase or JSON"""
    if FIREBASE_ENABLED and firebase_db:
        try:
            return firebase_db.get_raw_comments()
        except Exception as e:
            print(f"Firebase error: {e}. Falling back to JSON")
            return load_json(RAW_FILE, [])
    return load_json(RAW_FILE, [])

# -------------------------------------------------
# ADD NEW COMMENT (Firebase or JSON)
# -------------------------------------------------
@app.post("/comments", response_model=dict)
def add_comment(comment: NewComment):
    """Add new comment to Firebase or JSON"""
    try:
        comment.validate_input()
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": str(e)}
        )
    
    now = datetime.utcnow().isoformat()
    
    record = {
        "user_id": comment.user_id,
        "village": comment.village.strip(),
        "comment": comment.comment.strip(),
        "timestamp": now
    }
    
    # Add GPS data if provided
    if comment.gps_latitude and comment.gps_longitude:
        record["gps_latitude"] = comment.gps_latitude
        record["gps_longitude"] = comment.gps_longitude
    
    # Save to Firebase if available, else JSON
    if FIREBASE_ENABLED and firebase_db:
        try:
            comment_id = firebase_db.add_raw_comment(record)
            return {
                "status": "comment added",
                "comment_id": comment_id,
                "timestamp": now,
                "database": "Firestore"
            }
        except Exception as e:
            print(f"Firebase error: {e}. Falling back to JSON")
            # Fallback to JSON
            data = load_json(RAW_FILE, [])
            new_id = len(data) + 1
            record["comment_id"] = new_id
            data.append(record)
            save_json(RAW_FILE, data)
            return {
                "status": "comment added",
                "comment_id": new_id,
                "timestamp": now,
                "database": "JSON (Fallback)"
            }
    else:
        # JSON storage
        data = load_json(RAW_FILE, [])
        new_id = len(data) + 1
        record["comment_id"] = new_id
        data.append(record)
        save_json(RAW_FILE, data)
        return {
            "status": "comment added",
            "comment_id": new_id,
            "timestamp": now,
            "database": "JSON"
        }

# -------------------------------------------------
# GET COMMENTS BY VILLAGE (Firebase)
# -------------------------------------------------
@app.get("/comments/village/{village}")
def get_comments_by_village(village: str):
    """Get comments for a specific village (Firebase only)"""
    if not FIREBASE_ENABLED or not firebase_db:
        return {"error": "Firebase not available"}
    
    try:
        docs = firebase_db.db.collection('raw_comments')\
            .where('village', '==', village)\
            .stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        return {"error": str(e)}

# -------------------------------------------------
# DELETE COMMENT (Firebase or JSON)
# -------------------------------------------------
@app.delete("/comments/{comment_id}")
def delete_comment(comment_id: str):
    """Delete a comment"""
    if FIREBASE_ENABLED and firebase_db:
        try:
            firebase_db.delete_raw_comment(comment_id)
            return {"status": "deleted", "comment_id": comment_id}
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": str(e)}
            )
    else:
        # JSON fallback
        data = load_json(RAW_FILE, [])
        data = [x for x in data if x.get('comment_id') != int(comment_id)]
        save_json(RAW_FILE, data)
        return {"status": "deleted", "comment_id": comment_id}

# -------------------------------------------------
# PROCESS NEW COMMENTS (Firebase or JSON)
# -------------------------------------------------
@app.post("/process")
def process_comments():
    """Process unprocessed comments through Gemini and save to Firebase"""
    
    # Get raw comments
    if FIREBASE_ENABLED and firebase_db:
        try:
            raw = firebase_db.get_raw_comments()
            structured = firebase_db.get_structured_signals()
        except:
            raw = load_json(RAW_FILE, [])
            structured = load_json(STRUCTURED_FILE, [])
    else:
        raw = load_json(RAW_FILE, [])
        structured = load_json(STRUCTURED_FILE, [])
    
    processed_ids = {x.get("comment_id") or x.get("id") for x in structured}

    PROMPT = """
Extract structured health signals from the community water health report.

Return ONLY valid JSON with this exact structure:
{
  "village": "",
  "water_source": "well",
  "symptoms": [],
  "severity": "low"
}

Rules:
- Symptoms allowed: loose motion, fever, stomach pain, vomiting, weakness, headache
- Severity: low (1 symptom), medium (2 symptoms), high (3+ symptoms)
- If unsure, return empty symptoms array and low severity

Comment:
{comment}
"""

    MAX_PER_RUN = 5
    new_processed = 0
    errors = []
    rate_limit_hit = False

    for item in raw:
        item_id = item.get("comment_id") or item.get("id")
        if item_id in processed_ids:
            continue
        if new_processed >= MAX_PER_RUN or rate_limit_hit:
            break
        
        if "timestamp" not in item:
            item["timestamp"] = datetime.utcnow().isoformat()

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=PROMPT.format(comment=item["comment"])
            )

            if not response or not response.text:
                raise ValueError("Gemini returned empty response")

            parsed = extract_json(response.text)
            parsed["comment_id"] = item_id
            parsed["timestamp"] = item["timestamp"]
            
            # Save to Firebase if available
            if FIREBASE_ENABLED and firebase_db:
                try:
                    firebase_db.add_structured_signal(parsed)
                except:
                    structured.append(parsed)
                    save_json(STRUCTURED_FILE, structured)
            else:
                structured.append(parsed)
                save_json(STRUCTURED_FILE, structured)
            
            new_processed += 1
            time.sleep(0.5)

        except Exception as e:
            error_msg = str(e)
            errors.append({
                "comment_id": item_id,
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                rate_limit_hit = True
                break

    return {
        "status": "processing complete",
        "new_comments_processed": new_processed,
        "total_structured_records": len(structured),
        "rate_limit_hit": rate_limit_hit,
        "database": "Firestore" if (FIREBASE_ENABLED and firebase_db) else "JSON",
        "errors": errors
    }

# -------------------------------------------------
# TEST SINGLE COMMENT
# -------------------------------------------------
@app.post("/process/test")
def test_single_comment(comment: NewComment):
    try:
        comment.validate_input()
    except ValueError as e:
        return {"status": "error", "message": str(e)}, 400

    PROMPT = f"""Extract structured health signals from the water health report.

Return ONLY valid JSON:
{{
  "village": "{comment.village.strip()}",
  "water_source": "well",
  "symptoms": [],
  "severity": "low"
}}

Rules:
- Symptoms allowed: loose motion, fever, stomach pain, vomiting, weakness, headache
- Severity: low (1 symptom), medium (2 symptoms), high (3+ symptoms)

Comment:
{comment.comment}
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=PROMPT
        )

        if not response or not response.text:
            return {"status": "error", "message": "Gemini returned empty response"}, 500

        parsed = extract_json(response.text)
        parsed["timestamp"] = datetime.utcnow().isoformat()

        return {"status": "success", "ai_output": parsed}

    except ValueError as e:
        return {"status": "error", "message": f"Parsing failed: {str(e)}"}, 400
    except Exception as e:
        import logging
        logging.error(f"Gemini API error in test endpoint: {str(e)}", exc_info=True)
        return {"status": "error", "message": "API call failed. Check server logs."}, 500

# -------------------------------------------------
# GET STRUCTURED SIGNALS (Firebase or JSON)
# -------------------------------------------------
@app.get("/signals")
def get_signals():
    """Get all structured signals"""
    if FIREBASE_ENABLED and firebase_db:
        try:
            return firebase_db.get_structured_signals()
        except Exception as e:
            print(f"Firebase error: {e}")
            return load_json(STRUCTURED_FILE, [])
    return load_json(STRUCTURED_FILE, [])


@app.get("/signals/village/{village}")
def get_signals_by_village(village: str):
    """Get signals for specific village"""
    if FIREBASE_ENABLED and firebase_db:
        try:
            docs = firebase_db.db.collection('structured_signals')\
                .where('village', '==', village)\
                .stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            return {"error": str(e)}
    else:
        signals = load_json(STRUCTURED_FILE, [])
        return [s for s in signals if s.get('village') == village]


# -------------------------------------------------
# ALERTS ENGINE (Firebase or JSON)
# -------------------------------------------------
@app.get("/alerts")
def get_alerts(limit: int = 100):
    """Generate alerts from structured signals"""
    if FIREBASE_ENABLED and firebase_db:
        try:
            signals = firebase_db.get_structured_signals()
        except:
            signals = load_json(STRUCTURED_FILE, [])
    else:
        signals = load_json(STRUCTURED_FILE, [])
    
    if not signals:
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "alert_count": 0,
            "alerts": [],
            "database": "Firestore" if (FIREBASE_ENABLED and firebase_db) else "JSON"
        }
    
    try:
        alerts = run_all_rules(signals)
        
        alert_output = {
            "generated_at": datetime.utcnow().isoformat(),
            "signal_count": len(signals),
            "alerts": alerts
        }
        
        # Save to Firebase if available
        if FIREBASE_ENABLED and firebase_db:
            try:
                for alert in alerts:
                    alert['generated_at'] = alert_output["generated_at"]
                    firebase_db.add_alert(alert)
            except:
                save_json(ALERT_FILE, alert_output)
        else:
            save_json(ALERT_FILE, alert_output)
        
        return {
            "generated_at": alert_output["generated_at"],
            "alert_count": len(alerts),
            "alerts": alerts[:limit],
            "database": "Firestore" if (FIREBASE_ENABLED and firebase_db) else "JSON"
        }
    except Exception as e:
        import logging
        logging.error(f"Alert generation failed: {str(e)}", exc_info=True)
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "alert_count": 0,
            "alerts": [],
            "error": "Alert generation failed. Check server logs."
        }


@app.get("/alerts/village/{village}")
def get_alerts_by_village(village: str):
    """Get alerts for specific village"""
    if FIREBASE_ENABLED and firebase_db:
        try:
            return firebase_db.get_alerts_by_village(village)
        except Exception as e:
            return {"error": str(e)}
    else:
        alerts_data = load_json(ALERT_FILE, {})
        alerts = alerts_data.get('alerts', [])
        return [a for a in alerts if a.get('village') == village]


# -------------------------------------------------
# REALTIME WEBSOCKET SUPPORT (Firebase)
# -------------------------------------------------
@app.websocket("/ws/comments")
async def websocket_comments(websocket: WebSocket):
    """WebSocket for realtime comment updates"""
    if not FIREBASE_ENABLED or not firebase_db:
        await websocket.close(code=4000, reason="Firebase not available")
        return
    
    await websocket.accept()
    
    def on_snapshot(docs, changes, read_time):
        """Firestore snapshot callback"""
        for change in changes:
            try:
                data = change.document.to_dict()
                import asyncio
                asyncio.create_task(websocket.send_json({
                    "type": change.type.name,
                    "data": {'id': change.document.id, **data}
                }))
            except:
                pass
    
    try:
        # Add listener
        listener = firebase_db.db.collection('raw_comments').on_snapshot(on_snapshot)
        
        while True:
            # Keep connection alive
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        listener.unsubscribe()


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket for realtime alert updates"""
    if not FIREBASE_ENABLED or not firebase_db:
        await websocket.close(code=4000, reason="Firebase not available")
        return
    
    await websocket.accept()
    
    def on_snapshot(docs, changes, read_time):
        """Firestore snapshot callback"""
        for change in changes:
            try:
                data = change.document.to_dict()
                import asyncio
                asyncio.create_task(websocket.send_json({
                    "type": change.type.name,
                    "data": {'id': change.document.id, **data}
                }))
            except:
                pass
    
    try:
        listener = firebase_db.db.collection('alerts').on_snapshot(on_snapshot)
        
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        listener.unsubscribe()
