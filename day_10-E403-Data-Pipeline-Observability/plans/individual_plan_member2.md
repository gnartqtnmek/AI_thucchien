# Kế hoạch cá nhân: Thành viên 2 - Thiết kế quy tắc làm sạch

## Công việc cần làm

### Trước khi bắt đầu:
1. **Cài đặt môi trường làm việc:**
   - Đảm bảo Python và các thư viện cần thiết đã được cài đặt (xem `requirements.txt`).
   - Clone repository từ GitHub về máy cá nhân.
   - Tạo nhánh làm việc riêng, đặt tên theo định dạng `member2/cleaning-rules`.

2. **Hiểu yêu cầu:**
   - Đọc file `PLAN.md` để hiểu tổng quan kế hoạch.
   - Đọc file `transform/cleaning_rules.py` để hiểu các quy tắc hiện tại.

### Công việc chính:
1. **Thiết kế quy tắc mới:**
   - Thêm ít nhất 3 quy tắc làm sạch mới vào `transform/cleaning_rules.py`. Ví dụ:
     - Loại bỏ BOM/encoding không hợp lệ.
     - Kiểm tra ngày hợp lệ (ngày hiệu lực phải trong khoảng 2024–2027).
     - Loại bỏ các chunk chứa URL/API hoặc thông tin nhạy cảm.
   - Viết docstring cho mỗi quy tắc, giải thích mục đích và tác động.

2. **Kiểm tra quy tắc:**
   - Chạy pipeline sau khi thêm từng quy tắc:
     ```bash
     python etl_pipeline.py run --run-id rule_test
     ```
   - Ghi lại số lượng bản ghi được làm sạch và quarantine trước/sau khi áp dụng quy tắc.
   - Cập nhật bảng `metric_impact` trong báo cáo nhóm.

### Sau khi hoàn thành:
1. Commit và push nhánh lên GitHub:
   ```bash
   git add transform/cleaning_rules.py
   git commit -m "[Member2] Thêm quy tắc làm sạch mới"
   git push origin member2/cleaning-rules
   ```
2. Tạo pull request (PR) và gắn nhãn "Ready for Review".
3. Chờ nhóm review và chỉnh sửa nếu cần.

---

## Kết quả cần đạt được
- File `cleaning_rules.py` với ít nhất 3 quy tắc mới.
- Bảng `metric_impact` chứng minh hiệu quả của từng quy tắc.
- PR được merge vào nhánh chính.