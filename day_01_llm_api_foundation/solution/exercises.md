# Ngày 1 — Bài Tập & Phản Ánh
## Nền Tảng LLM API | Phiếu Thực Hành

**Thời lượng:** 1:30 giờ  
**Cấu trúc:** Lập trình cốt lõi (60 phút) → Bài tập mở rộng (30 phút)

---

## Phần 1 — Lập Trình Cốt Lõi (0:00–1:00)

Chạy các ví dụ trong Google Colab tại: https://colab.research.google.com/drive/172zCiXpLr1FEXMRCAbmZoqTrKiSkUERm?usp=sharing

Triển khai tất cả TODO trong `template.py`. Chạy `pytest tests/` để kiểm tra tiến độ.

**Điểm kiểm tra:** Sau khi hoàn thành 4 nhiệm vụ, chạy:
```bash
python template.py
```
Bạn sẽ thấy output so sánh phản hồi của GPT-4o và GPT-4o-mini.

---

## Phần 2 — Bài Tập Mở Rộng (1:00–1:30)

### Bài tập 2.1 — Độ Nhạy Của Temperature
Gọi `call_openai` với các giá trị temperature 0.0, 0.5, 1.0 và 1.5 sử dụng prompt **"Hãy kể cho tôi một sự thật thú vị về Việt Nam."**

**Bạn nhận thấy quy luật gì qua bốn phản hồi?** (2–3 câu)
> *Khi Temperature tăng dần từ 0.0 lên 1.5, câu trả lời của mô hình chuyển từ trạng thái an toàn, thực tế và mang tính khuôn mẫu sang trạng thái sáng tạo, đa dạng từ vựng hơn. Tuy nhiên, ở mức rất cao (như 1.5), văn bản bắt đầu trở nên thiếu tự nhiên, lan man hoặc thậm chí sinh ra thông tin ảo (hallucination) không chính xác.*

**Bạn sẽ đặt temperature bao nhiêu cho chatbot hỗ trợ khách hàng, và tại sao?**
> *đặt temperature ở mức thấp (khoảng 0.0 đến 0.2) cho chatbot hỗ trợ khách hàng. Lý do là vì trong môi trường chăm sóc khách hàng, tính chính xác, nhất quán và bám sát thông tin thực tế là yếu tố quan trọng nhất; chúng ta không muốn chatbot tự sáng tạo ra các chính sách hay thông tin sai lệch gây nhầm lẫn cho người dùng.*

---

### Bài tập 2.2 — Đánh Đổi Chi Phí
Xem xét kịch bản: 10.000 người dùng hoạt động mỗi ngày, mỗi người thực hiện 3 lần gọi API, mỗi lần trung bình ~350 token.

**Ước tính xem GPT-4o đắt hơn GPT-4o-mini bao nhiêu lần cho workload này:**
> *Tổng số token đầu ra mỗi ngày = 10.000 người x 3 lần x 350 token = 10.500.000 token. Chi phí cho GPT-4o là khoảng 2.625.000/ngày. Chi phí cho GPT-4o-mini là khoảng 157.500/ngày. Do đó, GPT-4o đắt hơn GPT-4o-mini khoảng 16,67 lần.*

**Mô tả một trường hợp mà chi phí cao hơn của GPT-4o là xứng đáng, và một trường hợp GPT-4o-mini là lựa chọn tốt hơn:**
> **- GPT-4o xứng đáng khi: Cần xử lý các tác vụ suy luận logic phức tạp, viết mã lập trình (code) chuyên sâu, phân tích dữ liệu đa chiều hoặc giải quyết các vấn đề đòi hỏi độ chính xác và khả năng hiểu ngữ cảnh cao. GPT-4o-mini là lựa chọn tốt hơn khi: Xử lý các tác vụ lặp đi lặp lại với khối lượng lớn và yêu cầu đơn giản như: tóm tắt văn bản, dịch thuật cơ bản, phân loại cảm xúc bình luận, hoặc trích xuất dữ liệu có cấu trúc (JSON). Lúc này, ưu tiên hàng đầu là tốc độ (latency) và tối ưu chi phí.**

---

### Bài tập 2.3 — Trải Nghiệm Người Dùng với Streaming
**Streaming quan trọng nhất trong trường hợp nào, và khi nào thì non-streaming lại phù hợp hơn?** (1 đoạn văn)
> *Streaming quan trọng nhất trong các ứng dụng tương tác trực tiếp với con người (như chatbot, trợ lý ảo), vì nó giúp giảm đáng kể "thời gian chờ đợi cảm nhận", giữ cho người dùng luôn được tương tác qua lại thay vì phải nhìn vào màn hình trống trong lúc chờ AI xử lý toàn bộ câu trả lời dài. Ngược lại, non-streaming lại phù hợp hơn cho các tác vụ chạy ngầm, xử lý dữ liệu hàng loạt, hoặc khi hệ thống cần bóc tách và định dạng dữ liệu có cấu trúc (như xuất ra file JSON); vì trong các trường hợp này, ứng dụng chỉ cần kết quả cuối cùng hoàn chỉnh và chính xác chứ không cần hiển thị từng chữ cho người dùng xem*


## Danh Sách Kiểm Tra Nộp Bài
- [ ] Tất cả tests pass: `pytest tests/ -v`
- [ ] `call_openai` đã triển khai và kiểm thử
- [ ] `call_openai_mini` đã triển khai và kiểm thử
- [ ] `compare_models` đã triển khai và kiểm thử
- [ ] `streaming_chatbot` đã triển khai và kiểm thử
- [ ] `retry_with_backoff` đã triển khai và kiểm thử
- [ ] `batch_compare` đã triển khai và kiểm thử
- [ ] `format_comparison_table` đã triển khai và kiểm thử
- [ ] `exercises.md` đã điền đầy đủ
- [ ] Sao chép bài làm vào folder `solution` và đặt tên theo quy định 
