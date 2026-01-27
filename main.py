import json
import os
import time
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai

# 🔗 IMPORT RULE ENGINE
from rules import run_all_rules

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
    title="Community Water Health Early Warning API",
    description="AI-powered early warning system using community water reports",
    version="1.0"
)

DATA_DIR = "data"
RAW_FILE = f"{DATA_DIR}/raw_community_comments_FINAL.json"
STRUCTURED_FILE = f"{DATA_DIR}/structured_signals.json"
ALERT_FILE = f"{DATA_DIR}/alerts.json"

os.makedirs(DATA_DIR, exist_ok=True)

# -------------------------------------------------
# UTILS
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
# DATA MODEL
# -------------------------------------------------
class NewComment(BaseModel):
    user_id: int
    village: str
    comment: str
    
    class Config:
        # Validate non-empty strings
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

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# -------------------------------------------------
# GET RAW COMMENTS
# -------------------------------------------------
@app.get("/comments")
def get_comments():
    return load_json(RAW_FILE, [])

# -------------------------------------------------
# ADD NEW COMMENT
# -------------------------------------------------
@app.post("/comments")
def add_comment(comment: NewComment):
    try:
        comment.validate_input()
    except ValueError as e:
        return {"status": "error", "message": str(e)}, 400
    
    data = load_json(RAW_FILE, [])
    new_id = len(data) + 1
    now = datetime.utcnow().isoformat()

    record = {
        "comment_id": new_id,
        "user_id": comment.user_id,
        "village": comment.village.strip(),
        "comment": comment.comment.strip(),
        "timestamp": now
    }

    data.append(record)
    save_json(RAW_FILE, data)

    return {
        "status": "comment added",
        "comment_id": new_id,
        "timestamp": now
    }

# -------------------------------------------------
# PROCESS NEW COMMENTS (SAFE + BATCHED)
# -------------------------------------------------
@app.post("/process")
def process_comments():
    raw = load_json(RAW_FILE, [])
    structured = load_json(STRUCTURED_FILE, [])
    processed_ids = {x["comment_id"] for x in structured}

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
        if item["comment_id"] in processed_ids:
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

            # Validate response has content
            if not response or not response.text:
                raise ValueError("Gemini returned empty response")

            parsed = extract_json(response.text)
            
            # Preserve original comment timestamp
            parsed["comment_id"] = item["comment_id"]
            parsed["timestamp"] = item["timestamp"]

            structured.append(parsed)
            new_processed += 1

            time.sleep(0.5)  # reduced from 2s for efficiency

        except Exception as e:
            error_msg = str(e)
            errors.append({
                "comment_id": item["comment_id"],
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Check for rate limiting
            if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                rate_limit_hit = True
                break

    save_json(STRUCTURED_FILE, structured)

    return {
        "status": "processing complete",
        "new_comments_processed": new_processed,
        "total_structured_records": len(structured),
        "rate_limit_hit": rate_limit_hit,
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
# GET STRUCTURED SIGNALS
# -------------------------------------------------
@app.get("/signals")
def get_signals():
    return load_json(STRUCTURED_FILE, [])

# -------------------------------------------------
# 🚨 ALERT ENGINE (RULE-BASED)
# -------------------------------------------------
@app.get("/alerts")
def get_alerts():
    """Generate alerts from structured signals using rule engine."""
    signals = load_json(STRUCTURED_FILE, [])
    
    if not signals:
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "alert_count": 0,
            "alerts": []
        }
    
    try:
        alerts = run_all_rules(signals)
        
        # Save with generation timestamp for deduplication on client side
        alert_output = {
            "generated_at": datetime.utcnow().isoformat(),
            "signal_count": len(signals),
            "alerts": alerts
        }
        
        save_json(ALERT_FILE, alert_output)
        
        return {
            "generated_at": alert_output["generated_at"],
            "alert_count": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        import logging
        logging.error(f"Alert generation failed: {str(e)}", exc_info=True)
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "alert_count": 0,
            "alerts": [],
            "error": "Alert generation failed. Check server logs."
        }, 500
