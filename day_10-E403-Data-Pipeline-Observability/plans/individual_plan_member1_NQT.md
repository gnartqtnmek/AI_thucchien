# Kế hoạch cá nhân: Thành viên 1 - Phân tích dữ liệu & Hợp đồng dữ liệu

## Công việc cần làm

### Trước khi bắt đầu:
1. **Cài đặt môi trường làm việc:**
   - Đảm bảo Python và các thư viện cần thiết đã được cài đặt (xem `requirements.txt`).
   - Clone repository từ GitHub về máy cá nhân.
   - Tạo nhánh làm việc riêng, đặt tên theo định dạng `member1/analysis-contract`.

2. **Hiểu yêu cầu:**
   - Đọc file `PLAN.md` để hiểu tổng quan kế hoạch.
   - Đọc file `policy_export_dirty.csv` để nắm rõ dữ liệu thô.

### Công việc chính:
1. **Phân tích dữ liệu:**
   - Mở file `data/raw/policy_export_dirty.csv` và ghi nhận các lỗi phổ biến (thiếu cột, dữ liệu trùng lặp, định dạng sai, v.v.).
   - Ghi lại các lỗi vào file `docs/data_analysis_notes.md`.

2. **Tạo hợp đồng dữ liệu:**
   - Tạo file `contracts/data_contract.yaml` với các thông tin:
     - **Owner:** Tên nhóm hoặc cá nhân.
     - **SLA_hours:** Thời gian SLA (ví dụ: 24 giờ).
     - **Sources:** Liệt kê ít nhất 2 nguồn dữ liệu.
     - **Schema:** Định nghĩa ít nhất 5 cột với kiểu dữ liệu và ràng buộc.
     - **Failure modes:** Liệt kê 3–4 lỗi phổ biến.
     - **Quarantine rules:** Quy định rõ lỗi nào cần "halt" và lỗi nào cần "warn".

3. **Kiểm tra hợp đồng:**
   - Chạy lệnh kiểm tra YAML:
     ```bash
     python -m yaml contracts/data_contract.yaml
     ```
   - Đảm bảo pipeline đọc file hợp đồng không lỗi.

### Sau khi hoàn thành:
1. Commit và push nhánh lên GitHub:
   ```bash
   git add contracts/data_contract.yaml docs/data_analysis_notes.md
   git commit -m "[Member1] Phân tích dữ liệu và tạo hợp đồng dữ liệu"
   git push origin member1/analysis-contract
   ```
2. Tạo pull request (PR) và gắn nhãn "Ready for Review".
3. Chờ nhóm review và chỉnh sửa nếu cần.

---

## Kết quả cần đạt được
- File `data_contract.yaml` hoàn chỉnh, không lỗi.
- File `docs/data_analysis_notes.md` ghi lại các lỗi dữ liệu.
- PR được merge vào nhánh chính.