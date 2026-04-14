# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Thị Quỳnh Trang
**Vai trò trong nhóm:** Retrieval Owner
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Trong lab này, tôi tập trung ở Sprint 1 và Sprint 3 với vai trò Retrieval Owner. Ở Sprint 1, tôi chuẩn hóa indexing: preprocess tài liệu, chunk theo section, và đặt tham số chunk_size 400, overlap 80 để hạn chế cắt ngang điều khoản. Tôi cũng thống nhất metadata gồm source, section, department, effective_date, access để hỗ trợ lọc và trích dẫn. Sang Sprint 3, tôi triển khai các preset retrieval trong rag_answer.py: baseline_dense, variant_hybrid, cùng cơ chế hợp nhất dense + sparse bằng Reciprocal Rank Fusion. Tôi phối hợp với Eval Owner map lỗi từ scorecard về retrieval stage, rồi chốt top_k_search = 10 và top_k_select = 3 nhằm cân bằng recall và độ sạch context. Công việc của tôi kết nối trực tiếp với phần generation vì chất lượng context quyết định grounded answer.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Sau lab này, tôi hiểu rõ hơn hai khái niệm: chunking có chủ đích và hybrid retrieval. Trước đây tôi nghĩ chunking chỉ là chia đều theo độ dài, nhưng khi làm thật mới thấy tách theo section giúp giữ trọn ngữ nghĩa điều khoản, nhất là với policy có câu điều kiện dài. Nếu chunk bị cắt sai điểm, model vẫn “faithful” nhưng trả lời thiếu ý hoặc mơ hồ. Với hybrid retrieval, tôi hiểu giá trị của việc kết hợp dense (semantic) và sparse/BM25 (keyword) khi corpus có cả ngôn ngữ tự nhiên lẫn token đặc thù như P1, Level 3, ERR-403. Dense mạnh ở paraphrase, còn sparse mạnh ở exact term. Trước lab tôi xem chúng như hai lựa chọn thay thế; sau lab tôi nhìn chúng như hai tín hiệu bổ sung cần trộn có kiểm soát bằng weighting và ranking.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Điều làm tôi ngạc nhiên là baseline có faithfulness rất cao (5.00) nhưng relevance/completeness vẫn chưa tốt (3.90 và 3.80). Ban đầu tôi giả thuyết lỗi nằm ở generation prompt, nhưng khi soi log retrieval thì thấy nhiều câu vướng ở bước chọn evidence: context đúng nhưng chưa “đúng trọng tâm”, hoặc chứa hai mảnh thông tin gần đúng gây nhiễu. Khó khăn debug lớn nhất là các lỗi không vỡ hẳn pipeline mà chỉ giảm chất lượng tinh tế, nên cần đọc từng cặp query-context-answer thay vì nhìn điểm trung bình. Ví dụ có câu model không bịa gì (faithful cao) nhưng trả lời quá an toàn hoặc thiếu điều kiện, làm completeness tụt. Thực tế này giúp tôi đổi thói quen: không đánh giá retrieval chỉ bằng recall, mà kiểm tra thêm mức độ quyết định của top chunk với câu trả lời cuối.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** q02 - "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?"

**Phân tích:**

Ở baseline_dense, câu này đạt Faithful 5, Relevant 4, Recall 5, Complete 4. Điểm không thấp, nhưng câu trả lời còn mơ hồ vì context retrieve có nhiều mảnh gần nhau về policy refund và model tổng hợp theo hướng chưa dứt khoát. Nhìn từ expected answer, chi tiết quan trọng là mốc thời gian “7 ngày làm việc kể từ thời điểm xác nhận đơn hàng”. Baseline trả lời vẫn bám tài liệu, nhưng chưa tối ưu mức chính xác ngữ cảnh cho người dùng cuối.

Ở variant_hybrid, câu q02 tăng lên 5 ở cả Relevance và Completeness (Faithful 5, Recall 5 giữ nguyên). Điều này cho thấy cải thiện chủ yếu không nằm ở generation mà ở retrieval/ranking: hybrid ưu tiên đúng đoạn chứa phrasing trực tiếp cho truy vấn “bao nhiêu ngày”, nên context vào prompt gọn và nhất quán hơn. Tôi kết luận lỗi gốc của baseline là chất lượng chọn evidence ở lớp retrieval (precision của top chunks), không phải indexing vì nguồn vẫn được lấy đúng, và cũng không phải hallucination vì faithfulness vốn đã cao.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."

Nếu có thêm thời gian, tôi sẽ thử hai cải tiến cụ thể. Thứ nhất, bật rerank nhẹ sau hybrid (top_k_search 15, rerank về top_k_select 3) vì scorecard cho thấy nhiều câu đúng nguồn nhưng chưa chọn được chunk “đinh” nhất để trả lời gọn. Thứ hai, bổ sung metadata-aware retrieval (ưu tiên effective_date mới nhất cho policy) vì các câu refund dễ gặp nhiều câu gần nghĩa, dẫn đến trả lời đúng nhưng thiếu sắc nét. Tôi kỳ vọng cải thiện relevance/completeness mà vẫn giữ faithfulness ổn định.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
