# AI Thực Chiến — Chương Trình Đào Tạo

**Tổ chức:** VinUniversity  
---

## Giới Thiệu

**AI Thực Chiến** là chương trình đào tạo thực hành chuyên sâu dành cho kỹ sư và lập trình viên muốn xây dựng sản phẩm AI thực tế. Chương trình bao gồm toàn bộ vòng đời phát triển AI: từ gọi API đến triển khai production, từ RAG pipeline đến fine-tuning, từ agent đơn giản đến hệ thống multi-agent phức tạp.

---

## Cấu Trúc Chương Trình

| Ngày | Chủ Đề | Kỹ Năng Chính |
|------|--------|---------------|
| 01 | Nền Tảng LLM API | OpenAI API, streaming, so sánh model, chi phí |
| 02 | Prompt Engineering | System prompt, few-shot, chain-of-thought |
| 03 | RAG Cơ Bản | Embedding, vector store, retrieval |
| 04 | RAG Nâng Cao | Reranking, hybrid search, evaluation |
| 05 | Tool Use & Function Calling | Tool schema, parallel calls, error handling |
| 06 | Xây Dựng Agent | ReAct loop, memory, planning |
| 07 | Multi-Agent Systems | Orchestration, communication, handoff |
| 08 | Evaluation & Testing | LLM-as-judge, benchmark, regression test |
| 09 | Tối Ưu Chi Phí & Latency | Caching, batching, model routing |
| 10 | Fine-tuning | Dataset curation, LoRA, evaluation |
| 11 | Triển Khai Production | FastAPI, Docker, logging, monitoring |
| 12 | Bảo Mật & An Toàn | Prompt injection, guardrails, PII |
| 13 | Voice & Multimodal | Whisper, vision, audio pipeline |
| 14 | Dự Án Tích Hợp | End-to-end product sprint |
| 15 | Demo & Review | Presentation, code review, feedback |

---

## Cấu Trúc Thư Mục

```
AI_thucchien/
├── day_01_llm_api_foundation/
│   ├── template.py          # Bài tập — điền TODO
│   ├── tests/               # Kiểm thử tự động
│   ├── exercises.md         # Câu hỏi và phần phản ánh
│   ├── README.md            # Hướng dẫn ngày học
│   └── solution/            # Nộp bài tại đây
├── day_02_prompt_engineering/
│   └── ...
└── requirements.txt
```

---

## Bắt Đầu

### Yêu Cầu
- Python 3.10+
- OpenAI API key

### Cài Đặt

```bash
git clone <repo-url>
cd AI_thucchien
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
```

### Quy Trình Mỗi Ngày

```bash
cd day_XX_<ten_chu_de>

# Đọc hướng dẫn
cat README.md

# Triển khai các TODO trong template
# (mở template.py trong editor)

# Kiểm tra tiến độ
pytest tests/ -v

# Chạy thử thủ công
python template.py

# Nộp bài
cp template.py solution/solution.py
```

---

## Kiểm Thử

Mỗi ngày đều có bộ kiểm thử tự động dùng mock — **không cần API key thật để chạy tests**.

```bash
pytest tests/ -v          # Chạy tất cả tests
pytest tests/ -k "test_X" # Chạy test cụ thể
```

---

## Tiêu Chí Đánh Giá

| Hạng Mục | Tỉ Lệ |
|----------|-------|
| Tests pass (`pytest`) | 60% |
| Chất lượng triển khai | 25% |
| Bài tập & phản ánh | 15% |

---

## Liên Hệ

**VinUniversity — School of Engineering and Computer Science**  
Hà Nội, Việt Nam
