import os
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path


class DocumentParser:
    """Extracts text and page-level metadata from various document formats."""

    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx", ".csv", ".json"}

    @classmethod
    def parse_file(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Parses a file and returns a list of page objects:
        [{"page_number": 1, "text": "...", "page_char_count": 123}]
        """
        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            return cls._parse_pdf(file_path)
        elif ext == ".docx":
            return cls._parse_docx(file_path)
        elif ext in {".txt", ".md", ".markdown", ".csv", ".json"}:
            return cls._parse_text(file_path)
        else:
            # Fallback text reading
            return cls._parse_text(file_path)

    @classmethod
    def _parse_pdf(cls, file_path: str) -> List[Dict[str, Any]]:
        pages = []
        try:
            import pypdf

            reader = pypdf.PdfReader(file_path)
            total_pages = len(reader.pages)
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text = cls._clean_text(text)
                if text.strip():
                    pages.append({
                        "page_number": idx + 1,
                        "text": text,
                        "page_char_count": len(text)
                    })
        except ImportError:
            # Fallback if pypdf is not installed
            raw = cls._read_file_raw(file_path)
            clean = cls._clean_text(raw)
            pages.append({"page_number": 1, "text": clean, "page_char_count": len(clean)})
        except Exception as e:
            # If pdf reading fails, fallback to best-effort raw decode
            raw = cls._read_file_raw(file_path)
            clean = cls._clean_text(raw)
            pages.append({"page_number": 1, "text": clean, "page_char_count": len(clean)})

        if not pages:
            pages.append({"page_number": 1, "text": "(Empty document)", "page_char_count": 16})
        return pages

    @classmethod
    def _parse_docx(cls, file_path: str) -> List[Dict[str, Any]]:
        try:
            import docx

            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())

            # Also parse tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        full_text.append(" | ".join(row_text))

            content = "\n\n".join(full_text)
            content = cls._clean_text(content)
            return [{"page_number": 1, "text": content, "page_char_count": len(content)}]
        except ImportError:
            raw = cls._read_file_raw(file_path)
            return [{"page_number": 1, "text": cls._clean_text(raw), "page_char_count": len(raw)}]

    @classmethod
    def _parse_text(cls, file_path: str) -> List[Dict[str, Any]]:
        raw = cls._read_file_raw(file_path)
        clean = cls._clean_text(raw)
        return [{"page_number": 1, "text": clean, "page_char_count": len(clean)}]

    @classmethod
    def _read_file_raw(cls, file_path: str) -> str:
        for enc in ("utf-8", "latin-1", "cp1252", "utf-16"):
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception:
                break
        # Final fallback with errors ignored
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        # Remove null bytes and strange unprintable control characters
        text = text.replace("\x00", "")
        # Normalize non-breaking spaces
        text = text.replace("\xa0", " ")
        # Collapse multiple empty newlines (> 2) to 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Normalize trailing whitespaces on lines
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
        return text.strip()
