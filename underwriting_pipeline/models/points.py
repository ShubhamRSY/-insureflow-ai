"""Step 4 — point hazard rank. Not a price, not a decline, not a carrier pick.

# ponytail: fixed points, no fit. Replace weights when loss labels exist.

Run: python underwriting_pipeline/models/points.py
"""


def score(facts: dict) -> dict:
    points = 0
    reasons = []
    if facts.get("liability_claim") or facts.get("property_claim_over_25k"):
        points += 30
        reasons.append("LOSS_HISTORY")
    if facts.get("construction") == "frame":
        points += 15
        reasons.append("FRAME_CONSTRUCTION")
    if facts.get("cooking") or facts.get("restaurant"):
        points += 25
        reasons.append("COOKING")
    if facts.get("habitational"):
        points += 15
        reasons.append("HABITATIONAL")
    if facts.get("contracting"):
        points += 15
        reasons.append("CONTRACTING")
    tiv = facts.get("tiv") or 0
    if tiv > 1_000_000:
        points += 10
        reasons.append("TIV_OVER_1M")
    return {"points": points, "reason_codes": reasons}


if __name__ == "__main__":
    office = score({"construction": "masonry", "tiv": 500_000})
    kitchen = score({"restaurant": True, "cooking": True, "tiv": 800_000})
    assert office["points"] < kitchen["points"]
    assert "COOKING" in kitchen["reason_codes"]
    assert "decline" not in office and "premium" not in office
    assert score({})["points"] == 0
    print("points ok", office, kitchen)
