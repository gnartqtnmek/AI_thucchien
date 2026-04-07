**Dự án:** Domain Translator (Phiên dịch PRD/Figma sang Technical Specs)

---
# Phase 4 — DEEP-DIVE

## 4.1 — Current-State Workflow

### Plaintext

```text
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│ Bước 1      │     │ Bước 2      │     │ Bước 3       │     │ Bước 4           │
│ Viết PRD &  │     │ Handoff     │     │ Tự dịch sang │     │ Lập trình        │
│ Vẽ Figma    │ ──→ │ Meeting     │ ──→ │ Tech Logic   │ ──→ │ (Coding)         │
│ Ai: BA/Design     │ Ai: Cả team │     │ Ai: Dev (SE) │     │ Ai: Dev (SE)     │
│ ⏱ 2-3 ngày  │     │ ⏱ 2 hours   │     │ ⏱ 1 ngày 🔴  │     │ ⏱ 3-5 ngày       │
│ In: Yêu cầu │     │ In: Docs    │     │ In: Docs/UI  │     │ In: Tech Specs   │
│ Out: Docs   │     │ Out: Q&A    │     │ Out: DB/API  │     │ Out: Tính năng   │
└─────────────┘     └─────────────┘     └──────────────┘     └──────────────────┘
                                                                       │
                                                                       ▼
┌──────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ Bước 7           │     │ Bước 6           │     │ Bước 5      │
│ Rework (Code lại)│     │ Cãi vã & Giải    │     │ QA Test     │
│ Ai: Dev (SE)     │ ←── │ thích lại PRD    │ ←── │ phát hiện   │
│ ⏱ 2-3 ngày 🔴   │     │ Ai: Cả team      │     │ sai nghiệp vụ│
│                  │     │ ⏱ 2-4 hours     │     │ Ai: QA/BA   │
└──────────────────┘     └──────────────────┘     └─────────────┘
```

## 🔴 = Bottleneck (Điểm nghẽn)

### Ghi chú bottleneck

- **Bước 3 (20% rủi ro):** Dev tốn thời gian tự dịch ngôn ngữ Business sang Tech, rất dễ hiểu sai ngữ cảnh do lười đọc text dài.
- **Bước 7 (Tốn kém nhất):** Việc code lại do sai logic nghiệp vụ từ đầu “đốt” mất 2-3 ngày của Sprint.

---

## 4.2 — Problem Statement (6-field)

| Field | Nội dung |
|---|---|
| **Actor / Operator** | Developer (SE), BA/IA, Designer trong các công ty |
| **Current Workflow** | BA viết PRD + Design Figma → Handoff → Dev tự dịch sang tech specs → Code → QA test sai nghiệp vụ → Họp giải thích lại → Rework. (7 bước, rất nhiều ma sát giao tiếp) |
| **Bottleneck** | Bước Dev tự dịch PRD/Figma sang Logic Tech dễ sai lệch ngữ cảnh. Hậu quả là bước Rework tốn 2-3 ngày mỗi Sprint |
| **Impact** | Chậm time-to-market. 30% bug ở khâu QA là do “không hiểu đúng requirement” chứ không phải lỗi kỹ năng code. Gây ức chế tâm lý trong team |
| **Success Metric** | Giảm thời gian Rework từ 9-10 ngày/sprint → 4-5 ngày/sprint. Giảm lượng bug sai nghiệp vụ từ 30% → dưới 10% |
| **Operational Boundary** | AI không sinh ra Production Code. AI không sửa PRD gốc. AI chỉ đọc và draft ra bản tóm tắt kỹ thuật. Dev bắt buộc phải review và xác nhận với BA trước khi code |

### Sub-goals Decomposition

- **Trước khi dùng AI:** Set up prompt template có khả năng nhận cả Text (PRD) và Vision (Figma screenshots).
- **Trong khi dùng AI:** Dev review bản dịch Tech Specs của AI, đặc biệt chú ý mục **Ambiguity Highlights** (các điểm AI thấy mâu thuẫn giữa Text và Hình) để ping BA confirm lại ngay.

