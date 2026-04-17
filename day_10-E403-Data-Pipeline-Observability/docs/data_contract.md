# Data contract — Lab Day 10

> Đồng bộ với `contracts/data_contract.yaml` — mọi thay đổi schema/rule phải cập nhật cả hai file.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/docs/policy_refund_v4.txt` | CSV export từ hệ thống nội bộ | Chunk lẫn nội dung policy-v3 cũ (14 ngày thay vì 7 ngày) do lỗi migration | `quarantine_records` tăng khi rule `no_stale_refund_window` kích hoạt |
| `data/docs/sla_p1_2026.txt` | CSV export từ hệ thống nội bộ | Thiếu `effective_date` hoặc ngày không thuộc năm 2026 | `quarantine_records` tăng khi rule `invalid_date` kích hoạt |
| `data/docs/it_helpdesk_faq.txt` | CSV export từ hệ thống nội bộ | `effective_date` sai định dạng (DD/MM/YYYY thay vì YYYY-MM-DD) | `quarantine_records` tăng khi rule `date_format_normalize` kích hoạt |
| `data/docs/hr_leave_policy.txt` | CSV export từ hệ thống nội bộ | Xung đột version: bản HR 2025 (10 ngày) lẫn với bản 2026 (12 ngày) | `quarantine_records` tăng khi rule `hr_leave_version` kích hoạt |
| `data/docs/access_control_sop.txt` | CSV export từ hệ thống nội bộ | Chunk rỗng hoặc thiếu metadata | `quarantine_records` tăng khi rule `empty_chunk` kích hoạt |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| `chunk_id` | string | Có | ID duy nhất, dùng để upsert idempotent vào Chroma — không được trùng |
| `doc_id` | string | Có | Phải thuộc `allowed_doc_ids` trong `data_contract.yaml` |
| `chunk_text` | string | Có | Độ dài 10–5000 ký tự, không được rỗng |
| `effective_date` | date | Có | Định dạng ISO 8601 (`YYYY-MM-DD`), khoảng 2024-01-01 đến 2027-12-31 |
| `exported_at` | datetime | Có | Định dạng ISO 8601 (`YYYY-MM-DDTHH:MM:SS`) |

---

## 3. Quy tắc quarantine vs drop

**Record bị flag sẽ đi vào `artifacts/quarantine/quarantine_<run_id>.csv`** — không bị xóa hoàn toàn, giữ lại để audit.

| Loại lỗi | Hành động | Mức độ | Ai approve merge lại? |
|----------|-----------|--------|----------------------|
| `chunk_text` rỗng | quarantine | **halt** — dừng pipeline | Không merge, loại vĩnh viễn |
| `doc_id` ngoài allowlist | quarantine | **halt** — dừng pipeline | Cleaning Owner review, thêm vào allowlist nếu hợp lệ |
| Nội dung refund 14 ngày (stale) | fix hoặc quarantine | **halt** — dừng pipeline | Ingestion Owner fix lại text nguồn rồi re-ingest |
| Duplicate `chunk_text` | quarantine (giữ 1) | warn — chạy tiếp | Không cần approve, tự động dedupe |
| HR leave policy version cũ (< 2026-01-01) | quarantine | warn — chạy tiếp | Không merge, bản cũ đã lỗi thời |
| `effective_date` sai định dạng | normalize tự động | warn — chạy tiếp | Không cần approve, pipeline tự sửa |

> **Quy tắc chung:** lỗi `halt` phải được fix tại nguồn trước khi re-ingest. Lỗi `warn` pipeline tự xử lý và ghi log.

---

## 4. Phiên bản & canonical

**Source of truth cho policy refund:** `data/docs/policy_refund_v4.txt`
- Cửa sổ hoàn tiền đúng: **7 ngày làm việc**
- Bất kỳ chunk nào chứa "14 ngày" trong context hoàn tiền đều là lỗi migration từ policy-v3 → bị halt

**Source of truth cho HR leave policy:** `data/docs/hr_leave_policy.txt`
- Phiên bản hợp lệ: `effective_date >= 2026-01-01` (12 ngày phép cho nhân viên < 3 năm)
- Bản cũ 2025 (10 ngày) → quarantine
- Cutoff date đọc từ `policy_versioning.hr_leave_min_effective_date` trong `data_contract.yaml` — không hard-code trong code

**Allowlist doc_id hợp lệ:**
```
policy_refund_v4 | sla_p1_2026 | it_helpdesk_faq | hr_leave_policy | access_control_sop
```
Doc mới muốn thêm vào phải cập nhật đồng thời: `data_contract.yaml` → `allowed_doc_ids` và `transform/cleaning_rules.py` → allowlist.
