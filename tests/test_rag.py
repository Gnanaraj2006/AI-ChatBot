import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.document_parser import DocumentParser
from app.services.text_splitter import TextSplitter
from app.services.embeddings import embeddings_service
from app.services.vector_store import vector_store
from app.services.rag_engine import rag_engine
from app.models.schemas import ChatRequest, DocumentInfo


class TestStudySphereRAG(unittest.TestCase):
    def setUp(self):
        self.sample_path = Path("sample_materials/Operating_Systems_Study_Guide.txt")
        self.splitter = TextSplitter(chunk_size=400, chunk_overlap=80)

    def test_document_parser(self):
        pages = DocumentParser.parse_file(str(self.sample_path))
        self.assertGreater(len(pages), 0)
        self.assertIn("PROCESSES AND THREADS", pages[0]["text"])

    def test_text_splitter(self):
        pages = DocumentParser.parse_file(str(self.sample_path))
        chunks = self.splitter.split_pages(
            doc_id="test_os_01",
            filename="Operating_Systems_Study_Guide.txt",
            pages=pages
        )
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].metadata.doc_id, "test_os_01")
        self.assertEqual(chunks[0].metadata.page_number, 1)

    def test_embeddings_service(self):
        query = "What is a deadlock and Banker's algorithm?"
        emb = embeddings_service.embed_query(query)
        self.assertIsInstance(emb, list)
        self.assertGreater(len(emb), 0)

    def test_vector_store_and_search(self):
        pages = DocumentParser.parse_file(str(self.sample_path))
        chunks = self.splitter.split_pages(
            doc_id="test_os_02",
            filename="Operating_Systems_Study_Guide.txt",
            pages=pages
        )
        embeddings = embeddings_service.embed_texts([c.text for c in chunks])

        doc_info = DocumentInfo(
            id="test_os_02",
            filename="Operating_Systems_Study_Guide.txt",
            file_type="TXT",
            file_size_bytes=len(pages[0]["text"]),
            chunks_count=len(chunks),
            pages_count=len(pages),
            uploaded_at="2026-10-19 00:00:00 UTC",
            status="ready"
        )
        vector_store.add_chunks(chunks, embeddings, doc_info)

        # Search for Banker's algorithm
        query_emb = embeddings_service.embed_query("Banker's Algorithm deadlock avoidance")
        results = vector_store.search(query_emb, top_k=2, doc_ids=["test_os_02"])
        self.assertGreater(len(results), 0)
        matched_chunk, score = results[0]
        self.assertIn("test_os_02", matched_chunk.id)

    def test_rag_engine_response(self):
        req = ChatRequest(
            query="What are the 4 Coffman conditions for a deadlock?",
            history=[],
            doc_ids=None,
            study_mode="qa"
        )
        resp = rag_engine.answer_query(req)
        self.assertIsNotNone(resp.answer)
        self.assertGreater(len(resp.answer), 20)
        self.assertIsInstance(resp.citations, list)


if __name__ == "__main__":
    unittest.main()
