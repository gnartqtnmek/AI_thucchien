
## Context: Tôi là ai?

Tôi là Trang, một người học và làm việc với nhiều loại tài liệu, code và dự án.  
Hàng tuần tôi phải đọc tài liệu, debug code, làm project nhóm và chuẩn bị báo cáo.  

Trong quá trình đó, tôi nhận ra nhiều vấn đề lặp lại hoặc tốn thời gian nhưng chưa có cách giải quyết hiệu quả.  

Bài toán tôi mang vào lab hôm nay đến từ chính trải nghiệm học tập và làm việc hàng ngày.

---

# Phase 1 — SCAN: Tìm kiếm cơ hội

Dùng 4 Lenses để quét. Ghi mọi thứ, không filter.

| # | Lens | Bài toán |
|---|------|---------|
| 1 | Tốn thời gian | Đọc paper/tài liệu dài, mất 2 giờ mà không biết có đáng đọc không |
| 2 | AI có thể tốt hơn | Ôn thi, muốn AI tạo flashcard hoặc quiz tự động |
| 3 | Lặp lại | Viết báo cáo hoặc thesis, tốn thời gian format hơn viết nội dung |
| 4 | Tốn thời gian | Debug code mất nhiều giờ vì không tìm được root cause |
| 5 | Lặp lại | Note bài giảng xong không nhớ điểm chính |
| 6 | AI có thể tốt hơn | Tìm tài liệu tham khảo nhưng kết quả không liên quan |
| 7 | Pain từ người khác | Làm project nhóm nhưng không ai track tiến độ |
| 8 | AI có thể tốt hơn | Học ngoại ngữ nhưng không có partner để luyện nói |

---

# Phase 2 — QUICK-ASSESS: 3 Quick Problem Cards

Chọn top 3 từ list:
#1 Đọc tài liệu dài không biết có đáng đọc không  
#4 Debug code không tìm được root cause  
#2 Ôn thi cần tạo flashcard tự động  

---

## Card #1 — Đọc tài liệu không hiệu quả

```text
┌──────────────────────────────────────────────────┐
│ QUICK PROBLEM CARD #1                            │
│                                                  │
│ Bài toán: Đọc tài liệu dài mất nhiều thời gian   │
│ nhưng không biết có đáng đọc hay không           │
│                                                  │
│ Ai đang đau? Sinh viên, dev, researcher          │
│                                                  │
│ Workflow hiện tại:                               │
│   1. Tìm tài liệu                                │
│   → 2. Mở đọc từ đầu                             │
│   → 3. Đọc 1-2 giờ                               │
│   → 4. Nhận ra không relevant                    │
│                                                  │
│ Bước nào tốn nhất? Bước 2-3 (⏱ 1-2 giờ/lần)     │
│                                                  │
│ AI có thể giúp ở bước nào? Bước 2               │
│  - tóm tắt nhanh                                 │
│  - đánh giá độ liên quan                         │
│                                                  │
│ Đo thành công bằng gì?                           │
│ Giảm thời gian đọc tài liệu không cần thiết      │
│                                                  │
│ Quick gut: ☑ LLM Feature                         │
└──────────────────────────────────────────────────┘
```
## Card #4 — Debug code mất nhiều thời gian
```text
┌──────────────────────────────────────────────────┐
│ QUICK PROBLEM CARD #4                            │
│                                                  │
│ Bài toán: Debug code mất nhiều thời gian vì      │
│ không tìm được nguyên nhân gốc                   │
│                                                  │
│ Ai đang đau? Developer                           │
│                                                  │
│ Workflow hiện tại:                               │
│   1. Code lỗi                                    │
│   → 2. Đọc log                                   │
│   → 3. Thử sửa từng chỗ                          │
│   → 4. Test lại                                  │
│   → 5. Lặp lại nhiều lần                         │
│                                                  │
│ Bước nào tốn nhất? Bước 3 (⏱ thử sai nhiều lần) │
│                                                  │
│ AI có thể giúp ở bước nào? Bước 2-3             │
│  - phân tích log                                 │
│  - gợi ý root cause                             │
│                                                  │
│ Đo thành công bằng gì?                           │
│ Giảm thời gian debug                             │
│                                                  │
│ Quick gut: ☑ LLM Feature                         │
└──────────────────────────────────────────────────┘
```
## Card #2 — flashcard
```text
┌──────────────────────────────────────────────────┐
│ QUICK PROBLEM CARD #2                            │
│                                                  │
│ Bài toán: Ôn thi cần tạo flashcard và quiz       │
│ nhưng làm thủ công rất mất thời gian             │
│                                                  │
│ Ai đang đau? Sinh viên                           │
│                                                  │
│ Workflow hiện tại:                               │
│   1. Đọc tài liệu                                │
│   → 2. Ghi chú                                   │
│   → 3. Tạo flashcard                             │
│   → 4. Ôn tập                                    │
│                                                  │
│ Bước nào tốn nhất? Bước 2-3 (⏱ tốn nhiều thời gian)│
│                                                  │
│ AI có thể giúp ở bước nào? Bước 2-3             │
│  - tạo flashcard tự động                         │
│  - sinh quiz                                     │
│                                                  │
│ Đo thành công bằng gì?                           │
│ Giảm thời gian chuẩn bị ôn tập                   │
│                                                  │
│ Quick gut: ☑ LLM Feature                         │
└──────────────────────────────────────────────────┘
```
# Phase 3 — PITCH-CHALLENGE-VOTE

## Lý do không chọn các problem

### Card #1 — Đọc tài liệu không hiệu quả
Vấn đề này phụ thuộc nhiều vào mục tiêu và ngữ cảnh của người đọc.  
AI có thể hỗ trợ tóm tắt nhưng khó đánh giá chính xác mức độ liên quan trong mọi trường hợp.  

Việc xác định tài liệu có đáng đọc hay không mang tính chủ quan.  
Do đó, rất khó xây dựng metric rõ ràng để đo hiệu quả.  

Kết luận  
Problem này khó đo lường và khó chứng minh giá trị của AI một cách cụ thể.

---

### Card #2 — Tạo flashcard tự động
Đã có nhiều công cụ trên thị trường hỗ trợ tạo flashcard và quiz.  

Giá trị khác biệt nếu xây dựng thêm là không rõ ràng.  
Ngoài ra, việc đo lường hiệu quả học tập như “học tốt hơn” hoặc “nhớ lâu hơn” không dễ định lượng.

---

### Card #4 — Debug code mất nhiều thời gian
Vấn đề này phụ thuộc nhiều vào ngữ cảnh cụ thể của codebase, stack và kinh nghiệm của developer.  

AI có thể hỗ trợ phân tích log và gợi ý nguyên nhân, nhưng độ chính xác không ổn định trong các trường hợp phức tạp.  

Việc xác định “root cause” không chỉ dựa vào log mà còn cần hiểu sâu về hệ thống, điều mà AI khó làm đầy đủ nếu thiếu context.  

Metric “giảm thời gian debug” cũng bị ảnh hưởng bởi nhiều yếu tố khác nhau, không chỉ riêng AI.  


Kết luận  
Problem này không đủ mạnh về mặt khác biệt và khó đánh giá hiệu quả.