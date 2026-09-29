import os
import json
from typing import Dict, Any

CRM_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "agent_crm.json")

def load_crm_data() -> Dict[str, Any]:
    if os.path.exists(CRM_FILE):
        try:
            with open(CRM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_crm_status(ad_id: str, status: str, note: str = "") -> None:
    data = load_crm_data()
    data[ad_id] = {
        "status": status,
        "note": note
    }
    os.makedirs(os.path.dirname(CRM_FILE), exist_ok=True)
    with open(CRM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_lead_status(ad_id: str) -> Dict[str, str]:
    data = load_crm_data()
    return data.get(ad_id, {"status": "Do kontaktu", "note": ""})
