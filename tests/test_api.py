import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app


class TestFastAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("active_provider", data)

    def test_load_sample_and_query(self):
        # 1. Load sample materials
        load_res = self.client.post("/api/sample/load")
        self.assertEqual(load_res.status_code, 200)
        docs = load_res.json()
        self.assertGreater(len(docs), 0)

        # 2. List documents
        docs_res = self.client.get("/api/documents")
        self.assertEqual(docs_res.status_code, 200)
        self.assertGreater(len(docs_res.json()), 0)

        # 3. Test Chat Q&A query
        chat_res = self.client.post("/api/chat", json={
            "query": "What is the difference between processes and threads?",
            "history": [],
            "study_mode": "qa"
        })
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.json()
        self.assertIn("answer", chat_data)
        self.assertGreater(len(chat_data["answer"]), 20)
        self.assertGreater(len(chat_data["citations"]), 0)

    def test_settings_endpoints(self):
        get_res = self.client.get("/api/settings")
        self.assertEqual(get_res.status_code, 200)
        settings_data = get_res.json()
        self.assertIn("active_provider", settings_data)


if __name__ == "__main__":
    unittest.main()
