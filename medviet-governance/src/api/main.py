# src/api/main.py
import json
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
import pandas as pd
from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer
from src.consent.manager import give_consent, revoke_consent, get_consent, list_consents

app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()

RAW_DATA_PATH = "data/raw/patients_raw.csv"

audit_logger = logging.getLogger("medviet.audit")
logging.basicConfig(
    filename="reports/audit.log",
    level=logging.INFO,
    format="%(message)s"
)


@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    response = await call_next(request)
    audit_logger.info(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": request.method,
        "path": request.url.path,
        "user": request.headers.get("Authorization", "anonymous"),
        "status_code": response.status_code,
        "ip": request.client.host if request.client else "unknown",
    }))
    return response


@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(
    current_user: dict = Depends(get_current_user)
):
    df = pd.read_csv(RAW_DATA_PATH)
    return JSONResponse(content=df.head(10).to_dict(orient="records"))


@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(
    current_user: dict = Depends(get_current_user)
):
    df = pd.read_csv(RAW_DATA_PATH)
    df_anon = anonymizer.anonymize_dataframe(df.head(10))
    return JSONResponse(content=df_anon.to_dict(orient="records"))


@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(
    current_user: dict = Depends(get_current_user)
):
    df = pd.read_csv(RAW_DATA_PATH)
    counts = df["benh"].value_counts().to_dict()
    avg_result = round(df["ket_qua_xet_nghiem"].mean(), 2)
    return JSONResponse(content={
        "total_patients": len(df),
        "by_disease": counts,
        "avg_test_result": avg_result,
    })


@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    df = pd.read_csv(RAW_DATA_PATH)
    if patient_id not in df["patient_id"].values:
        raise HTTPException(status_code=404, detail="Patient not found")
    df = df[df["patient_id"] != patient_id]
    df.to_csv(RAW_DATA_PATH, index=False)
    return {"message": f"Patient {patient_id} deleted", "deleted_by": current_user["username"]}


# --- CONSENT ENDPOINTS (NĐ13 - Explicit Consent) ---

@app.post("/api/consent/{patient_id}")
@require_permission(resource="patient_data", action="write")
async def record_consent(
    patient_id: str,
    purpose: str = "ai_training",
    current_user: dict = Depends(get_current_user)
):
    """Thu thập consent của bệnh nhân. Lưu với timestamp theo NĐ13."""
    df = pd.read_csv(RAW_DATA_PATH)
    if patient_id not in df["patient_id"].values:
        raise HTTPException(status_code=404, detail="Patient not found")
    record = give_consent(patient_id, purpose=purpose, given_by=current_user["username"])
    return {"message": "Consent recorded", "consent": record}


@app.delete("/api/consent/{patient_id}")
async def revoke_patient_consent(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Rút consent (Right to Erasure). Bất kỳ user nào cũng có thể rút consent của mình."""
    record = revoke_consent(patient_id, revoked_by=current_user["username"])
    if record is None:
        raise HTTPException(status_code=404, detail="No consent record found for this patient")
    return {"message": "Consent revoked", "consent": record}


@app.get("/api/consent/{patient_id}")
@require_permission(resource="patient_data", action="read")
async def check_consent(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Kiểm tra trạng thái consent của bệnh nhân."""
    record = get_consent(patient_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No consent record found")
    return record


@app.get("/api/consent")
@require_permission(resource="patient_data", action="read")
async def list_all_consents(
    current_user: dict = Depends(get_current_user)
):
    """Liệt kê tất cả consent records (dùng cho compliance audit)."""
    return {"consents": list_consents(), "total": len(list_consents())}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API", "dpo_contact": "dpo@medviet.vn"}
