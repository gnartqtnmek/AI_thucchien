# Bài làm UX Exercise — Phân tích Chatbot NEO (Vietnam Airlines)

**Sản phẩm:** Vietnam Airlines — Chatbot NEO  
**Kênh:** Zalo / Website vietnamairlines.com  
**Ngày thử nghiệm:** 08/04/2026  
**Người thực hiện:** Đặng Văn Minh Minh - 2A2026000A27

---

## Phần 1 — Khám phá sản phẩm

### Marketing hứa gì?

Vietnam Airlines quảng bá NEO là "trợ lý ảo thông minh" hỗ trợ khách hàng 24/7, có khả năng:
- Tra cứu chuyến bay, hành lý, lịch bay theo thời gian thực
- Hỗ trợ đặt vé, check-in, hoàn/đổi vé
- Trả lời mọi thắc mắc về quy định bay

### Thực tế quan sát được

NEO hoạt động dưới dạng rule-based chatbot với một số khả năng NLU nhất định. Hệ thống có 2 layer rõ rệt:
- **Layer bot (NEO):** xử lý FAQ, tra cứu thông tin tĩnh
- **Layer human agent:** được chuyển khi request vượt scope (không minh bạch khi nào chuyển)

---

## Phần 2 — Phân tích 4 Paths

### Path 1: Khi AI đúng (Happy Path)

| Câu hỏi | Kết quả | Nhận xét |
|---------|---------|---------|
| Hành lý ký gửi HAN–SGN? | Trả lời đúng: 23kg (kèm note về hạng vé) | Tốt, có context đầy đủ |
| Check-in online? | Đúng: hướng dẫn 4 bước + link + khung giờ 24h–1h | Tốt, actionable |
| Hotline CSKH? | Đúng: 1900 1100 + số quốc tế | Chuẩn xác |
| Tra cứu dặm Lotusmiles? | Đúng: hướng dẫn + link đăng nhập | Tốt nhưng link redirect về homepage |
| VN123 delay không? | Hỏi confirm lại → trả lời đúng giờ bay | Tốt, có bước xác nhận |

**Điểm mạnh:** NEO xử lý tốt các câu hỏi FAQ chuẩn. Thông tin chính xác, có link dẫn nguồn, có số điện thoại backup. Khi hỏi về chuyến bay cụ thể, biết hỏi lại để confirm.

**Điểm yếu nhỏ:** Một số câu trả lời bị duplicate (gửi 2–3 lần cùng nội dung) — lỗi hệ thống gây UX xấu.

---

### Path 2: Khi AI không chắc (Ambiguous Path)

| Câu hỏi mơ hồ | Phản ứng NEO | Đánh giá |
|--------------|-------------|---------|
| "Đặt vé cho bé" | **Không hỏi lại** — dump ngay toàn bộ quy định trẻ em (rất dài) | Sai approach: nên hỏi "Bé dưới 2 tuổi hay 2–12 tuổi?" |
| "Hành lý đặc biệt" | **Không hỏi lại** — liệt kê hành lý đặc biệt nói chung | Nên hỏi: "Bạn mang nhạc cụ, gậy golf hay xe đạp?" |
| "Quy định hoàn vé" | **Không hỏi lại** — trả lời đầy đủ nhưng rất dài, khó đọc | Nên hỏi: "Vé mua kênh nào? Hạng vé gì?" |
| "Mất đồ ở sân bay" | **Không hỏi lại** — hướng dẫn quy trình chung | Nên hỏi: "Mất trong khu vực nào?" |

**Nhận xét:** NEO **không có cơ chế hỏi ngược lại** (clarification). Khi gặp input mơ hồ, mặc định đổ ra toàn bộ thông tin liên quan → response quá dài, khó đọc, không targeted.

---

### Path 3: Khi AI sai (Error Path)

| Câu hỏi bẫy | Phản ứng NEO | Đánh giá |
|------------|-------------|---------|
| Mang mèo + sáo lên máy bay | Trả lời phí chung cho thú cưng, không phân biệt mèo vs chim | Sai về nghiệp vụ: chim (sáo) có quy định riêng (CITES/IATA), không giống thú nuôi |
| Sai tên đệm, tự sửa web? | Trả lời đúng: không tự sửa được, cần gọi hotline | Tốt |
| Web báo lỗi 404, mua hành lý | **Chuyển sang human agent** (không giải thích) | Chuyển được nhưng không nói "đang kết nối nhân viên" — user bối rối |
| So sánh giá Thương gia vs Phổ thông linh hoạt London tháng 10 | "Bạn tham khảo trên website nhé" | Fail hoàn toàn: đẩy user ra khỏi kênh không giải thích lý do |
| Dùng dặm đổi vé cho bạn | Không được hỏi thử vì conversation đã bị giới hạn | N/A |

**Nhận xét:** NEO **không có error acknowledgement** — khi không trả lời được, không nói "NEO chưa có thông tin về vấn đề này" mà hoặc im lặng chuyển agent hoặc redirect thô về website.

---

### Path 4: Khi user mất tin tưởng (Fallback Path)

