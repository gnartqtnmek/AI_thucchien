# Kế hoạch cá nhân: Thành viên 3 - Thiết kế kỳ vọng & Kiểm tra

## Công việc cần làm

### Trước khi bắt đầu:
1. **Cài đặt môi trường làm việc:**
   - Đảm bảo Python và các thư viện cần thiết đã được cài đặt (xem `requirements.txt`).
   - Clone repository từ GitHub về máy cá nhân.
   - Tạo nhánh làm việc riêng, đặt tên theo định dạng `member3/expectations-testing`.

2. **Hiểu yêu cầu:**
   - Đọc file `PLAN.md` để hiểu tổng quan kế hoạch.
   - Đọc file `quality/expectations.py` để hiểu các kỳ vọng hiện tại.

### Công việc chính:
1. **Thiết kế kỳ vọng mới:**
   - Thêm ít nhất 2 kỳ vọng mới vào `quality/expectations.py`. Ví dụ:
     - Kiểm tra độ dài chunk (10–5000 ký tự).
     - Đảm bảo metadata (doc_id, exported_at) không bị thiếu.
   - Viết docstring cho mỗi kỳ vọng, giải thích logic và quyết định halt/warn.

2. **Kiểm tra kỳ vọng:**
   - Chạy pipeline sau khi thêm từng kỳ vọng:
     ```bash
     python etl_pipeline.py run --run-id expectation_test
     ```
   - Ghi lại số lượng pass/fail cho từng kỳ vọng.
   - Cập nhật bảng `expectations_matrix` trong báo cáo nhóm.

3. **Tạo kịch bản tiêm lỗi:**
   - Tạo các kịch bản lỗi để kiểm tra kỳ vọng:
     - Thêm dữ liệu lỗi vào `data/raw/policy_export_dirty.csv`.
     - Chạy pipeline và ghi nhận kết quả.

### Sau khi hoàn thành:
1. Commit và push nhánh lên GitHub:
   ```bash
   git add quality/expectations.py data/raw/policy_export_dirty.csv
   git commit -m "[Member3] Thêm kỳ vọng mới và kiểm tra"
   git push origin member3/expectations-testing
   ```
2. Tạo pull request (PR) và gắn nhãn "Ready for Review".
3. Chờ nhóm review và chỉnh sửa nếu cần.

---

## Kết quả cần đạt được
- File `expectations.py` với ít nhất 2 kỳ vọng mới.
- Bảng `expectations_matrix` ghi lại kết quả pass/fail.
- PR được merge vào nhánh chính.