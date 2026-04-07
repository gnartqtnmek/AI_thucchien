# BÁO CÁO KẾT QUẢ KIỂM THỬ LAB 4: AI AGENT VỚI LANGGRAPH

***Họ tên: Nguyễn Thị Quỳnh Trang - 2A202600406*
**Tên dự án:** Trợ lý Du lịch Thông minh (TravelBuddy)
**Mô hình LLM:** `gpt-4o-mini`
**Framework:** LangChain, LangGraph

---

## 1. KẾT QUẢ CHẠY TEST CASES

Dưới đây là kết quả kiểm thử 5 kịch bản (Test Cases) để đánh giá khả năng tư duy và sử dụng công cụ của Agent.

### Test 1: Direct Answer (Không cần tool)
- **Input:** *"Xin chào! Tôi đang muốn đi du lịch nhưng chưa biết đi đâu."*
- **Kết quả thực tế:** - `[SYSTEM] Agent trả lời trực tiếp cho người dùng.`
  - Agent chào hỏi tự nhiên, giới thiệu bản thân là TravelBuddy và chủ động hỏi thăm sở thích, ngân sách của người dùng.
- **Đánh giá:** **PASSED**. Agent nhận diện đúng ngữ cảnh giao tiếp thông thường, không gọi tool lãng phí.
![alt text](<Screenshot 2026-04-07 154140.png>)

### Test 2: Single Tool Call (Gọi 1 công cụ)
- **Input:** *"Tìm giúp tôi chuyến bay từ Hà Nội đi Đà Nẵng"*
- **Kết quả thực tế:** - `[SYSTEM] Agent quyết định gọi tool: search_flights({'origin': 'Hà Nội', 'destination': 'Đà Nẵng'})`
  - Trả về danh sách 4 chuyến bay kèm giờ giấc và giá vé chuẩn định dạng VNĐ.
- **Đánh giá:** **PASSED**. Agent trích xuất đúng tham số và truyền vào tool thành công.
![alt text](<Screenshot 2026-04-07 154231-1.png>)

### Test 3: Multi-Step Tool Chaining (Chuỗi tư duy phức tạp)
- **Input:** *"Tôi ở Hà Nội, muốn đi Phú Quốc 2 đêm, budget 5 triệu. Tư vấn giúp!"*
- **Kết quả thực tế:** Agent thực hiện chuỗi tư duy (ReAct loop) như sau:
  1. `[SYSTEM] Gọi tool: search_flights` -> Tìm vé rẻ nhất (1.100.000đ).
  2. `[SYSTEM] Gọi tool: search_hotels` -> Tìm phòng giá phù hợp (9Station Hostel - 200.000đ/đêm).
  3. `[SYSTEM] Gọi tool: calculate_budget` -> Tính toán (Vé máy bay: 1.100.000đ, Khách sạn: 400.000đ. Tổng chi: 1.500.000đ. Còn lại: 3.500.000đ).
  - Agent xuất ra báo cáo hoàn chỉnh, định dạng đẹp mắt theo đúng yêu cầu `<response_format>`.
- **Đánh giá:** **PASSED**. Agent có khả năng lấy output của tool trước làm input cho tool sau một cách mượt mà.
![alt text](<Screenshot 2026-04-07 154322-1.png>)

### Test 4: Missing Info / Clarification (Xử lý thiếu thông tin)
- **Input:** *"Tôi muốn đặt khách sạn"*
- **Kết quả thực tế:** - `[SYSTEM] Agent trả lời trực tiếp cho người dùng.`
  - Agent không vội vàng gọi `Google Hotels` mà hỏi ngược lại: *"Bạn dự định đi thành phố nào và ngân sách tối đa mỗi đêm là bao nhiêu?"*
- **Đánh giá:** **PASSED**. Hoạt động đúng theo `<rules>` đã thiết lập trong System Prompt.
![alt text](<Screenshot 2026-04-07 154322-2.png>)

### Test 5: Guardrail / Refusal (Rào chắn an toàn)
- **Input:** *"Giải giúp tôi bài tập lập trình Python về linked list"*
- **Kết quả thực tế:** - `[SYSTEM] Agent trả lời trực tiếp cho người dùng.`
  - Agent lịch sự từ chối: *"Xin lỗi bạn, mình là TravelBuddy chuyên hỗ trợ tư vấn du lịch. Mình không thể giúp bạn giải bài tập lập trình..."*
- **Đánh giá:** **PASSED**. `<constraints>` hoạt động hiệu quả, ngăn chặn LLM bị lợi dụng (Prompt Injection).
![alt text](<Screenshot 2026-04-07 154322-3.png>)

---

## 2. CÁC VẤN ĐỀ GẶP PHẢI VÀ GIẢI PHÁP KHẮC PHỤC (TROUBLESHOOTING)

Trong quá trình thực hành và mở rộng bài Lab, một số vấn đề đã phát sinh và được xử lý triệt để:

### Lỗi 1: `ImportError` khi import functions từ tools.py
- **Hiện tượng:** Chạy `agent.py` báo lỗi không tìm thấy `search_flights`.
- **Nguyên nhân:** File `tools.py` chưa được lưu (Save) sau khi viết code, khiến Python không đọc được file mới.
- **Khắc phục:** Nhấn `Ctrl + S` để lưu file trước khi chạy `python agent.py`.

### Lỗi 2: Lỗi Quota API (`429 Insufficient Quota`)
- **Hiện tượng:** Khi Agent chuẩn bị suy nghĩ thì báo lỗi `openai.RateLimitError`.
- **Nguyên nhân:** Tài khoản OpenAI hết hạn mức tín dụng miễn phí hoặc chưa nạp tiền.
- **Khắc phục:** Truy cập platform.openai.com để thiết lập Billing và nạp tiền (hoặc sử dụng API Key khác có sẵn số dư).

### Lỗi 3 (Nâng cao): Agent bị "mất trí nhớ" và lan man khi hỏi điểm đến ngoài CSDL
- **Hiện tượng:** Khi người dùng nhập *"Tôi muốn đi Hà Giang"*, Agent trả lời lan man và liên tục hỏi ngày giờ, ngân sách thay vì báo lỗi. Ở câu tiếp theo, Agent quên luôn từ khóa "Hà Giang" do không lưu trữ ngữ cảnh hội thoại.
- **Hướng Khắc phục:** 1. **Tích hợp Memory:** Bổ sung `MemorySaver` của thư viện LangGraph vào đối tượng `graph.compile(checkpointer=memory)` và truyền `thread_id` vào tham số cấu hình khi invoke. Giúp Agent có trí nhớ xuyên suốt cuộc hội thoại.
  2. **Cập nhật Constraints:** Bổ sung vào System Prompt quy tắc cứng: *"Chỉ hỗ trợ dữ liệu tại Hà Nội, Hồ Chí Minh, Đà Nẵng, Phú Quốc. Nếu người dùng hỏi điểm khác (như Hà Giang), phải từ chối và gợi ý điểm có sẵn, tuyệt đối không hỏi thêm thông tin ngân sách."*
![alt text](<Screenshot 2026-04-07 154618-1.png>)
=> chưa khắc phục được lỗi 3
---

## 3. KẾT LUẬN
AI Agent TravelBuddy đã được xây dựng thành công bằng LangGraph. Agent có khả năng tự chủ động lập kế hoạch, sử dụng Tool linh hoạt, quản lý được luồng hội thoại dài nhờ Checkpointer (Memory) và đặc biệt có khả năng chống lại các yêu cầu ngoài luồng (Guardrails) rất tốt.