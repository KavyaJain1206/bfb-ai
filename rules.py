from collections import defaultdict
from datetime import datetime, timedelta

# =================================================
# CONFIG
# =================================================
ALERT_THRESHOLD = 5

SEVERITY_WEIGHTS = {
    "low": 1,
    "medium": 2,
    "high": 3
}

# =================================================
# HELPERS
# =================================================
def parse_time(ts: str) -> datetime:
    return datetime.fromisoformat(ts)

def within_hours(ts: str, hours: int) -> bool:
    return parse_time(ts) >= datetime.utcnow() - timedelta(hours=hours)

# =================================================
# RULE A — SEVERITY BASED
# =================================================
def rule_A1_high_severity_cluster(signals):
    counts = defaultdict(int)
    alerts = []

    for s in signals:
        if s["severity"] == "high" and within_hours(s["timestamp"], 24):
            counts[s["village"]] += 1

    for village, count in counts.items():
        if count >= 3:
            alerts.append({
                "rule": "A1_HIGH_SEVERITY_CLUSTER",
                "level": "HIGH",
                "village": village,
                "reason": f"{count} high severity reports in 24h"
            })
    return alerts

def rule_A2_mixed_severity(signals):
    village_map = defaultdict(lambda: {"high": 0, "medium": 0})
    alerts = []

    for s in signals:
        if within_hours(s["timestamp"], 24):
            if s["severity"] in ["high", "medium"]:
                village_map[s["village"]][s["severity"]] += 1

    for v, c in village_map.items():
        if c["high"] >= 2 or (c["high"] >= 1 and c["medium"] >= 2):
            alerts.append({
                "rule": "A2_MIXED_SEVERITY",
                "level": "HIGH",
                "village": v,
                "reason": "Mixed high and medium severity spike"
            })
    return alerts

def rule_A3_repeated_medium(signals):
    counts = defaultdict(int)
    alerts = []

    for s in signals:
        if s["severity"] == "medium" and within_hours(s["timestamp"], 48):
            counts[s["village"]] += 1

    for v, c in counts.items():
        if c >= 5:
            alerts.append({
                "rule": "A3_REPEATED_MEDIUM",
                "level": "MEDIUM",
                "village": v,
                "reason": f"{c} medium severity reports in 48h"
            })
    return alerts

# =================================================
# RULE B — VOLUME BASED
# =================================================
def rule_B1_volume_24h(signals):
    counts = defaultdict(int)
    alerts = []

    for s in signals:
        if within_hours(s["timestamp"], 24):
            counts[s["village"]] += 1

    for v, c in counts.items():
        if c >= 5:
            alerts.append({
                "rule": "B1_VOLUME_24H",
                "level": "MEDIUM",
                "village": v,
                "reason": f"{c} reports in 24h"
            })
    return alerts

def rule_B2_volume_48h(signals):
    counts = defaultdict(int)
    alerts = []

    for s in signals:
        if within_hours(s["timestamp"], 48):
            counts[s["village"]] += 1

    for v, c in counts.items():
        if c >= 5:
            alerts.append({
                "rule": "B2_VOLUME_48H",
                "level": "HIGH",
                "village": v,
                "reason": f"{c} reports in 48h"
            })
    return alerts

def rule_B3_extreme_volume(signals):
    counts = defaultdict(int)
    alerts = []

    for s in signals:
        if within_hours(s["timestamp"], 48):
            counts[s["village"]] += 1

    for v, c in counts.items():
        if c >= 10:
            alerts.append({
                "rule": "B3_EXTREME_VOLUME",
                "level": "CRITICAL",
                "village": v,
                "reason": f"{c} reports in 48h"
            })
    return alerts

# =================================================
# RULE C — SYMPTOM PATTERNS
# =================================================
def rule_C1_symptom_diversity(signals):
    alerts = []

    for s in signals:
        if len(set(s.get("symptoms", []))) >= 3:
            alerts.append({
                "rule": "C1_SYMPTOM_DIVERSITY",
                "level": "MEDIUM",
                "village": s["village"],
                "reason": "Single report has 3+ symptoms"
            })
    return alerts

def rule_C2_fever_loose_motion(signals):
    counts = defaultdict(int)
    alerts = []

    for s in signals:
        if within_hours(s["timestamp"], 24):
            symptoms = set(s.get("symptoms", []))
            if "fever" in symptoms and "loose motion" in symptoms:
                counts[s["village"]] += 1

    for v, c in counts.items():
        if c >= 3:
            alerts.append({
                "rule": "C2_FEVER_LOOSE_MOTION",
                "level": "HIGH",
                "village": v,
                "reason": "Fever + loose motion cluster"
            })
    return alerts

