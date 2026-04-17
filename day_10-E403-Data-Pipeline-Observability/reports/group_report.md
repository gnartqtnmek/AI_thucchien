# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Nhóm 9 - E403  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Nguyễn Quang Tùng | Ingestion / Raw Owner | quangtungnguyen613@gmail.com |
| Đặng Văn Minh | Cleaning & Quality Owner | minhdv0201@gmail.com |
| Nguyễn Thị Quỳnh Trang | Embed & Idempotency Owner | quynhtrang1225@gmail.com |
| Đồng Văn Thịnh | Monitoring / Docs Owner | dvttvdthanhan@gmail.com |

**Ngày nộp:** 15/04/2026  
**Repo:** https://github.com/DangMinh21/Day10-E403-Data-Pipeline-Observability  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**
Pipeline vận hành theo mô hình Automated ETL với Data Observability, đóng vai trò là "lớp gác cổng" kiến thức cho Agent qua 4 giai đoạn:

1. **Ingest:** Trích xuất dữ liệu thô từ file `policy_export_dirty.csv`.

2. **Transform:** Chuẩn hóa định dạng và áp dụng logic nghiệp vụ (fix refund window).

3. **Quality Control:** Kiểm tra các kỳ vọng dữ liệu (expectations). Hệ thống tự động Halt (dừng) nếu phát hiện lỗi nghiêm trọng để bảo vệ Vector DB, hoặc đẩy bản ghi lỗi vào Quarantine.

4. **Embed & Manifest:** Thực hiện upsert dữ liệu sạch vào ChromaDB theo chunk_id để chống trùng lặp (Idempotency). Cuối cùng, tạo file Manifest ghi lại metadata và kiểm tra Freshness SLA.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

```
# Luồng chuẩn: fix stale refund 14→7, expectation pass, embed
python etl_pipeline.py run

# Kiểm tra freshness theo manifest vừa tạo
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json
```

---

## 2. Cleaning & expectation (150–200 từ)

Baseline đã có 6 expectations (E1-E6). Member 3 (Nguyễn Thị Quỳnh Trang) thêm 2 kỳ vọng mới:

**E7: Độ dài chunk_text (10-5000 ký tự)** - HALT  
Đảm bảo chunks không quá ngắn (< 10) hoặc quá dài (> 5000), phát hiện vấn đề chunking.

**E8: Tính đầy đủ metadata (doc_id, exported_at)** - HALT  
Kiểm tra mỗi record có doc_id và exported_at không rỗng, bảo vệ traceability và freshness check.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| E7: chunk_text_length_10_5000 | raw=10, cleaned=4 | inject errors: quarantine=5, cleaned=4 | artifacts/cleaned/*, artifacts/quarantine/* |
| E8: metadata_completeness | raw=10, cleaned=4 | inject errors: quarantine=5, cleaned=4 | artifacts/logs/run_*.log |
| **Cleaning rules baseline** | Allowlist (4 doc_ids), ISO format, HR stale, refund fix, dedupe | Loại bỏ doc_id lạ, invalid date, rỗng text, duplicates | quality/expectations.py, transform/cleaning_rules.py |

**Expectations chính (baseline + mở rộng):**

- E1: min_one_row (HALT)
- E2: no_empty_doc_id (HALT)
- E3: refund_no_stale_14d_window (HALT)
- E4: chunk_min_length_8 (WARN)
- E5: effective_date_iso_yyyy_mm_dd (HALT)
- E6: hr_leave_no_stale_10d_annual (HALT)
- **E7: chunk_text_length_10_5000 (HALT)** ✅ Mới
- **E8: metadata_completeness_doc_id_exported_at (HALT)** ✅ Mới

**Ví dụ expectation behavior:**

Run member3_baseline: raw_records=10 → cleaned=4, quarantine=4. Tất cả expectations PASS vì cleaning rules loại bad data trước. Run member3_error_test: thêm errors (doc_id rỗng, chunk quá dài/ngắn, exported_at rỗng) → và đều được quarantine, E7 & E8 vẫn PASS vì data có vấn đề không qua được cleaning.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

_________________

**Kết quả định lượng (từ CSV / bảng):**

_________________

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

_________________

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- …

## Metric Impact Table

| Rule Name                  | Total Rows | Cleaned Rows | Quarantined Rows | Notes                          |
|----------------------------|------------|--------------|------------------|--------------------------------|
| contains_sensitive_info    | 10         | 4            | 1                | Removed rows with sensitive info (e.g., URLs). |
| invalid_exported_at_format | 10         | 4            | 4                | Quarantined rows with invalid or out-of-range exported_at dates. |
| duplicate_doc_id           | 10         | 4            | 0                | No duplicates found in this dataset. |