| Trigger | Phản ứng NEO | Đánh giá |
|---------|-------------|---------|
| "Cho tôi gặp người thật!" | "Chúng tôi là Chatbot Team" | **Tệ:** không kết nối được human, phản hồi vô nghĩa |
| "Hệ thống tệ, tôi muốn khiếu nại" | Đưa số hotline + email | Chấp nhận được, nhưng thiếu empathy |
| "Kết nối nhân viên hỗ trợ trực tuyến" | "Vui lòng cung cấp mã đặt chỗ" | **Tệ:** không kết nối được, hỏi thêm thông tin không cần thiết |
| "Chuyến bay sắp cất cánh, xử lý gấp" | "Vui lòng cung cấp mã đặt chỗ" | **Rất tệ:** tình huống khẩn cấp nhưng không escalate ưu tiên |

**Nhận xét:** Fallback path là **điểm yếu nhất của NEO**. Không có live chat thực sự. Khi user yêu cầu gặp người, bot không hiểu intent hoặc giả vờ không hiểu. Trong tình huống khẩn cấp (sắp bay), vẫn hỏi mã đặt chỗ trước — ngược với kỳ vọng người dùng.

---

## Phần 3 — Tổng đánh giá

### Path mạnh nhất: Path 1 — Happy Path

NEO xử lý tốt các câu FAQ chuẩn: thông tin chính xác, có link nguồn, có số liên lạc backup. Đây là core value proposition hoạt động ổn định.

### Path yếu nhất: Path 4 — Fallback / Mất tin tưởng

Lý do:
1. **Không có live handoff thực sự:** Khi user yêu cầu "gặp người thật", bot reply "Chúng tôi là Chatbot Team" — không kết nối được human agent, không đưa ra lối thoát rõ ràng.
2. **Không nhận ra urgency:** Câu "chuyến bay sắp cất cánh" không trigger bất kỳ priority flag nào.
3. **Thiếu empathy hoàn toàn:** Không có câu "Xin lỗi vì sự bất tiện" hay acknowledgement cảm xúc.

### Gap marketing vs thực tế

| Marketing hứa | Thực tế |
|--------------|---------|
| "Trợ lý ảo thông minh" | Rule-based + NLU hạn chế, không clarify được |
| Hỗ trợ 24/7 seamless | 24/7 đúng, nhưng scope rất hẹp; ngoài FAQ là hỏng |
| Giải quyết vấn đề ngay | Nhiều case phải gọi hotline hoặc vào website thủ công |
| Live chat với nhân viên | Chỉ có một số flow được human agent; không minh bạch khi nào |

---

## Phần 4 — Sketch "làm tốt hơn" (Path 4 — Fallback)

### As-is: User journey hiện tại

```
User frustrated → "Cho tôi gặp người thật"
        ↓
NEO: "Chúng tôi là Chatbot Team"  ← [ĐIỂM GÃY #1: vô nghĩa]
        ↓
User: "Hệ thống tệ, khiếu nại"
        ↓
NEO: đưa hotline/email  ← [ĐIỂM GÃY #2: đẩy user sang kênh khác, không giữ ngữ cảnh]
        ↓
User: "Chuyến bay sắp bay, gấp!"
        ↓
NEO: "Cung cấp mã đặt chỗ"  ← [ĐIỂM GÃY #3: không hiểu urgency]
        ↓
User bỏ cuộc / gọi hotline tự làm
```

### To-be: User journey đề xuất

```
User frustrated → "Cho tôi gặp người thật"
        ↓
[DETECT ESCALATION INTENT]
NEO: "NEO hiểu bạn muốn gặp nhân viên.
      Hiện tại: [●] 3 nhân viên đang online.
      Thời gian chờ ước tính: ~2 phút."
      [Kết nối ngay] [Gọi hotline] [Tiếp tục với NEO]
        ↓
User click [Kết nối ngay]
        ↓
NEO: "Đang chuyển cuộc trò chuyện kèm toàn bộ lịch sử chat..."
     "Nhân viên Nguyễn Lan đã tham gia."  ← Human agent vào với context đầy đủ
        ↓
[Nếu user báo urgency: "sắp bay", "gấp", "cất cánh"]
        ↓
[DETECT URGENCY KEYWORDS] → PRIORITY FLAG
NEO: "NEO nhận thấy đây là tình huống khẩn cấp.
      Đang ưu tiên kết nối ngay..."
      → Skip queue, kết nối ngay hoặc auto-dial hotline
```

**Thêm gì:**
- Urgency detection (keywords: "gấp", "sắp bay", "cất cánh", "khẩn")
- Hiển thị trạng thái queue thực (số agent online, ETA)
- Handoff có context: agent nhận được toàn bộ lịch sử chat
- Empathy message trước khi chuyển

**Bớt gì:**
- Yêu cầu nhập mã đặt chỗ TRƯỚC khi kết nối human (thu thập sau, khi đã kết nối)
- Reply vô nghĩa "Chúng tôi là Chatbot Team"

**Đổi gì:**
- Fallback default: từ "đưa hotline" → "offer live chat với ETA rõ ràng"
- Tone: từ transactional → empathetic ("NEO hiểu đây là tình huống không dễ chịu")

---

## Điểm tự đánh giá

| Tiêu chí | Mức độ hoàn thành |
|----------|-------------------|
| Phân tích 4 paths đủ + nhận xét path yếu nhất | Đủ 4 paths, có ví dụ cụ thể từ thử nghiệm thực tế |
| Sketch as-is + to-be rõ ràng | Có as-is với điểm gãy đánh dấu, to-be với giải pháp cụ thể |
| Nhận xét gap marketing vs thực tế | Có bảng so sánh rõ ràng |

---

*Bài tập UX — Ngày 5 — VinUni A20 — AI Thực Chiến · 2026*
