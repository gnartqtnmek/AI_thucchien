# Individual Reflection 
Tên học viên: Nguyễn Thị Quỳnh Trang - 2A202600406

## 1. Vai trò trong nhóm (Role)
- Frontend Developer & UX/UI Designer. Phụ trách thiết kế và phát triển giao diện Chatbot (Vietnam Airlines UI) bằng React + Vite, tối ưu trải nghiệm người dùng (UX) và tích hợp các công cụ render Markdown.

## 2. Đóng góp cụ thể
- **Xây dựng giao diện Chat Widget:** Khởi tạo project React/Vite, thiết kế UI với Tailwind CSS. Tích hợp `react-markdown` và `remark-gfm` để render mượt mà các bảng giá vé, danh sách khách sạn và link tham khảo từ API Backend trả về.
- **Thiết kế cơ chế Feedback Loop:** Code UI phần Feedback Bar (👍 👎 💬) dưới mỗi tin nhắn của bot và phần Dynamic Suggestions (gợi ý câu hỏi). Dữ liệu này được đẩy qua `POST /feedback` để lưu vào `feedback_log.json` dưới backend, đáp ứng trực tiếp yêu cầu thu thập "Learning signal" trong file SPEC.

## 3. Đánh giá SPEC (Mạnh nhất & Yếu nhất)
- **Phần mạnh nhất:** *Top 3 failure modes*. Nhóm đã xác định rất đúng rủi ro "AI tự tin cao nhưng trả lời sai" (đặc biệt nguy hiểm với quy định hành lý hàng không). Việc thiết kế các Tool gọi trực tiếp vào Mock Data (như `baggage_rules.json`) thay vì để LLM tự đoán đã giải quyết triệt để rủi ro này.
- **Phần yếu nhất:** *ROI 3 kịch bản*. Các assumption (giả định) về cost đang hơi đơn giản vì chỉ tính chi phí gọi API OpenAI ($30-$300/ngày). Thực tế, hệ thống còn tốn chi phí duy trì server FastAPI (Render) và Frontend (Vercel) nếu scale lên hàng ngàn lượt truy cập, cộng thêm chi phí bảo trì hệ thống `url.txt` khi website VNA thay đổi cấu trúc.

## 4. Các đóng góp khác
- Hỗ trợ test các edge cases khó (Prompt Injection) và test logic của tool `check_special_baggage_item` với các từ khóa như "lẩu tự sôi", "sầu riêng", "pin dự phòng".
- Hỗ trợ setup file cấu hình `vercel.json` và `vite.config.js` để chuẩn bị cho việc deploy Frontend lên Vercel.

## 5. Một điều học được trong Hackathon
- Trước đây khi nghĩ về AI Chatbot, em thường nghĩ chỉ cần viết Prompt cho LLM là đủ. Qua dự án này, em hiểu sức mạnh thực sự nằm ở **Function Calling (Agent Pattern)**. Việc tách AI thành một "bộ não điều phối" để gọi các Python functions (`flights.py`, `prices.py`) giúp hệ thống không bao giờ bịa ra giá vé máy bay ảo, đảm bảo tiêu chí "Precision-first" mà nhóm đã đề ra trong SPEC.

## 6. Nếu làm lại, sẽ thay đổi điều gì?
- Em sẽ cải thiện UX ở phần xử lý độ trễ (Latency). Theo SPEC, target là `<2s`, nhưng đôi khi LLM phải gọi liên tiếp 2-3 tools (ví dụ: tìm chuyến bay + tính ngân sách) khiến user phải chờ lâu. Thay vì chỉ hiện spinner xoay tròn, em sẽ dùng **Streaming UI** để render từng chữ một ngay khi LLM đang sinh câu trả lời, giúp người dùng cảm thấy hệ thống phản hồi tức thì.

## 7. Trải nghiệm dùng AI tools (Giúp gì / Sai gì)
- **AI giúp gì:** Mình dùng AI để nhanh chóng generate các component React bằng Tailwind CSS (ví dụ: khung chat, các nút bấm feedback). Nó giúp tiết kiệm 80% thời gian gõ code UI boilerplate để mình tập trung vào logic kết nối API.
- **AI sai / mislead ở đâu:** Khi yêu cầu AI gợi ý cách quản lý state cho lịch sử chat (chat history), AI liên tục ép dùng Redux. Điều này gây *scope creep* (phình to phạm vi) không cần thiết cho một Prototype Hackathon. Cuối cùng, mình phải gạt AI sang một bên và tự dùng `useState` đơn giản của React để hoàn thành kịp tiến độ M2.