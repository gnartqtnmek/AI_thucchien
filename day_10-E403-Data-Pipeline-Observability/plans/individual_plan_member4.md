# Kế hoạch cá nhân: Thành viên 4 - Tài liệu & Báo cáo

## Công việc cần làm

### Trước khi bắt đầu:
1. **Cài đặt môi trường làm việc:**
   - Đảm bảo Python và các thư viện cần thiết đã được cài đặt (xem `requirements.txt`).
   - Clone repository từ GitHub về máy cá nhân.
   - Tạo nhánh làm việc riêng, đặt tên theo định dạng `member4/documentation-report`.

2. **Hiểu yêu cầu:**
   - Đọc file `PLAN.md` để hiểu tổng quan kế hoạch.
   - Xem các file mẫu trong thư mục `docs/` và `reports/`.

### Công việc chính:
1. **Viết tài liệu kiến trúc:**
   - Hoàn thành file `docs/pipeline_architecture.md` với các nội dung:
     - Sơ đồ pipeline (Mermaid hoặc ASCII).
     - Bảng phân công trách nhiệm (owner table).
     - Chiến lược idempotency và xử lý lỗi.

2. **Viết runbook:**
   - Hoàn thành file `docs/runbook.md` với 5 phần:
     - **Triệu chứng:** Mô tả lỗi cụ thể.
     - **Phát hiện:** Cách phát hiện lỗi qua log hoặc metric.
     - **Chẩn đoán:** Các bước kiểm tra nguyên nhân.
     - **Khắc phục:** Hành động sửa lỗi ngay lập tức.
     - **Phòng ngừa:** Cải tiến để tránh lỗi trong tương lai.

3. **Viết báo cáo nhóm:**
   - Hoàn thành file `reports/group_report.md` (600–1000 từ) với các phần:
     - Tổng quan pipeline.
     - Quy tắc làm sạch và tác động.
     - Chiến lược kỳ vọng (halt/warn).
     - Đánh giá trước/sau khi tiêm lỗi.
     - Kiểm tra độ mới và quan sát.
     - Kết quả học tập và bước tiếp theo.

4. **Hỗ trợ báo cáo cá nhân:**
   - Hướng dẫn các thành viên khác viết báo cáo cá nhân (400–650 từ).

### Sau khi hoàn thành:
1. Commit và push nhánh lên GitHub:
   ```bash
   git add docs/pipeline_architecture.md docs/runbook.md reports/group_report.md
   git commit -m "[Member4] Hoàn thành tài liệu và báo cáo nhóm"
   git push origin member4/documentation-report
   ```
2. Tạo pull request (PR) và gắn nhãn "Ready for Review".
3. Chờ nhóm review và chỉnh sửa nếu cần.

---

## Kết quả cần đạt được
- File `pipeline_architecture.md` và `runbook.md` hoàn chỉnh.
- Báo cáo nhóm (600–1000 từ) đầy đủ và đúng yêu cầu.
- PR được merge vào nhánh chính.