# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Thị Quỳnh Trang
- **Student ID**: 2A202600406
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

* **Modules Implemented**: Tối ưu hóa Regex Parser trong `src/agent/agent.py` và tinh chỉnh luồng dữ liệu của tool trong `src/tools/restaurant_tools.py`.
* **Code Highlights**: Thiết kế lại bộ Parser để Agent có thể bóc tách (parse) được các tham số (arguments) linh hoạt hơn, chống lại tình trạng LLM sinh ra format sai (hallucination format).
  ```python
  # Trong src/agent/agent.py
  def _parse_action(text: str) -> Optional[Tuple[str, str]]:
      # Hỗ trợ bắt Action linh hoạt, xử lý lỗi parse do LLM sinh ra dấu ngoặc kép hoặc xuống dòng
      match = re.search(r"Action\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*)\((.*?)\)", text, flags=re.IGNORECASE | re.DOTALL)
      if not match: 
          return None
      return match.group(1).strip(), match.group(2).strip().strip('"').strip("'")

---

## II. Debugging Case Study (10 Points)

- Problem Description: Agent bị kẹt trong vòng lặp vô hạn (Infinite Loop) và bị ngắt bởi max_steps khi cố gắng gọi tool check_freeship.

- Log Source: Trích xuất từ hệ thống Telemetry qua file logs/2026-04-07.log:
    ```
    {"event": "AGENT_STEP", "data": {"llm_output": "Action: check_freeship(total_amount=200000, city='Ha Noi')"}}
    {"event": "AGENT_TOOL_ERROR", "data": {"tool": "check_freeship", "error": "Missing args. Expected: total_amount[,city]"}}"
    ```

- Diagnosis: LLM đã tự động thêm tên biến (total_amount=) vào bên trong chuỗi argument theo thói quen lập trình, trong khi hàm xử lý của tool chỉ mong đợi một chuỗi giá trị thuần túy được phân tách bằng dấu phẩy "200000, Ha Noi". Do Observation trả về lỗi không đủ chi tiết, LLM tiếp tục thử lại cú pháp sai lầm đó nhiều lần cho đến khi cạn max_steps.

- Solution: Cập nhật lại thuộc tính description của tool trong TOOL_REGISTRY với rule khắt khe hơn: "Check delivery and freeship. Input MUST BE exactly: 'amount,city' (e.g., '200000,Ha Noi'). DO NOT use key=value format." Đồng thời, tôi nâng cấp hàm _tool_check_freeship để nó tự động loại bỏ các từ khóa rác như total_amount= nếu LLM vẫn cố tình sinh ra.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

- Reasoning: Khối Thought giúp LLM tự hình thành một "bộ nhớ nháp" trước khi hành động. Nhờ có bước phân tích này, Agent không vội đoán mò giá trị (như Chatbot thường làm), mà lên kế hoạch gọi tool để kiểm chứng, qua đó triệt tiêu gần như hoàn toàn "ảo giác" (hallucination) dữ liệu.

- Reliability: Mặc dù suy luận mạnh mẽ, Agent lại hoạt động tệ hơn Chatbot ở khía cạnh tốc độ khi đối mặt với các câu hỏi đơn giản. Vòng lặp ReAct khiến thời gian phản hồi (latency) tăng gấp đôi/gấp ba so với việc trả lời trực tiếp, gây ảnh hưởng đáng kể đến trải nghiệm người dùng (UX) trong các tác vụ cần sự phản xạ nhanh.

- Observation: Đây là mỏ neo thực tế của hệ thống. Khi kết quả trả về từ DB là hết hàng, Observation ép LLM phải bám sát vào sự thật đó để đưa ra Final Answer từ chối khéo léo, thay vì tiếp tục làm hài lòng khách hàng bằng những lời hứa suông.

---

## IV. Future Improvements (5 Points)

Để mở rộng Agent này thành một hệ thống Production thực thụ, em đề xuất:

- Scalability & UX Enhancements: Chuyển đổi kiến trúc sang một Backend sử dụng Node.js quản lý State của Agent một cách bất đồng bộ, kết hợp với giao diện Frontend được tối ưu hóa bằng React/Vite. Thông qua WebSockets, chúng ta có thể thiết kế một giao diện "stream" trực tiếp quá trình suy luận (Thought và Action) của Agent lên UI theo thời gian thực. Điều này giúp giảm thiểu sự mệt mỏi của người dùng (user journey) khi phải chờ hệ thống load qua nhiều bước.

- Safety: Cài đặt thêm một "Supervisor LLM" (chạy song song) đứng giữa Agent và người dùng để giám sát, bắt các output vi phạm luồng nghiệp vụ hoặc rò rỉ prompt bảo mật.

- Performance: Khi số lượng Tool tăng lên, việc đưa toàn bộ mô tả tool vào System Prompt sẽ vượt quá Context Window. Giải pháp là ứng dụng Vector DB (Agentic RAG) để truy xuất động (Retrieve) chỉ 3-5 tools liên quan nhất đến câu hỏi của người dùng.
---