def rule_C3_weakness_dominant(signals):
    counts = defaultdict(int)
    alerts = []

    for s in signals:
        if within_hours(s["timestamp"], 24) and "weakness" in s.get("symptoms", []):
            counts[s["village"]] += 1

    for v, c in counts.items():
        if c >= 4:
            alerts.append({
                "rule": "C3_WEAKNESS_DOMINANT",
                "level": "MEDIUM",
                "village": v,
                "reason": "Weakness reported frequently"
            })
    return alerts

# =================================================
# RULE D — TREND BASED
# =================================================
def rule_D1_rising_trend(signals):
    now = datetime.utcnow()
    alerts = []
    village_counts = defaultdict(lambda: {"prev": 0, "curr": 0})

    for s in signals:
        ts = parse_time(s["timestamp"])
        if now - timedelta(hours=12) <= ts:
            village_counts[s["village"]]["curr"] += 1
        elif now - timedelta(hours=24) <= ts < now - timedelta(hours=12):
            village_counts[s["village"]]["prev"] += 1

    for v, c in village_counts.items():
        if c["curr"] > c["prev"] and c["curr"] >= 3:
            alerts.append({
                "rule": "D1_RISING_TREND",
                "level": "MEDIUM",
                "village": v,
                "reason": "Rising report trend"
            })
    return alerts

def rule_D2_continuous_reporting(signals):
    alerts = []
    village_hours = defaultdict(set)

    for s in signals:
        ts = parse_time(s["timestamp"])
        if ts >= datetime.utcnow() - timedelta(hours=24):
            village_hours[s["village"]].add(ts.hour)

    for v, hours in village_hours.items():
        if len(hours) >= 4:
            alerts.append({
                "rule": "D2_CONTINUOUS_REPORTING",
                "level": "MEDIUM",
                "village": v,
                "reason": "Reports coming continuously"
            })
    return alerts

def rule_D3_long_tail(signals):
    counts = defaultdict(int)
    alerts = []

    for s in signals:
        if within_hours(s["timestamp"], 72):
            if s["severity"] in ["low", "medium"]:
                counts[s["village"]] += 1

    for v, c in counts.items():
        if c >= 10:
            alerts.append({
                "rule": "D3_LONG_TAIL",
                "level": "MEDIUM",
                "village": v,
                "reason": "Persistent low/medium reports"
            })
    return alerts

# =================================================
# RULE E — WEIGHTED SCORE
# =================================================
def rule_E1_weighted_score(signals):
    scores = defaultdict(int)
    alerts = []

    for s in signals:
        if within_hours(s["timestamp"], 24):
            scores[s["village"]] += SEVERITY_WEIGHTS.get(s["severity"], 0)

    for v, score in scores.items():
        if score >= 10:
            alerts.append({
                "rule": "E1_WEIGHTED_SCORE",
                "level": "HIGH",
                "village": v,
                "reason": f"Severity score {score} in 24h"
            })
    return alerts

def rule_E2_score_growth(signals):
    now = datetime.utcnow()
    scores = defaultdict(lambda: {"prev": 0, "curr": 0})
    alerts = []

    for s in signals:
        ts = parse_time(s["timestamp"])
        weight = SEVERITY_WEIGHTS.get(s["severity"], 0)

        if now - timedelta(hours=24) <= ts:
            scores[s["village"]]["curr"] += weight
        elif now - timedelta(hours=48) <= ts < now - timedelta(hours=24):
            scores[s["village"]]["prev"] += weight

    for v, s in scores.items():
        if s["prev"] > 0 and s["curr"] >= 1.5 * s["prev"]:
            alerts.append({
                "rule": "E2_SCORE_GROWTH",
                "level": "MEDIUM",
                "village": v,
                "reason": "Severity score rising rapidly"
            })
    return alerts

# =================================================
# RULE F — FAILSAFE
# =================================================
def rule_F1_multi_rule(alerts):
    village_counts = defaultdict(int)
    escalated = []

    for a in alerts:
        village_counts[a["village"]] += 1

    for a in alerts:
        if village_counts[a["village"]] >= 2:
            a["level"] = "HIGH"
            a["reason"] += " (multiple rules triggered)"
            escalated.append(a)

    return escalated

# =================================================
# RUN ALL RULES
# =================================================
def run_all_rules(signals):
    alerts = []

    alerts += rule_A1_high_severity_cluster(signals)
    alerts += rule_A2_mixed_severity(signals)
    alerts += rule_A3_repeated_medium(signals)

    alerts += rule_B1_volume_24h(signals)
    alerts += rule_B2_volume_48h(signals)
    alerts += rule_B3_extreme_volume(signals)

    alerts += rule_C1_symptom_diversity(signals)
    alerts += rule_C2_fever_loose_motion(signals)
    alerts += rule_C3_weakness_dominant(signals)

    alerts += rule_D1_rising_trend(signals)
    alerts += rule_D2_continuous_reporting(signals)
    alerts += rule_D3_long_tail(signals)

    alerts += rule_E1_weighted_score(signals)
    alerts += rule_E2_score_growth(signals)

    alerts = rule_F1_multi_rule(alerts)

    return alerts
