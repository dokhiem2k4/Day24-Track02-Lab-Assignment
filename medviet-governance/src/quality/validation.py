# src/quality/validation.py
import re
import pandas as pd


def build_patient_expectation_suite() -> dict:
    """Tạo expectation suite cho patient data, trả về dict mô tả các rules."""
    df = pd.read_csv("data/raw/patients_raw.csv")
    suite = {}

    # 1. patient_id không được null
    suite["patient_id_not_null"] = df["patient_id"].notna().all()

    # 2. cccd phải có đúng 12 ký tự
    suite["cccd_length_12"] = df["cccd"].astype(str).str.len().eq(12).all()

    # 3. ket_qua_xet_nghiem trong khoảng [0, 50]
    suite["result_in_range"] = df["ket_qua_xet_nghiem"].between(0, 50).all()

    # 4. benh thuộc danh sách hợp lệ
    valid_conditions = ["Tiểu đường", "Huyết áp cao", "Tim mạch", "Khỏe mạnh"]
    suite["disease_valid"] = df["benh"].isin(valid_conditions).all()

    # 5. email match regex
    email_regex = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
    suite["email_format"] = df["email"].astype(str).str.match(email_regex).all()

    # 6. patient_id unique
    suite["patient_id_unique"] = df["patient_id"].is_unique

    return suite


def validate_anonymized_data(filepath: str, original_filepath: str = "data/raw/patients_raw.csv") -> dict:
    """Validate anonymized data. Trả về {"success": bool, "failed_checks": list, "stats": dict}"""
    df = pd.read_csv(filepath)
    original_df = pd.read_csv(original_filepath)

    results = {
        "success": True,
        "failed_checks": [],
        "stats": {
            "total_rows": len(df),
            "columns": list(df.columns)
        }
    }

    # Check 1: CCCD trong anonymized file phải là 12 chữ số (fake) — không trùng CCCD gốc
    original_cccds = set(original_df["cccd"].astype(str).tolist())
    anon_cccds = set(df["cccd"].astype(str).tolist())
    overlap = original_cccds & anon_cccds
    if overlap:
        results["success"] = False
        results["failed_checks"].append(f"CCCD overlap found: {len(overlap)} original CCCDs still present")

    # Check 2: Không có null values trong các cột quan trọng
    required_cols = ["patient_id", "benh", "ket_qua_xet_nghiem"]
    for col in required_cols:
        if col in df.columns and df[col].isna().any():
            results["success"] = False
            results["failed_checks"].append(f"Null values found in column: {col}")

    # Check 3: Số rows phải bằng original
    if len(df) != len(original_df):
        results["success"] = False
        results["failed_checks"].append(
            f"Row count mismatch: anonymized={len(df)}, original={len(original_df)}"
        )

    return results
