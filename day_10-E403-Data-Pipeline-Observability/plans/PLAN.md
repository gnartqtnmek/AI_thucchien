# Kế hoạch: Lab 10 - Xây dựng Pipeline ETL

## Tóm tắt ngắn gọn

Lab 10 yêu cầu xây dựng một pipeline ETL sản xuất với các kiểm soát chất lượng dữ liệu xung quanh hệ thống RAG hiện có. Công việc bao gồm xử lý CSV lỗi, áp dụng các quy tắc làm sạch và kỳ vọng, nhúng dữ liệu vào vector DB, kiểm tra độ mới dữ liệu, và chứng minh tác động qua các kiểm tra trước/sau khi tiêm lỗi. 

**Thời gian:** 4 sprint × 60 phút, hoàn thành báo cáo và tài liệu cuối ngày.

---

## Các giai đoạn chính

### Giai đoạn 1: Khám phá & Hiểu dữ liệu (Sprint 1)
- Phân tích dữ liệu thô (`policy_export_dirty.csv`) và ghi nhận các lỗi phổ biến.
- Đọc và hiểu các quy tắc làm sạch và kỳ vọng hiện tại.
- Tạo hợp đồng dữ liệu (`data_contract.yaml`) với SLA, nguồn dữ liệu, schema, và quy tắc quarantine.

### Giai đoạn 2: Thiết kế quy tắc & kỳ vọng mới (Sprint 2)
- Thêm ≥3 quy tắc làm sạch mới vào `transform/cleaning_rules.py`.
- Thêm ≥2 kỳ vọng mới vào `quality/expectations.py`.
- Đảm bảo mỗi quy tắc và kỳ vọng có đo lường tác động rõ ràng.

### Giai đoạn 3: Kiểm tra tiêm lỗi & Đánh giá trước/sau (Sprint 3)
- Tạo các kịch bản lỗi (bỏ qua quy tắc, thêm dữ liệu lỗi).
- Đánh giá chất lượng truy xuất trước/sau qua `eval_retrieval.py`.

### Giai đoạn 4: Tài liệu & Báo cáo (Sprint 4)
- Viết tài liệu kiến trúc pipeline (`pipeline_architecture.md`), hợp đồng dữ liệu, và runbook.
- Hoàn thành báo cáo nhóm (600–1000 từ) và cá nhân (400–650 từ).

### Giai đoạn 5: Chấm điểm & Nộp bài (Sprint 5)
- Chạy pipeline lần cuối, đảm bảo không lỗi.
- Nộp tất cả file cần thiết (code, log, báo cáo, JSONL chấm điểm).

---

## Phân công công việc cho nhóm 4 người

### Thành viên 1: Phân tích dữ liệu & Hợp đồng dữ liệu
- **Nhiệm vụ:**
  - Phân tích dữ liệu thô (`policy_export_dirty.csv`), ghi lại các lỗi phổ biến.
  - Tạo file `data_contract.yaml` với SLA, schema, và quy tắc quarantine.
- **Kết quả:**
  - File `data_contract.yaml` hoàn chỉnh, không lỗi.
  - Báo cáo các lỗi dữ liệu và cách xử lý.

### Thành viên 2: Thiết kế quy tắc làm sạch
- **Nhiệm vụ:**
  - Thêm ≥3 quy tắc mới vào `transform/cleaning_rules.py`.
  - Đảm bảo mỗi quy tắc có docstring và đo lường tác động (quarantine/cleaned).
- **Kết quả:**
  - File `cleaning_rules.py` với ≥3 quy tắc mới.
  - Bảng `metric_impact` chứng minh hiệu quả.

### Thành viên 3: Thiết kế kỳ vọng & Kiểm tra
- **Nhiệm vụ:**
  - Thêm ≥2 kỳ vọng mới vào `quality/expectations.py`.
  - Tạo kịch bản tiêm lỗi và chạy kiểm tra pipeline.
- **Kết quả:**
  - File `expectations.py` với ≥2 kỳ vọng mới.
  - Báo cáo pass/fail cho từng kỳ vọng.

### Thành viên 4: Tài liệu & Báo cáo
- **Nhiệm vụ:**
  - Viết tài liệu kiến trúc (`pipeline_architecture.md`), runbook, và báo cáo nhóm.
  - Tổng hợp kết quả từ các thành viên khác.
- **Kết quả:**
  - Báo cáo nhóm (600–1000 từ) và cá nhân (400–650 từ).
  - Tài liệu đầy đủ, dễ hiểu.

---

## Checklist kiểm tra

### Phải hoàn thành (Cơ bản):
- [ ] Pipeline chạy không lỗi (`python etl_pipeline.py run`).
- [ ] File `data_contract.yaml` hợp lệ.
- [ ] Tài liệu (`pipeline_architecture.md`, `runbook.md`) đầy đủ.
- [ ] Báo cáo nhóm và cá nhân đúng yêu cầu.

### Kiểm tra nâng cao (Chống trivial):
- [ ] Quy tắc mới có đo lường tác động rõ ràng.
- [ ] Kỳ vọng mới có logic và kết quả pass/fail.
- [ ] Đánh giá trước/sau chứng minh chất lượng cải thiện.

---

### Quy trình làm việc qua GitHub

#### Quy trình nhóm:
1. Mỗi thành viên tạo nhánh riêng cho công việc của mình theo định dạng `feature/<task>`.
2. Commit code thường xuyên với thông điệp rõ ràng.
3. Mở pull request (PR) để yêu cầu review từ các thành viên khác.
4. Thành viên khác review PR, đảm bảo code đạt yêu cầu trước khi merge vào nhánh `main`.

#### Lệnh Git cụ thể:
```bash
# Tạo nhánh mới
git checkout -b feature/<task>

# Commit code
git add .
git commit -m "Thêm <mô tả công việc>"

# Push nhánh lên GitHub
git push origin feature/<task>

# Mở PR trên GitHub
```

---

### Lệnh chạy pipeline và kiểm tra

#### Chạy pipeline:
```bash
python etl_pipeline.py run
```

#### Kiểm tra kỳ vọng:
```bash
python eval_retrieval.py
```

#### Kiểm tra độ mới dữ liệu:
```bash
python monitoring/freshness_check.py
```

---

Nếu cần chỉnh sửa thêm, hãy cho tôi biết!
