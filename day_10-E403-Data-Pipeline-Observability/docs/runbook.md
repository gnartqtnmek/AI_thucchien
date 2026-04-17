# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

> User / agent thấy gì? (VD: trả lời “14 ngày” thay vì 7 ngày)

---

## Detection

> Metric nào báo? (freshness, expectation fail, eval `hits_forbidden`)

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | … |
| 2 | Mở `artifacts/quarantine/*.csv` | … |
| 3 | Chạy `python eval_retrieval.py` | … |

---

## Mitigation

> Rerun pipeline, rollback embed, tạm banner “data stale”, …

- **Rerun Pipeline:** Chạy lại toàn bộ luồng ETL với run-id mới để ép hệ thống cập nhật.

- **Manual Clear:** Xóa thư mục lưu trữ chroma_db cũ để hệ thống khởi tạo lại từ đầu (nếu cơ chế Upsert lỗi).

- **Maintenance Mode:** Tạm thời cấu hình Agent trả lời: "Hệ thống đang cập nhật dữ liệu, vui lòng quay lại sau."

---

## Prevention

> Thêm expectation, alert, owner — nối sang Day 11 nếu có guardrail.

- **Tighten Expectations:** Thêm quy tắc chặn các giá trị giá (price) phi lý ngay từ tầng expectations.py.

- **Auto-Alert:** Cài đặt bot thông báo nếu file Quarantine vượt quá một dung lượng nhất định.

- **Guardrail (Day 11):** Nối sang Day 11 bằng cách cài đặt bộ lọc đầu ra (Output Filter) để chặn Agent phát ngôn khi độ tin cậy của tài liệu nguồn (confidence score) quá thấp.
