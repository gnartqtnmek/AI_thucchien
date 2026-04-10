# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Thị Quỳnh Trang
**Nhóm:** Nhóm 09 - E403
**Ngày:** 10/04/2026

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> *High cosine similarity (độ tương đồng cosine cao, điểm số gần bằng 1) có nghĩa là hai vector đại diện cho văn bản đang chỉ về gần cùng một hướng trong không gian đa chiều. Về mặt ngữ nghĩa, điều này thể hiện hai đoạn văn bản có nội dung, ý nghĩa và chủ đề rất giống nhau.*

**Ví dụ HIGH similarity:**
- Sentence A: Khách hàng có thể yêu cầu hoàn tiền trong vòng 30 ngày nếu sản phẩm bị lỗi.
- Sentence B: Chính sách cho phép lấy lại tiền mặt sau một tháng nếu hàng hóa hư hỏng.
- Tại sao tương đồng: Dù hai câu sử dụng các từ vựng khác nhau (hoàn tiền/lấy lại tiền mặt, 30 ngày/một tháng), nhưng chúng mang cùng một thông điệp và ngữ nghĩa cốt lõi, do đó vector của chúng sẽ nằm rất sát nhau.

**Ví dụ LOW similarity:**
- Sentence A: Khách hàng có thể yêu cầu hoàn tiền trong vòng 30 ngày nếu sản phẩm bị lỗi.
- Sentence B: Trái Đất quay quanh Mặt Trời theo một quỹ đạo hình elip.
- Tại sao khác: Hai câu nói về hai chủ đề hoàn toàn không liên quan (thương mại/hỗ trợ khách hàng so với thiên văn học), nên các vector đại diện sẽ có hướng lệch nhau rất xa (góc lớn, điểm cosine thấp).

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> *Cosine similarity chỉ đo lường góc (hướng) giữa hai vector để so sánh ngữ nghĩa mà không bị ảnh hưởng bởi độ lớn (chiều dài) của vector. Nhờ đó, nó đánh giá chính xác độ tương đồng giữa một đoạn văn rất dài và một câu tóm tắt rất ngắn, trong khi Euclidean distance sẽ cho khoảng cách sai lệch do chênh lệch số lượng từ.*

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính: Gọi L là độ dài Document (10,000), C là chunk_size (500), và O là overlap (50). Bước nhảy (step) giữa các chunk là: C - O = 500 - 50 = 450 ký tự. Công thức tính tổng số chunk là: N = [(L-O)/(C-O)]*
> *Đáp án: 23*

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> *Khi overlap tăng lên 100, số lượng chunk tăng từ 23 lên 25 vì step giảm từ 450 xuống 400. Overlap lớn giúp giữ ngữ cảnh tại ranh giới chunk, giảm nguy cơ mất ý khi retrieve các câu trả lời nằm sát điểm cắt.*

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Tin tức công nghệ và khoa học Việt Nam (tháng 4/2026)

