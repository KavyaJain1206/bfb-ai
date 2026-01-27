# Quick Reference: Key Fixes Applied

## 1️⃣ Improved JSON Extraction (Handles Empty/Malformed Responses)

```python
# OLD: Naive, crashes on empty or invalid responses
def extract_json(text: str):
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == -1:
        raise ValueError("Non-JSON response")
    return json.loads(text[start:end])

# NEW: Robust, with detailed error messages
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
```

---

## 2️⃣ Input Validation for Comments

```python
class NewComment(BaseModel):
    user_id: int
    village: str
    comment: str

    def validate_input(self):
        """Basic input validation."""
        if not self.comment or not self.comment.strip():
            raise ValueError("Comment cannot be empty")
        if not self.village or not self.village.strip():
            raise ValueError("Village cannot be empty")
        if len(self.comment) > 5000:
            raise ValueError("Comment exceeds maximum length")
        return True
```

---

## 3️⃣ Timestamp Preservation (Raw → Structured)

```python
# In /process endpoint:
for item in raw:
    # Preserve original timestamp from raw comment
    if "timestamp" not in item:
        item["timestamp"] = datetime.utcnow().isoformat()

    try:
        response = client.models.generate_content(...)
        parsed = extract_json(response.text)

        # Use original timestamp, don't overwrite
        parsed["comment_id"] = item["comment_id"]
        parsed["timestamp"] = item["timestamp"]  # KEY FIX

        structured.append(parsed)
```

---

## 4️⃣ Gemini Response Validation

```python
# Before accessing response.text, validate it exists
response = client.models.generate_content(
    model=MODEL_NAME,
    contents=PROMPT.format(comment=item["comment"])
)

# Validate response has content
if not response or not response.text:
    raise ValueError("Gemini returned empty response")

parsed = extract_json(response.text)
```

---

## 5️⃣ Rate Limit Detection & Reporting

```python
# In /process endpoint:
rate_limit_hit = False

for item in raw:
    try:
        response = client.models.generate_content(...)
        # ... process ...
    except Exception as e:
        error_msg = str(e)
        errors.append({
            "comment_id": item["comment_id"],
            "error": error_msg,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Detect rate limits and break early
        if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
            rate_limit_hit = True
            break

return {
    "status": "processing complete",
    "new_comments_processed": new_processed,
    "total_structured_records": len(structured),
    "rate_limit_hit": rate_limit_hit,  # Client knows to back off
    "errors": errors
}
```

---

## 6️⃣ Better Error Logging (Server-side)

```python
# OLD: Generic error returned to client, no server logging
except Exception as e:
    return {"status": "error", "message": str(e)}

# NEW: Server logs stack trace, client gets generic message
except ValueError as e:
    return {"status": "error", "message": f"Parsing failed: {str(e)}"}, 400
except Exception as e:
    import logging
    logging.error(f"Gemini API error: {str(e)}", exc_info=True)
    return {"status": "error", "message": "API call failed. Check server logs."}, 500
```

---

## 7️⃣ Alerts with Deduplication Metadata

```python
# OLD: Just saves alerts array
def get_alerts():
    signals = load_json(STRUCTURED_FILE, [])
    alerts = run_all_rules(signals)
    save_json(ALERT_FILE, alerts)
    return {"generated_at": now, "alert_count": len(alerts), "alerts": alerts}

# NEW: Includes generation timestamp & signal count for deduplication
def get_alerts():
    signals = load_json(STRUCTURED_FILE, [])

    if not signals:
        return {"generated_at": now, "alert_count": 0, "alerts": []}

    try:
        alerts = run_all_rules(signals)
        alert_output = {
            "generated_at": datetime.utcnow().isoformat(),
            "signal_count": len(signals),  # For change detection
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
        return {"error": "Alert generation failed"}, 500
```

---

## 8️⃣ Performance: Sleep Time Optimization

```python
# OLD: Wasteful 2-second sleep on every request
time.sleep(2)

# NEW: Efficient 0.5-second sleep (safe for Gemini v1 free tier)
time.sleep(0.5)

# Rationale: Rate limit detected → early exit, no need to sleep longer
```

---

## Summary of Changes

| Issue                       | Severity    | Fix                                                  |
| --------------------------- | ----------- | ---------------------------------------------------- |
| Missing response validation | 🔴 Critical | Added `if not response or not response.text` checks  |
| Naive JSON extraction       | 🔴 Critical | Improved error handling with context                 |
| No input validation         | 🟠 High     | Added `validate_input()` with length checks          |
| Timestamp overwriting       | 🟠 High     | Preserve original comment timestamp through pipeline |
| Generic error handling      | 🟠 High     | Separate error types, log stack traces server-side   |
| Poor rate limit handling    | 🟠 High     | Detect 429, return flag to client, break early       |
| No alert deduplication      | 🟡 Medium   | Add generation timestamp & signal count metadata     |
| Inefficient sleep time      | 🟡 Medium   | 2s → 0.5s, maintains API safety                      |

---

## Testing Commands

```bash
# Test empty comment validation
curl -X POST http://localhost:8000/comments \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "village": "TestVillage", "comment": ""}'
# Expected: 400 error, "Comment cannot be empty"

# Test long comment
curl -X POST http://localhost:8000/comments \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "village": "TestVillage", "comment": "'$(python3 -c "print('x'*6000)')''"}'
# Expected: 400 error, "exceeds maximum length"

# Test process with rate limit simulation
# (Manually add rate_limit_hit check in /process)

# Verify timestamps are preserved
curl http://localhost:8000/comments  # Check raw timestamps
curl http://localhost:8000/signals   # Verify they match in structured
curl http://localhost:8000/alerts    # Check generation metadata
```
