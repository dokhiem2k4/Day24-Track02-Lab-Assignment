# NĐ13/2023 Compliance Checklist — MedViet AI Platform

## A. Data Localization
- [ ] Tất cả patient data lưu trên servers đặt tại Việt Nam *(infrastructure — cần deploy production tại VN datacenter)*
- [ ] Backup cũng phải ở trong lãnh thổ VN *(infrastructure — cần config backup policy)*
- [x] Log việc transfer data ra ngoài nếu có — audit middleware ghi log mọi API call (`reports/audit.log`)

## B. Explicit Consent
- [x] Thu thập consent trước khi dùng data cho AI training — `POST /api/consent/{patient_id}` (`src/consent/manager.py`)
- [x] Có mechanism để user rút consent (Right to Erasure) — `DELETE /api/consent/{patient_id}` tự phục vụ
- [x] Lưu consent record với timestamp — `data/consents.json` ghi `given_at`, `revoked_at`, `given_by`

## C. Breach Notification (72h)
- [x] Có incident response plan — xem Section F.2 (4 giai đoạn 0–72h)
- [x] Alert tự động khi phát hiện breach — Prometheus alert rules (`prometheus/alert_rules.yml`)
- [ ] Quy trình báo cáo chính thức đến Bộ TT&TT trong 72h *(cần bổ sung quy trình hành chính + liên hệ cơ quan)*

## D. DPO Appointment
- [ ] Đã bổ nhiệm Data Protection Officer *(cần quyết định nhân sự)*
- [x] DPO có thể liên hệ tại: dpo@medviet.vn — hiển thị trong `GET /health`

## E. Technical Controls (mapping từ requirements)
| NĐ13 Requirement | Technical Control | Status | Owner |
|-----------------|-------------------|--------|-------|
| Data minimization | PII anonymization pipeline (Presidio) | ✅ Done | AI Team |
| Access control | RBAC (Casbin) + ABAC (OPA) | ✅ Done | Platform Team |
| Encryption | AES-256-GCM at rest (`src/encryption/vault.py`), TLS 1.3 in transit | ✅ Done (local) / 🚧 TLS cần infra | Infra Team |
| Audit logging | FastAPI middleware → `reports/audit.log` (JSON structured) | ✅ Done | Platform Team |
| Breach detection | Prometheus alert rules (`prometheus/alert_rules.yml`) + AlertManager | ✅ Done | Security Team |
| Explicit consent | Consent API (`src/consent/manager.py`) + Right to Erasure | ✅ Done | Platform Team |

## F. Technical Solutions

### 1. Audit Logging

**Đã implement** trong `src/api/main.py` — FastAPI middleware ghi mọi request thành JSON:

```python
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    response = await call_next(request)
    audit_logger.info(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": request.method,
        "path": request.url.path,
        "user": request.headers.get("Authorization", "anonymous"),
        "status_code": response.status_code,
        "ip": request.client.host,
    }))
    return response
```

**Storage:** File JSON → ship lên ELK Stack (Elasticsearch + Logstash + Kibana) deploy tại VN.

**Retention:** Giữ audit log tối thiểu 2 năm theo NĐ13.

---

### 2. Breach Detection

**Đã implement** trong `prometheus/alert_rules.yml` — 4 alert rules:

| Alert | Trigger | Severity |
|-------|---------|----------|
| `SuspiciousAccessAttempts` | > 10 lần 403 từ cùng IP trong 5 phút | Warning |
| `BulkDataExport` | > 1000 records trả về trong 10 phút | Critical |
| `MultipleAuthFailures` | > 5 lần 401 trong 5 phút | Warning |
| `HighAPILatency` | P99 latency > 5s trong 5 phút | Warning |

**Notification flow:**
```
Anomaly → Prometheus → AlertManager → PagerDuty/Slack → Security Team
                                                          ↓ (confirmed breach)
                                                    DPO notified → Báo Bộ TT&TT trong 72h
```

**Incident Response Plan:**
1. **0–4h:** Phát hiện, isolate affected systems, preserve evidence
2. **4–24h:** Root cause analysis, scope assessment
3. **24–48h:** Containment, notify affected users
4. **48–72h:** Formal report gửi Bộ TT&TT theo Điều 24 NĐ13

---

### 3. Explicit Consent (Right to Erasure)

**Đã implement** trong `src/consent/manager.py` + `src/api/main.py`:

| Endpoint | Mục đích |
|----------|---------|
| `POST /api/consent/{patient_id}` | Thu thập consent, lưu timestamp |
| `DELETE /api/consent/{patient_id}` | Rút consent (Right to Erasure) |
| `GET /api/consent/{patient_id}` | Kiểm tra trạng thái consent |
| `GET /api/consent` | Liệt kê tất cả consent (audit) |

**Storage:** `data/consents.json` — mỗi record ghi `given_at`, `revoked_at`, `given_by`, `purpose`.

---

### 4. Data Localization (Còn Thiếu — Infrastructure)

Cần thực hiện khi deploy production:

1. **Cloud Provider:** Chọn provider có datacenter tại VN (Viettel IDC, VNPT IDC, hoặc AWS ap-southeast-1 Singapore với data residency policy)
2. **Backup Policy:** Configure automated backup đến VN region, retention ≥ 90 ngày
3. **Data Transfer Logging:** Audit log đã bắt mọi API call — cần thêm alert nếu destination IP nằm ngoài VN subnet
4. **Compliance Attestation:** Ký SLA với cloud provider về data residency

---

### 5. DPO & Breach Reporting Process (Còn Thiếu — Hành Chính)

1. **DPO:** Bổ nhiệm DPO chính thức, đăng ký với Bộ TT&TT
2. **Liên hệ DPO:** dpo@medviet.vn (hiện tại là placeholder)
3. **Báo cáo breach:** Theo Điều 24 NĐ13 — điền mẫu báo cáo gửi Cục An toàn thông tin trong 72h kể từ khi phát hiện
