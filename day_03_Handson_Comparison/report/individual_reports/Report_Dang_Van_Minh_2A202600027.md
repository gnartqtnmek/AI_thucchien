# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Đặng Văn Minh
- **Student ID**: 2A202600027
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

### Modules Implemented

| Module | Mô tả |
| :--- | :--- |
| `src/chatbot/chatbot.py` | Xây dựng chatbot baseline với system prompt giới hạn domain nhà hàng |
| `src/tools/restaurant_tools.py` | Thêm 4 tools mới: `list_menu`, `list_discounts`, `apply_discount`, `calculate_bill` |
| `src/tools/__init__.py` | Export các tool mới |
| `src/agent/agent.py` | Cập nhật `_plan_actions_v2()` để pre-ground các tool mới; thêm verbose logging |

### Code Highlights

- [Chatbot baseline](https://github.com/dung323123/lab03-e403-04/blob/chatbot_baseline/src/chatbot/chatbot.py)
- [Bổ sung thêm tools](https://github.com/dung323123/lab03-e403-04/commit/9df522c539c3b008777960f1b00494161bfe1eab)
- [Cập nhật mô tả tool](https://github.com/dung323123/lab03-e403-04/commit/35dc4944f161474f2b5309f74df816a1547e0c03)

### Documentation — Cách code tương tác với ReAct Loop

Agent hoạt động theo kiến trúc **ReAct (Reasoning + Acting)**, kết hợp hai giai đoạn xử lý tool.

**Giai đoạn 1 — Pre-grounding**

Trước khi gọi LLM, hàm `_plan_actions_v2()` phân tích câu hỏi bằng regex để đoán trước tool nào cần thiết, sau đó chủ động gọi tool và nạp kết quả vào scratchpad. Mục đích là giảm hallucination — LLM nhận được dữ liệu thực ngay từ đầu thay vì tự đoán.

**Giai đoạn 2 — ReAct Loop**

Nếu dữ liệu pre-ground chưa đủ, LLM tiếp tục sinh các bước theo format:

```
Thought: <lý do>
Action:  <tool_name>(<args>)
```

Hệ thống parse `Action`, thực thi tool, ghi `Observation` vào scratchpad, rồi cho LLM tiếp tục. Vòng lặp dừng khi LLM sinh ra `Final Answer:` hoặc đạt giới hạn bước (`max_steps = 7`).

**Sơ đồ luồng xử lý**

```
User Input
    │
    ▼
_plan_actions_v2()       ← regex phân tích intent
    │
    ▼
Pre-ground tools          ← gọi tool, ghi vào scratchpad
    │
    ▼
┌──────────────────────────────────────┐
│  LLM sinh Thought + Action           │
│       │                              │
│       ▼                              │
│  _parse_action()                     │
│       │                              │
│  ┌────┴─────────────────────────┐    │
│  │ Có Action → _execute_tool() │    │
│  │ ghi Observation              │────┤ lặp lại (max 7 bước)
│  └──────────────────────────────┘    │
│       │                              │
│  Không Action → Final Answer         │
└──────────────────────────────────────┘
    │
    ▼
_enforce_business_rules_v2()   ← kiểm tra rule giao hàng
    │
    ▼
Final Answer → User
```

**Kết quả thực tế**

UC 2: Hôm nay có những món gì và mã giảm giá nào đang áp dụng?
UC 3: Đi 2 người, mua 2 GA2 + 2 Pepsi hay dùng Combo FF2 thì rẻ hơn?
UC 5: Hôm nay thời tiết Hà Nội như thế nào?

| Use Case | Tools pre-ground | Số bước LLM | Kết quả |
| :--- | :--- | :---: | :--- |
| Menu + discount (UC2) | `list_discounts`, `list_menu` | 1 | Đúng |
| Out-of-domain (UC5) | Không có | 1 | Đúng — từ chối |
| So sánh giá (UC3) | `get_item`, `calculate_bill` | 3 | Đúng |

**Điểm quan sát — Cần cải thiện**

- **Regex pre-ground bắt nhầm**: `get_combo('FF2 thì rẻ hơn')` — cần cắt chuỗi sạch hơn trước khi truyền vào tool.
- **Alias FF2 chưa nhận diện được**: Khi LLM gọi `get_combo('Combo FF2')` bị trả về not found, phải fallback sang `get_combo()` để lấy toàn bộ combo, tốn thêm 2 bước không cần thiết.

---

## II. Debugging Case Study (10 Points)

### Problem Description

Agent v2 không thể tra cứu **Combo FF2** dù alias hợp lệ tồn tại trong hệ thống. Khi xử lý UC3 *"Đi 2 người, mua 2 GA2 + 2 Pepsi hay dùng Combo FF2 thì rẻ hơn?"*, agent phải mất 3 bước ReAct thay vì 1, và trả lời đúng số tiền nhưng gọi sai tên combo ("Combo Cặp đôi" thay vì "Combo FF2").

### Log Source

```json
// Pre-ground — regex bắt nhầm args
{"event": "AGENT_TOOL_CALL", "data": {"tool": "get_combo", "args": "FF2 thì rẻ hơn", "ok": false}}

// Step 1 — LLM thử lại với tên hợp lý hơn, vẫn fail
{"event": "AGENT_TOOL_CALL", "data": {"tool": "get_combo", "args": "Combo FF2", "ok": false}}

// Step 2 — LLM fallback: lấy toàn bộ combo
{"event": "AGENT_TOOL_CALL", "data": {"tool": "get_combo", "args": "", "ok": true}}

// Step 3 — Final Answer đúng giá nhưng sai tên combo
{"event": "AGENT_END", "data": {"steps": 3, "final_answer": "...Combo Cặp đôi có giá chỉ 159,000 VND..."}}
```

### Diagnosis

Có **hai bug xảy ra liên tiếp**, cả hai đều thuộc về **tool spec** và **pre-grounding logic**, không phải lỗi của model:

**Bug 1 — Regex pre-ground không có boundary dừng:**

```python
# Pattern hiện tại:
combo_match = re.search(r"combo\s+([\w\sÀ-ỹ]+)", user_input)
# Input: "...hay dùng Combo FF2 thì rẻ hơn?"
# → bắt được toàn bộ: "FF2 thì rẻ hơn"  ← sai
```

**Bug 2 — `_normalize_key()` phá vỡ alias lookup:**

```python
_normalize_key("Combo FF2") → "COMBO_FF2"
COMBO_ALIASES.get("COMBO_FF2") → None   # alias chỉ có key "FF2"
# Tên "Combo FF2" cũng không khớp với name_vi nào → not found
```

Hàm `_normalize_key` nối prefix "COMBO_" vào "FF2" thành "COMBO_FF2", trong khi `COMBO_ALIASES` chỉ định nghĩa key `"FF2"`. Model không sai — nó đã thử cách hợp lý nhất nhưng tool trả về không tìm thấy.

### Solution

**Fix Bug 1** — giới hạn regex chỉ bắt từ đơn liền ngay sau "combo":

```python
# Chỉ bắt 1 token (mã alias) sau "combo"
combo_match = re.search(r"combo\s+([\w]+)", user_input, flags=re.IGNORECASE)
```

**Fix Bug 2** — thêm bước strip prefix trước khi tra alias:

```python
key = _normalize_key(combo_name)            # "COMBO_FF2"
short_key = re.sub(r"^COMBO_", "", key)     # "FF2"
mapped_key = COMBO_ALIASES.get(key) or COMBO_ALIASES.get(short_key, key)
```

Sau fix, `get_combo("Combo FF2")` → `COMBO_FF2` → strip → `FF2` → alias → `C002` → trả về đúng combo trong 1 bước.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning — Thought block giúp ích như thế nào?

Block `Thought` cho phép agent **tự lý luận trước khi hành động**, tránh việc gọi tool bừa bãi. Điều này thể hiện rõ ở UC5:

> *Thought: "Yêu cầu hiện tại không liên quan đến dịch vụ của nhà hàng gà rán"*
> → Không gọi bất kỳ tool nào → Final Answer ngay lập tức.

Trong khi đó, chatbot không có cơ chế lý luận trung gian — nó dựa hoàn toàn vào system prompt để từ chối. Khi system prompt thiếu context (như ở log `09:27:53` với `prompt_tokens: 49`), chatbot trả lời sai hoàn toàn: *"Chúng tôi có các món gà rán, gà nướng, gà xốt cay..."* — đây là **hallucination** vì không có gà nướng hay gà xốt cay trong menu.

Ở UC3, Thought block còn giúp agent **tự phục hồi sau lỗi tool**: sau khi `get_combo('Combo FF2')` thất bại, agent suy luận *"cần giới thiệu lại các combo hiện có"* và fallback sang `get_combo()` thay vì báo lỗi cho người dùng.

### 2. Reliability — Trường hợp Agent tệ hơn Chatbot

| Tiêu chí | Chatbot | Agent v2 |
| :--- | :--- | :--- |
| Latency UC3 | ~1.5s | ~6.5s (3 bước) |
| Token usage UC3 | ~600 tokens | ~5,600 tokens |
| UC4 với context đầy đủ | Đúng (tính được 347,200đ, freeship) | Sai khi tool `get_combo('Gia đình')` fail |
| UC2 khi tool fail | Trả lời từ kiến thức LLM | Trả về "không tìm thấy thông tin" |

Agent thực sự tệ hơn chatbot khi **tool spec không đủ robust**: log lúc `14:45:09` cho thấy agent không tính được bill UC4 vì `get_combo('Gia đình')` trả về not found, trong khi chatbot cùng UC4 (lúc `14:36:32`) tính đúng hoàn toàn nhờ kiến thức nội tại của LLM.

Nghịch lý: agent **phụ thuộc vào tool**, nên khi tool lỗi thì agent thất bại dù model đủ thông minh để tự tính.

### 3. Observation — Feedback ảnh hưởng đến bước tiếp theo

Mỗi `Observation` đóng vai trò là **vòng phản hồi** định hướng lại hành vi của LLM:

- **Observation thành công** → LLM dùng dữ liệu thực, tránh hallucinate số tiền.
- **Observation thất bại** (`ok: false`) → LLM tự điều chỉnh chiến lược, ví dụ từ `get_combo('Combo FF2')` chuyển sang `get_combo()`.
- **Không có Observation** (UC5) → LLM nhận ra không cần tool và kết thúc ngay.

Điều này cho thấy chất lượng của Observation trực tiếp quyết định hiệu quả agent: nếu tool trả về message lỗi mơ hồ, LLM sẽ tốn thêm bước để đoán. Nếu message lỗi rõ ràng (ví dụ: *"Combo 'FF2' not found. Các combo hợp lệ: Combo Cá nhân, Combo Cặp đôi, Combo Gia đình"*), agent có thể phục hồi ngay trong 1 bước.

---

## IV. Future Improvements (5 Points)

### Scalability — Gọi tool song song

Hiện tại pre-grounding gọi tool **tuần tự**, mỗi tool phải đợi tool trước xong. Với hệ thống có nhiều tool độc lập, có thể chạy song song:

```python
import asyncio

async def _pre_ground_async(self, planned_actions):
    tasks = [self._execute_tool_async(name, args) for name, args in planned_actions]
    return await asyncio.gather(*tasks)
```

Với UC2 (gọi cả `list_menu` lẫn `list_discounts`), chạy song song có thể giảm latency pre-ground từ 2x xuống còn 1x.

### Safety — Validate và sanitize tool arguments

Từ bug FF2, nguyên nhân gốc rễ là args không được làm sạch trước khi gọi tool. Cần thêm lớp validation:

```python
def _sanitize_args(self, tool_name: str, args: str) -> str:
    # Với get_combo: chỉ giữ lại token đầu tiên có nghĩa
    if tool_name == "get_combo":
        args = args.split()[0] if args.strip() else ""
    return args.strip()
```

Ngoài ra, cần giới hạn độ dài args để tránh LLM nhồi cả câu hỏi vào tham số tool.

### Performance — Fuzzy matching cho tiếng Việt

Alias mapping hiện tại chỉ hỗ trợ exact match sau normalize. Với ngôn ngữ tự nhiên tiếng Việt, người dùng và LLM có thể dùng nhiều biến thể khác nhau. Giải pháp là thêm fuzzy matching:

```python
from rapidfuzz import process

def _find_combo_fuzzy(query: str) -> Optional[Dict]:
    names = {c["name_vi"]: c for c in COMBOS.values()}
    match, score, _ = process.extractOne(query, names.keys())
    if score >= 80:
        return names[match]
    return None
```

Với ngưỡng similarity 80%, `get_combo("Combo FF2")`, `get_combo("combo cap doi")`, hay `get_combo("cặp đôi")` đều sẽ tìm được đúng combo mà không cần thêm alias thủ công.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
