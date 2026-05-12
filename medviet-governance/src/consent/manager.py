# src/consent/manager.py
import json
import os
from datetime import datetime, timezone
from typing import Optional

CONSENT_STORE_PATH = "data/consents.json"


def _load_store() -> dict:
    if os.path.exists(CONSENT_STORE_PATH):
        with open(CONSENT_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_store(store: dict) -> None:
    os.makedirs(os.path.dirname(CONSENT_STORE_PATH), exist_ok=True)
    with open(CONSENT_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def give_consent(patient_id: str, purpose: str, given_by: str) -> dict:
    """Thu thập consent của bệnh nhân. Lưu với timestamp theo NĐ13."""
    store = _load_store()
    record = {
        "patient_id": patient_id,
        "status": "active",
        "purpose": purpose,
        "given_by": given_by,
        "given_at": datetime.now(timezone.utc).isoformat(),
        "revoked_at": None,
    }
    store[patient_id] = record
    _save_store(store)
    return record


def revoke_consent(patient_id: str, revoked_by: str) -> Optional[dict]:
    """Rút consent (Right to Erasure theo NĐ13/GDPR). Trả về None nếu không tìm thấy."""
    store = _load_store()
    if patient_id not in store:
        return None
    store[patient_id]["status"] = "revoked"
    store[patient_id]["revoked_at"] = datetime.now(timezone.utc).isoformat()
    store[patient_id]["revoked_by"] = revoked_by
    _save_store(store)
    return store[patient_id]


def get_consent(patient_id: str) -> Optional[dict]:
    """Kiểm tra trạng thái consent của bệnh nhân."""
    return _load_store().get(patient_id)


def has_active_consent(patient_id: str) -> bool:
    """True nếu bệnh nhân có consent còn hiệu lực."""
    record = get_consent(patient_id)
    return record is not None and record["status"] == "active"


def list_consents() -> list:
    """Trả về tất cả consent records (dùng cho audit)."""
    return list(_load_store().values())
