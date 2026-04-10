from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []

        parts = re.split(r'(\. |\! |\? |\.\n)', text)
        sentences = []
        temp_sentence = ""
        
        for part in parts:
            temp_sentence += part
            if part in {". ", "! ", "? ", ".\n"}:
                cleaned = temp_sentence.strip()
                if cleaned:
                    sentences.append(cleaned)
                temp_sentence = ""
                
        cleaned_last = temp_sentence.strip()
        if cleaned_last:
            sentences.append(cleaned_last)

        chunks = []
        for i in range(0, len(sentences), self.max_sentences_per_chunk):
            chunk_group = " ".join(sentences[i : i + self.max_sentences_per_chunk])
            chunks.append(chunk_group)
            
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        # Nếu đoạn text đã đủ nhỏ, trả về luôn
        if len(current_text) <= self.chunk_size:
            return [current_text]

        # Nếu đã hết dấu phân cách, chia theo từng ký tự (fallback)
        if not remaining_separators:
            return [current_text[i : i + self.chunk_size] for i in range(0, len(current_text), self.chunk_size)]

        separator = remaining_separators[0]
        next_separators = remaining_separators[1:]

        # Nếu dấu phân cách là "" (ký tự trống), chia chặt theo chunk_size
        if separator == "":
            return [current_text[i : i + self.chunk_size] for i in range(0, len(current_text), self.chunk_size)]

        # Tách text bằng dấu phân cách hiện tại
        splits = current_text.split(separator)
        
        good_chunks = []
        current_chunk = ""

        # Gộp dần các phần lại với nhau sao cho không vượt quá chunk_size
        for s in splits:
            if current_chunk:
                test_chunk = current_chunk + separator + s
            else:
                test_chunk = s
                
            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    good_chunks.append(current_chunk)
                
                # Nếu riêng bản thân đoạn `s` này đã lớn hơn chunk_size, gọi đệ quy để cắt nhỏ nó hơn
                if len(s) > self.chunk_size:
                    good_chunks.extend(self._split(s, next_separators))
                    current_chunk = ""
                else:
                    current_chunk = s

        # Thêm phần còn thừa cuối cùng
        if current_chunk:
            good_chunks.append(current_chunk)

        return good_chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    dot_product = _dot(vec_a, vec_b)
    mag_a = math.sqrt(_dot(vec_a, vec_a))
    mag_b = math.sqrt(_dot(vec_b, vec_b))
    
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
        
    return dot_product / (mag_a * mag_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        # Khởi tạo 3 chiến lược
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size),
            "by_sentences": SentenceChunker(),
            "recursive": RecursiveChunker(chunk_size=chunk_size)
        }
        
        result = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            count = len(chunks)
            avg_length = sum(len(c) for c in chunks) / count if count > 0 else 0
            
            result[name] = {
                "count": count,
                "avg_length": avg_length,
                "chunks": chunks
            }
            
        return result