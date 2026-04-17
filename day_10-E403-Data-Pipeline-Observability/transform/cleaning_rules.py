"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")

# Define ISO 8601 datetime regex pattern
_ISO_DATETIME = re.compile(r"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}$")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Normalize effective_date to ISO 8601 format (YYYY-MM-DD).

    Args:
        raw (str): The raw effective_date string.

    Returns:
        Tuple[str, str]: A tuple containing the normalized date and an error reason if invalid.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _contains_sensitive_info(text: str) -> bool:
    """
    Check if the given text contains sensitive information such as URLs.

    Args:
        text (str): The text to check.

    Returns:
        bool: True if sensitive information is found, False otherwise.
    """
    return bool(re.search(r"https?://|www\\.", text))


def _validate_exported_at(date: str) -> Tuple[bool, str]:
    """
    Validate the `exported_at` field to ensure it is in ISO 8601 format and within the range 2024-2027.

    Args:
        date (str): The exported_at date string to validate.

    Returns:
        Tuple[bool, str]: A tuple where the first element indicates validity and the second provides an error reason if invalid.
    """
    try:
        # Parse the date to ensure it matches ISO 8601 format
        parsed_date = datetime.fromisoformat(date)
        date_only = parsed_date.date().isoformat()  # Extract YYYY-MM-DD part
        if not ("2024-01-01" <= date_only <= "2027-12-31"):
            return False, "exported_at_out_of_range"
    except ValueError:
        return False, "invalid_exported_at_format"
    return True, ""


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        # Rule 1: Check for sensitive information
        if _contains_sensitive_info(raw.get("chunk_text", "")):
            quarantine.append({**raw, "reason": "contains_sensitive_info"})
            continue

        # Rule 2: Validate exported_at
        exported_at = raw.get("exported_at", "")
        valid_exported_at, exported_at_reason = _validate_exported_at(exported_at)
        if not valid_exported_at:
            quarantine.append({**raw, "reason": exported_at_reason})
            continue

        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        key = _norm_text(text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        fixed_text = text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at or "",
            }
        )

    # Rule 3: Deduplicate doc_id within the same day
    cleaned = _deduplicate_doc_id(cleaned)

    return cleaned, quarantine


def _deduplicate_doc_id(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Remove duplicate records with the same `doc_id` within the same day.

    Args:
        rows (List[Dict[str, str]]): The list of data rows to process.

    Returns:
        List[Dict[str, str]]: A list of unique rows with duplicates removed.
    """
    seen_doc_ids = set()
    unique_rows = []
    for row in rows:
        key = (row.get("doc_id"), row.get("exported_at", "")[:10])
        if key in seen_doc_ids:
            continue
        seen_doc_ids.add(key)
        unique_rows.append(row)
    return unique_rows


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    # Sample data for testing
    sample_rows = [
        {"doc_id": "policy_refund_v4", "chunk_text": "Visit https://example.com for details", "effective_date": "2026-05-01", "exported_at": "2026-05-01T12:00:00"},
        {"doc_id": "sla_p1_2026", "chunk_text": "Valid chunk", "effective_date": "2026-01-15", "exported_at": "2026-01-15T08:00:00"},
        {"doc_id": "sla_p1_2026", "chunk_text": "Duplicate chunk", "effective_date": "2026-01-15", "exported_at": "2026-01-15T08:00:00"},
        {"doc_id": "hr_leave_policy", "chunk_text": "", "effective_date": "2025-12-31", "exported_at": "2026-01-01T00:00:00"},
        {"doc_id": "policy_refund_v4", "chunk_text": "Valid chunk", "effective_date": "2026-05-01", "exported_at": "invalid-date"},
    ]

    # Test the cleaning rules
    cleaned, quarantine = clean_rows(sample_rows)

    # Measure impact
    print("\nImpact Measurement:")
    print(f"Total rows processed: {len(sample_rows)}")
    print(f"Cleaned rows: {len(cleaned)}")
    print(f"Quarantined rows: {len(quarantine)}")

    print("\nCleaned Rows:")
    for row in cleaned:
        print(row)

    print("\nQuarantine Rows:")
    for row in quarantine:
        print(row)