### Metrics

| Loại | Metric | Ngưỡng |
|---|---|---|
| **Efficiency** | Thời gian Rework do sai Requirement | 3 ngày/sprint → < 1 ngày/sprint |
| **Quality** | Tỷ lệ Bug Logic Nghiệp vụ ở vòng QA đầu | ~30% tổng số bug → < 10% |

---

## 4.3 — Research

### Existing solution

Các AI tool như **v0.dev** hoặc **Builder.io** mạnh về việc dịch UI sang Frontend Code, nhưng yếu ở việc tổng hợp logic nghiệp vụ Backend/Database từ một file PRD chữ dài. **Jira AI** thì chỉ tóm tắt text, không nhìn được Figma.

### Case study

Một số team Agile dùng **GPT-4 Vision** để đối chiếu PRD và UI Design, yêu cầu AI xuất ra **JSON schema** và danh sách **API Endpoints**. Việc này giúp Dev có ngay “dàn bài” kỹ thuật quen thuộc để bắt đầu, giảm 50% thời gian ngồi “tưởng tượng” logic.

### Quick poll

Khảo sát nhanh 3 SE trong nhóm: **3/3** thừa nhận rất “lười” đọc file docs dài của BA, chỉ thích nhìn vào sơ đồ Database hoặc API Contract để code luôn.

### Bài học rút ra

Dev thường có tâm lý “ngại” đọc những file PRD dài dòng từ BA, dẫn đến việc tự diễn giải logic theo cảm tính và gây ra 2-3 ngày rework mỗi sprint. Để giải quyết triệt để, AI cần đóng vai trò hỗ trợ có khả năng đa phương thức (**Multimodal**): vừa đọc PRD, vừa nhìn Figma để đối chiếu sự mâu thuẫn và vừa tổng hợp, tóm tắt lại cho Dev hiểu.

---

## 4.4 — Future-State Flow + AI Fit

### AI Fit Check

Bài toán nằm ở: **Complexity (vừa phải) + Ambiguity (cao) → LLM Feature (Multi-modal)**

### AI Suitability Check

- Cần **NLP** (xử lý ngôn ngữ tự nhiên) để hiểu PRD
- Cần **Vision** để nhìn Figma
- Cần khả năng tổng hợp và phát hiện mâu thuẫn chéo (**Cross-reference**)

### UX Check

Nếu AI phân tích sai hoặc thiếu sót $\rightarrow$ Dev vẫn phải tự đọc PRD gốc và hỏi BA (quay về quy trình cũ). Hậu quả không nghiêm trọng.

### Future-State Flow

```text
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Bước 1      │     │ Bước 2           │     │ Bước 3           │
│ Handoff PRD │ ──→ │ 🔵 AI đối chiếu  │ ──→ │ 🔵 AI sinh draft │
│ & Figma     │     │ Text & Image     │     │ Tech Specs & API │
└─────────────┘     └──────────────────┘     └──────────────────┘
                                                       │
                                                       ▼
┌──────────────────┐     ┌─────────────┐     ┌──────────────────┐
│ Bước 6           │     │ Bước 5      │     │ Bước 4           │
│ QA Test Pass 90% │ ←── │ 🟢 Lập trình│ ←── │ 🟢 Dev Review &  │
│ logic nghiệp vụ  │     │ (Coding)    │     │ Confirm Ambiguity│
└──────────────────┘     └─────────────┘     └──────────────────┘
```

**➡️ Fallback:** AI ảo giác/tóm tắt sai → Dev tự đọc PRD gốc (như cũ).

### AI Fit Decision

**Chốt:** LLM Feature (Multi-modal)

#### Vì sao không phải Agent?
Workflow này là tuyến tính một chiều từ BA → Dev. Không cần AI phải tự động lên plan, tự chia task trên Jira hay tự trigger các bước tiếp theo.

#### Vì sao không phải Rule?
Ngôn ngữ PRD không theo quy tắc cố định, bắt buộc phải dùng LLM để hiểu ngữ cảnh.

### Underspecification Check (Những điều chưa rõ)

