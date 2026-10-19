import re
import uuid
from typing import List, Dict, Any
from app.models.schemas import DocumentChunk, ChunkMetadata


class TextSplitter:
    """
    Intelligent recursive text splitter that respects paragraph and sentence
    boundaries while ensuring semantic continuity for study materials.
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_pages(
        self,
        doc_id: str,
        filename: str,
        pages: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """
        Takes parsed pages and generates indexed DocumentChunks with page citations.
        """
        all_chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page in pages:
            page_num = page.get("page_number", 1)
            text = page.get("text", "").strip()

            if not text:
                continue

            page_raw_chunks = self._split_text(text)
            for raw_chunk in page_raw_chunks:
                clean_chunk = raw_chunk.strip()
                if len(clean_chunk) < 20:  # Skip tiny noise fragments
                    continue

                chunk_id = f"{doc_id}_{global_chunk_idx}"
                metadata = ChunkMetadata(
                    doc_id=doc_id,
                    filename=filename,
                    page_number=page_num,
                    chunk_index=global_chunk_idx
                )

                all_chunks.append(DocumentChunk(
                    id=chunk_id,
                    text=clean_chunk,
                    metadata=metadata
                ))
                global_chunk_idx += 1

        return all_chunks

    def _split_text(self, text: str) -> List[str]:
        """
        Recursively breaks text using hierarchical separators:
        [\n\n, \n, . , ! , ? , ; , ' ', '']
        """
        if len(text) <= self.chunk_size:
            return [text]

        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", " ", ""]
        return self._recursive_split(text, separators)

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        final_chunks: List[str] = []

        if not separators:
            return [text]

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator == "":
            splits = list(text)
        else:
            splits = text.split(separator)

        good_splits: List[str] = []
        for s in splits:
            if not s:
                continue
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                other_chunks = self._recursive_split(s, remaining_separators)
                final_chunks.extend(other_chunks)

        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)

        return final_chunks

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        docs: List[str] = []
        current_doc: List[str] = []
        total = 0

        for s in splits:
            s_len = len(s)
            sep_len = len(separator) if current_doc else 0

            if total + s_len + sep_len > self.chunk_size and current_doc:
                merged = separator.join(current_doc)
                docs.append(merged)

                # Keep overlap from the end of current_doc
                while total > self.chunk_overlap and len(current_doc) > 1:
                    popped = current_doc.pop(0)
                    total -= len(popped) + len(separator)

            current_doc.append(s)
            total += s_len + (len(separator) if len(current_doc) > 1 else 0)

        if current_doc:
            docs.append(separator.join(current_doc))

        return docs