**Tại sao nhóm chọn domain này?**
> *Bộ dữ liệu có nhiều kiểu câu hỏi khác nhau: factual, procedural, comparative, filter-required và multi-document synthesis. Nội dung có nhiều thực thể và số liệu (thời gian, giá, số lượng, địa điểm), rất phù hợp để đánh giá độ nhạy của chunking strategy lên retrieval. Ngoài ra dữ liệu cùng ngôn ngữ tiếng Việt giúp nhóm so sánh chiến lược trong cùng một điều kiện ngữ nghĩa.*

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|---|---|---:|---|
| 1 | Cơ quan quản lý sẽ giám sát giá dịch vụ Starlink tại Việt Nam | VnExpress | 3638 | `source`, `topic=vien-thong` |
| 2 | Cuộc đấu của hai công cụ AI tại công sở Trung Quốc | VnExpress | 4610 | `source`, `topic=ai` |
| 3 | Nền tảng số hỗ trợ tìm nhà thầu xây dựng | VnExpress | 3767 | `source`, `topic=xay-dung` |
| 4 | Phóng thành công vệ tinh tư nhân Make in Vietnam | VnExpress | 3277 | `source`, `topic=vu-tru` |
| 5 | Phi hành đoàn Artemis II vượt nửa đường về Trái Đất | VnExpress | 3707 | `source`, `topic=vu-tru` |
| 6 | Chính sách doanh nghiệp một người | VnExpress | 3905 | `source`, `topic=khoi-nghiep` |
| 7 | Việt Nam đặt mục tiêu 10 người dân có một người khởi nghiệp | VnExpress | 3491 | `source`, `topic=khoi-nghiep` |
| 8 | Vì sao cờ Mỹ trên Mặt Trăng 'bay' dù thiếu gió? | VnExpress | 5222 | `source`, `topic=vu-tru` |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|-----------------|------|---------------|--------------------------------|
| `source` | str | `data/vu_tru_co_my.txt` | Xác định tài liệu gốc, phục vụ traceability |
| `topic` | str | `vu-tru`, `ai`, `khoi-nghiep` | Hỗ trợ `search_with_filter()` cho query theo chủ đề |
| `doc_id` | str | `vu_tru_co_my` | Gom chunk cùng tài liệu, đánh giá multi-doc coverage |
| `chunk_index` | int | `7` | Debug thứ tự chunk và kiểm tra cắt ngữ cảnh |
| `chunker` | str | `recursive` | So sánh hành vi retrieval giữa các strategy |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| Starlink | FixedSizeChunker (`fixed_size`) | 10 | 408.80 | Trung bình, có thể cắt rời số liệu |
| Starlink | SentenceChunker (`by_sentences`) | 9 | 402.11 | Khá tốt với câu đầy đủ |
| Starlink | RecursiveChunker (`recursive`) | 13 | 278.00 | Tốt, giữ ngữ cảnh theo đoạn |
| AI công sở | FixedSizeChunker (`fixed_size`) | 13 | 400.77 | Trung bình, dễ tách cụm ý dài |
| AI công sở | SentenceChunker (`by_sentences`) | 12 | 381.92 | Tốt cho đoạn mô tả định nghĩa |
| AI công sở | RecursiveChunker (`recursive`) | 16 | 286.25 | Tốt cho câu hỏi so sánh 2 khái niệm |
| Cờ Mỹ trên Mặt Trăng | FixedSizeChunker (`fixed_size`) | 14 | 419.43 | Dễ cắt giữa chi tiết kỹ thuật |
| Cờ Mỹ trên Mặt Trăng | SentenceChunker (`by_sentences`) | 14 | 371.00 | Khá tốt nhưng đôi lúc quá dài |
| Cờ Mỹ trên Mặt Trăng | RecursiveChunker (`recursive`) | 17 | 305.29 | Tốt nhất cho procedural explanation |

### Strategy Của Tôi

**Loại:** RecursiveChunker

**Mô tả cách hoạt động:**
> *Strategy tách theo thứ tự ưu tiên separator: `\n\n` -> `\n` -> `. ` -> ` ` -> fallback theo ký tự. Nếu đoạn hiện tại đã nhỏ hơn `chunk_size` thì trả về ngay; nếu vẫn lớn thì đệ quy với separator nhỏ hơn. Cách này tránh cắt thô theo số ký tự ngay từ đầu, giữ các cụm ý theo đoạn/câu. Khi benchmark em dùng `chunk_size=420` để cân bằng giữa độ phủ và tính mạch lạc.*

**Tại sao tôi chọn strategy này cho domain nhóm?**
> *Domain tin tức có cấu trúc đoạn rõ ràng (mở bài, số liệu, trích dẫn, kết luận), nên recursive tận dụng tốt ranh giới tự nhiên. Với các query procedural và multi-document, recursive giữ được cụm ý đầy đủ hơn fixed-size. Kết quả benchmark cho thấy recursive đạt cùng Precision@3 cao nhất nhưng tốt hơn về source coverage ở query nhiều nguồn.*

**Code snippet (nếu custom):**
```python
# Không dùng custom chunker.
# Sử dụng RecursiveChunker(chunk_size=500)
```

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| Bộ 5 benchmark queries | best baseline: FixedSize | 108 | ~400 | Avg Precision@3 = 0.533, Source Coverage = 0.700 |
| Bộ 5 benchmark queries | **của tôi: Recursive** | 106 | ~305 | Avg Precision@3 = 0.533, Source Coverage = 0.800 |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi | Recursive | 8/10 | Giữ ngữ cảnh tốt, tốt hơn ở query đa nguồn | Q2 còn thiếu top-1 đúng trọng tâm |