| Điều chưa rõ | Hậu quả | Cách tìm ra |
|---|---|---|
| **“Tech Specs đủ tốt” là như thế nào?** | AI sinh ra cấu trúc quá chung chung, Dev vẫn không dùng được | Test thử với 1 tính năng nhỏ (Epic nhỏ), đưa cho Dev xem có code từ đó được không |
| **Limit input của LLM** | File PRD quá dài + nhiều ảnh Figma làm tràn Context Window của mô hình | Chia nhỏ tài liệu theo từng User Story để cho AI đọc |



# Phase 5 — EVALUATE

### AI Readiness Checklist

| # | Câu hỏi | Kết quả | Ghi chú |
|---|---|---|---|
| 1 | Có data/input đủ chất lượng? | Yes | Có requirement docs, ticket, acceptance criteria, Figma/wireframe, comment review làm input ban đầu |
| 2 | Có metric rõ? | Yes | Rework từ 2–3 ngày/sprint → < 1 ngày/sprint; bug logic nghiệp vụ giảm ≥ 30% |
| 3 | Sai thì hậu quả có chấp nhận được? | Yes | Nếu AI hiểu sai vẫn có Dev, BA/PO, Design review trước khi code merge hoặc release |
| 4 | User sẵn sàng dùng AI? | Yes | Dev thường muốn có bản technical summary ngắn, list ambiguity, checklist clarify trước khi code |
| 5 | Có resource để maintain? | Not Yet | Cần effort để tích hợp với nơi chứa spec/ticket/Figma và tinh chỉnh prompt/workflow |

### Optimization Check

#### Lợi ích

- Giảm thời gian đọc và tự diễn giải requirement cho Dev
- Giảm số vòng clarify giữa Dev – BA – Design
- Phát hiện sớm điểm mơ hồ trước khi code
- Giảm rework và bug logic nghiệp vụ ở cuối sprint

#### Rủi ro nếu optimize sai

- AI tóm tắt quá “mượt” nhưng bỏ sót một số nghiệp vụ quan trọng
- AI có thể ảo tưởng, tạo phản hồi gây cảm giác hiểu đúng dù requirement vẫn còn mơ hồ
- Dev tin vào summary mà không quay lại đọc source
- Team tối ưu tốc độ handoff nhưng làm giảm chất lượng hiểu bài toán gốc

### Quyết định

**Go (với scope nhỏ)**

### Justify

- Bài toán có workflow rõ, nhiều handoff, bottleneck rõ, rất phù hợp để pilot dưới dạng AI hỗ trợ đọc hiểu và clarify sớm
- Metric đo được và có ngưỡng cụ thể, nên dễ validate pilot thành công hay không
- Sai sót ở giai đoạn này vẫn chịu được vì còn lớp review của con người
- Điểm còn thiếu chủ yếu là resource để tích hợp và maintain, không phải do problem sai hay không đo được

### Scope pilot đề xuất

- Chỉ áp dụng cho **1 loại tài liệu** trước, ví dụ: **PRD + acceptance criteria**
- AI chỉ làm **3 việc**:
  1. Tóm tắt requirement cho Dev
  2. Highlight ambiguity / missing info
  3. Tạo checklist câu hỏi cần clarify
- AI chỉ hỗ trợ QA/BA review, không trực tiếp đưa ra quyết định. QA/BA tự chủ động ra quyết định và đưa ra giải pháp.

### Nếu pilot thất bại

- Quay về **Not Yet**
- Hoặc hạ xuống mức đơn giản hơn: **template handoff + checklist rule-based + summary bán thủ công**
- Hoặc giới hạn AI chỉ còn vai trò **highlight ambiguity**, chưa đụng vào technical summary

### Vì sao quyết định này tốt

Quyết định này tốt vì khi thực thi với scope nhỏ có thể đánh giá sớm và cải thiện workflow cũng như prompt, model.  
Sau khi chạy thử với scope nhỏ, nếu thấy giải pháp chưa thật sự giải được vấn đề thì có thể modify sớm hoặc từ bỏ để tránh lãng phí tài nguyên.