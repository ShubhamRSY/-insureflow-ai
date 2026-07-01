from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NCCIClassCode:
    code: str
    description: str
    risk_level: str  # low, moderate, high, critical
    typical_industries: list[str] = field(default_factory=list)


NCCI_CLASS_CODES: dict[str, NCCIClassCode] = {
    "8810": NCCIClassCode(
        "8810", "Clerical Office", "low", ["office", "administrative", "professional services"]
    ),
    "8824": NCCIClassCode("8824", "Accounting or Auditing", "low", ["accounting", "finance"]),
    "8831": NCCIClassCode("8831", "Real Estate Appraisal", "low", ["real estate", "appraisal"]),
    "7720": NCCIClassCode("7720", "Retail Store — NOC", "low", ["retail", "store"]),
    "8008": NCCIClassCode("8008", "Wholesale Store — NOC", "low", ["wholesale", "distribution"]),
    "8017": NCCIClassCode(
        "8017", "Restaurant — Fast Food", "moderate", ["restaurant", "fast food"]
    ),
    "8031": NCCIClassCode(
        "8031", "Restaurant — Full Service", "moderate", ["restaurant", "dining"]
    ),
    "8044": NCCIClassCode("8044", "Bar or Tavern", "moderate", ["bar", "nightclub"]),
    "8380": NCCIClassCode("8380", "Marine Cargo Handling", "high", ["marine", "shipping", "cargo"]),
    "8391": NCCIClassCode(
        "8391", "Trucking — NOC", "high", ["trucking", "transportation", "logistics"]
    ),
    "5402": NCCIClassCode("5402", "Carpentry — Residential", "high", ["construction", "carpentry"]),
    "5403": NCCIClassCode("5403", "Carpentry — Commercial", "high", ["construction", "carpentry"]),
    "5221": NCCIClassCode("5221", "Concrete or Cement Work", "high", ["construction", "concrete"]),
    "5222": NCCIClassCode("5222", "Roofing", "critical", ["construction", "roofing"]),
    "5223": NCCIClassCode(
        "5223", "Structural Steel Erection", "critical", ["construction", "steel erection"]
    ),
    "5555": NCCIClassCode("5555", "General Classification", "moderate", ["general"]),
    "9101": NCCIClassCode("9101", "Janitorial Services", "moderate", ["janitorial", "cleaning"]),
    "9519": NCCIClassCode("9519", "Machine Shop", "high", ["manufacturing", "machining"]),
    "9534": NCCIClassCode("9534", "Welding", "high", ["manufacturing", "welding"]),
}


def get_ncci_risk_level(class_code: str) -> str:
    entry = NCCI_CLASS_CODES.get(class_code)
    return entry.risk_level if entry else "moderate"


def is_high_risk_ncci_class(class_code: str) -> bool:
    return get_ncci_risk_level(class_code) in ("high", "critical")


def get_ncci_description(class_code: str) -> str:
    entry = NCCI_CLASS_CODES.get(class_code)
    return entry.description if entry else "Unknown classification"