**Strategy nào tốt nhất cho domain này? Tại sao?**
> *Recursive là lựa chọn tốt nhất cho bộ dữ liệu này. Lý do là strategy này đạt điểm Precision@3 cao nhất (đồng hạng với fixed-size) nhưng vượt trội về khả năng phủ đủ nhiều nguồn ở query tổng hợp nhiều tài liệu (Q5). Đây là tiêu chí quan trọng với nhóm query mang tính synthesis.*

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> *Em tách câu bằng regex theo các dấu kết thúc phổ biến (`. `, `! `, `? `, `.\n`), sau đó gom lại theo `max_sentences_per_chunk`. Với input rỗng hoặc chỉ whitespace thì trả về list rỗng để tránh chunk rác. Em có xử lý phần đuôi câu còn lại sau vòng lặp để không mất nội dung cuối văn bản.*

**`RecursiveChunker.chunk` / `_split`** — approach:
> *`chunk()` gọi `_split()` theo danh sách separator ưu tiên từ lớn đến nhỏ. Base case: nếu đoạn hiện tại đã <= `chunk_size` thì trả về ngay; nếu hết separator thì fallback cắt cứng theo `chunk_size`. Trong quá trình duyệt split, em gộp dần để chunk không vượt ngưỡng, còn đoạn nào quá dài thì đệ quy cắt sâu hơn.*

### EmbeddingStore

**`add_documents` + `search`** — approach:
> *`add_documents()` embed từng chunk và lưu record gồm `id`, `content`, `metadata`, `embedding` trong in-memory store. `search()` embed query, tính cosine similarity với toàn bộ records, rồi sort giảm dần theo `score`. Em không dùng ngưỡng cứng để tránh rơi mất chunk có thông tin quan trọng nhưng score thấp hơn kỳ vọng.*

**`search_with_filter` + `delete_document`** — approach:
> *`search_with_filter()` filter metadata trước rồi mới tính similarity trên tập đã lọc, giúp tăng precision cho query theo topic. `delete_document()` dùng list comprehension loại các record theo `id` hoặc `metadata['doc_id']`, sau đó so sánh kích thước trước/sau để trả về boolean thành công.*

### KnowledgeBaseAgent

**`answer`** — approach:
> *`answer()` dùng hybrid retrieval: mở rộng query nhiều vế, gom candidates, rerank bằng semantic + lexical + bonus số liệu, sau đó chọn top-k context chunks. Prompt có quy tắc grounding rõ ràng, cấm suy diễn, ưu tiên trích xuất số liệu đúng đơn vị, và tách phí một lần/phí định kỳ. Context được inject kèm nguồn từng tài liệu để tăng khả năng traceability.*

### Test Results

