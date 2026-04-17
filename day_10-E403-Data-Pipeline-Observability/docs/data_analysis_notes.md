# Ghi nhận lỗi dữ liệu — policy_export_dirty.csv

**Người phân tích:** Nguyễn Quang Tùng - 2A202600197 
**Ngày phân tích:** 2026-04-15  
**File nguồn:** `data/raw/policy_export_dirty.csv`  
**Tổng số dòng dữ liệu:** 10 records

---

## Tổng quan các cột

| Cột | Kiểu mong đợi | Ghi chú |
|-----|---------------|---------|
| `chunk_id` | integer, unique | Định danh chunk |
| `doc_id` | string, allowlist | Phải thuộc danh sách doc hợp lệ |
| `chunk_text` | string, non-empty | Nội dung chunk |
| `effective_date` | date ISO 8601 (YYYY-MM-DD) | Ngày hiệu lực |
| `exported_at` | datetime ISO 8601 | Thời điểm export |

---

## Các lỗi phát hiện

### 1. Duplicate chunk (chunk_id 1 & 2)
- **Dòng:** chunk_id = 1 và chunk_id = 2
- **Mô tả:** Hai dòng có `doc_id`, `chunk_text`, `effective_date`, `exported_at` hoàn toàn giống nhau — chỉ khác `chunk_id`.
- **Tác động:** Gây nhiễu khi embed vào vector DB, truy xuất trả về kết quả trùng lặp.
- **Xử lý:** Quarantine hoặc dedupe, giữ lại 1 dòng.

---

### 2. Nội dung chunk lỗi thời / sai version (chunk_id 3)
- **Dòng:** chunk_id = 3
- **Mô tả:** `chunk_text` ghi "14 ngày làm việc" — đây là nội dung từ policy-v3 cũ, bị migration nhầm. Bản đúng (v4) là 7 ngày (xem chunk_id 1).
- **Ghi chú trong data:** `"ghi chú: bản sync cũ policy-v3 — lỗi migration"`
- **Tác động:** Nếu được embed, agent sẽ trả lời sai cửa sổ hoàn tiền (14 ngày thay vì 7 ngày).
- **Xử lý:** Fix text về "7 ngày" hoặc quarantine, không được embed chunk này.

---

### 3. Chunk rỗng — thiếu `chunk_text` và `effective_date` (chunk_id 5)
- **Dòng:** chunk_id = 5
- **Mô tả:** `chunk_text` = rỗng (`""`), `effective_date` = null/trống.
- **Tác động:** Chunk vô nghĩa, không thể embed, gây lỗi pipeline nếu không lọc.
- **Xử lý:** Quarantine ngay, không xử lý tiếp.

---

### 4. doc_id không hợp lệ / ngoài allowlist (chunk_id 9)
- **Dòng:** chunk_id = 9
- **Mô tả:** `doc_id = "legacy_catalog_xyz_zzz"` — không thuộc danh sách doc hợp lệ của hệ thống (allowlist gồm: `policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`, `access_control_sop`).
- **Tác động:** Chunk từ nguồn không xác định, có thể chứa thông tin lỗi thời hoặc không liên quan.
- **Xử lý:** Quarantine, không embed.

---

### 5. Xung đột version nội dung — HR leave policy (chunk_id 7 & 8)
- **Dòng:** chunk_id = 7 và chunk_id = 8
- **Mô tả:** Hai chunk cùng nói về số ngày phép nhân viên dưới 3 năm nhưng mâu thuẫn nhau:
  - chunk_id 7: "10 ngày phép" — `effective_date = 2025-01-01` (bản HR 2025 cũ)
  - chunk_id 8: "12 ngày phép" — `effective_date = 2026-02-01` (bản 2026 mới)
- **Tác động:** Nếu cả hai được embed, agent có thể trả lời sai số ngày phép tùy chunk nào được retrieve.
- **Xử lý:** Giữ bản mới nhất (chunk_id 8, effective_date 2026), quarantine chunk_id 7.

---

### 6. Định dạng `effective_date` không chuẩn ISO 8601 (chunk_id 10)
- **Dòng:** chunk_id = 10
- **Mô tả:** `effective_date = "01/02/2026"` — dùng định dạng DD/MM/YYYY thay vì YYYY-MM-DD.
- **Tác động:** Pipeline parse ngày sẽ lỗi hoặc hiểu sai (có thể bị đọc thành ngày 2 tháng 1 thay vì ngày 1 tháng 2).
- **Xử lý:** Chuẩn hóa về `2026-02-01` trước khi xử lý tiếp.

---

## Tổng hợp

| chunk_id | Lỗi | Hành động đề xuất |
|----------|-----|-------------------|
| 1, 2 | Duplicate | Dedupe — giữ 1 |
| 3 | Nội dung sai version (14 ngày → 7 ngày) | Fix hoặc quarantine |
| 5 | chunk_text rỗng, thiếu effective_date | Quarantine |
| 7 | HR policy cũ (2025), xung đột với chunk_id 8 | Quarantine |
| 9 | doc_id ngoài allowlist | Quarantine |
| 10 | effective_date sai định dạng (DD/MM/YYYY) | Chuẩn hóa → `2026-02-01` |

**Dự kiến sau cleaning:**
- Records đưa vào cleaned: ~4–5 dòng
- Records quarantine: ~5–6 dòng

---

## Ghi chú thêm

- File có 10 records, sau khi loại bỏ lỗi chỉ còn khoảng 4 chunk sạch đủ điều kiện embed.
- Lỗi nghiêm trọng nhất là chunk_id 3 (sai cửa sổ hoàn tiền) và chunk_id 7 (HR policy cũ) — nếu lọt qua sẽ ảnh hưởng trực tiếp đến câu trả lời của agent.