```
=============================================================== test session starts ===============================================================
platform win32 -- Python 3.14.0, pytest-9.0.3, pluggy-1.6.0
rootdir: G:\AI_thucchien\Day-07-Lab-Data-Foundations
collected 42 items

tests/test_solution.py::... PASSED                                                                                                           [100%]

=============================================================== 42 passed in 0.10s ================================================================
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Khách hàng có thể hoàn tiền trong 30 ngày nếu sản phẩm lỗi. | Chính sách cho phép lấy lại tiền trong một tháng khi hàng hỏng. | high | -0.1006 | Sai |
| 2 | Starlink có tối đa 600.000 thuê bao tại Việt Nam. | Mức phí duy trì Starlink là 85 USD mỗi tháng. | high | -0.0170 | Sai |
| 3 | VEGAFLY-1 được phóng bằng Falcon 9. | Sứ mệnh Transporter-16 do SpaceX vận hành. | high | -0.2690 | Sai |
| 4 | Artemis II đáp xuống gần San Diego lúc 20h07. | Dự án anti-distillation skill làm mơ hồ dữ liệu công sở. | low | 0.2309 | Sai |
| 5 | Cờ Mỹ trên Mặt Trăng dùng thanh kim loại ngang. | Việt Nam đặt mục tiêu 5 triệu chủ thể kinh doanh vào 2030. | low | -0.0907 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> *Bất ngờ nhất là Pair 4: hai câu khác domain nhưng score lại dương (0.2309), trong khi nhiều cặp cùng domain lại âm. Điều này cho thấy `_mock_embed` chỉ phù hợp để kiểm thử tính ổn định kỹ thuật, không phản ánh tốt ngữ nghĩa thật. Vì vậy, khi đánh giá retrieval quality nên ưu tiên embedding model thực hoặc thêm bước lexical rerank để ổn định hơn.*

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân của bạn trong package `src`. **5 queries phải trùng với các thành viên cùng nhóm.**

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | Starlink tối đa bao nhiêu thuê bao và giá hàng tháng bao nhiêu? | 600.000 thuê bao; 85 USD/tháng; tháng đầu ~435 USD |
| 2 | Cờ Mỹ được thiết kế thế nào để trông như bay trên Mặt Trăng? | Dùng thanh kim loại ngang ở mép trên + hiệu ứng gợn do nếp gấp/thanh chưa kéo hết |
| 3 | colleague.skill và anti-distillation skill đối lập ra sao? | Một bên trích xuất kỹ năng thành AI Agent, bên kia làm mờ/vô hiệu dữ liệu kỹ năng |
| 4 | VEGAFLY-1 phóng bằng gì, từ đâu, ai vận hành? | Falcon 9; Vandenberg; sứ mệnh Transporter-16 do SpaceX vận hành |
| 5 | Chính sách và mục tiêu khởi nghiệp VN đến 2030/2045? | Mục tiêu số lượng DN + GII + vốn; chính sách hỗ trợ IP, doanh nghiệp một người, thủ tục số |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Starlink thuê bao + giá tháng | Chunk nêu giới hạn 600.000 thuê bao trong giai đoạn thí điểm | 0.5005 | Yes | Trả lời đúng 600.000 và 85 USD/tháng; có thể tách thêm phí tháng đầu |
| 2 | Thiết kế cờ Mỹ trên Mặt Trăng | Chunk mở bài về hiện tượng cờ “bay”, chưa vào cơ chế thanh ngang | 0.4516 | Partial | Trả lời thiếu chi tiết cơ chế nếu chỉ dựa top-1 |
| 3 | colleague.skill vs anti-distillation | Chunk định nghĩa colleague.skill dùng chat/email/tài liệu để tạo AI Agent | 0.3232 | Yes | Trả lời được vế colleague.skill; cần thêm chunk anti-distillation để đầy đủ |
| 4 | VEGAFLY-1 phương tiện/địa điểm/vận hành | Chunk về bối cảnh công nghệ chiến lược, không chứa đầy đủ launch facts | 0.3471 | Partial | Trả lời thiếu nếu không lấy thêm chunk chứa Falcon 9/Transporter-16 |
| 5 | Chính sách & mục tiêu khởi nghiệp 2030/2045 | Chunk về khởi nghiệp chiến lược dài hạn, có dữ liệu mục tiêu | 0.5461 | Yes | Với top-3 có thể tổng hợp được cả mục tiêu lẫn chính sách từ 2 tài liệu |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 4 / 5

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> *Điều em học được là cần tách rõ mục tiêu đo retrieval và mục tiêu đo answer quality. Có bạn ưu tiên chunk lớn để giữ ngữ cảnh, có bạn ưu tiên chunk nhỏ để tăng độ khớp từ khóa; cả hai đều đúng trong ngữ cảnh khác nhau. Việc thêm source coverage vào benchmark giúp nhìn ra hạn chế của chiến lược chỉ tối ưu top-1 score.*

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> *Nhóm khác nhấn mạnh vai trò metadata filter trong query mơ hồ theo chủ đề, đặc biệt với tập tài liệu có từ khóa chồng chéo như “vệ tinh”. Em áp dụng lại bằng cách thêm topic metadata và benchmark Q4 có filter, giúp precision ổn định hơn. Đây là phần cải thiện rõ rệt so với so sánh thủ công ban đầu.*

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> *Em sẽ chuẩn hóa metadata ngay từ đầu (topic, date, author, entity) thay vì thêm dần theo nhu cầu benchmark. Em cũng muốn tách trước các đoạn “fact block” chứa số liệu quan trọng để giảm rủi ro chunk bị cắt nửa câu. Cuối cùng, em sẽ chạy benchmark trên embedding model thực để phản ánh đúng semantic hơn mock embedding.*

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 9 / 10 |
| Chunking strategy | Nhóm | 14 / 15 |
| My approach | Cá nhân | 9 / 10 |
| Similarity predictions | Cá nhân | 4 / 5 |
| Results | Cá nhân | 8 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 4 / 5 |
| **Tổng** | | **83 / 100** |
