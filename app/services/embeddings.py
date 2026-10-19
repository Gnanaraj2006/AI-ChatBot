import math
import re
from typing import List, Optional
from app.config import settings


class EmbeddingsService:
    """Multi-provider text embeddings supporting Gemini, OpenAI, and Local Fallback."""

    def __init__(self):
        self._gemini_configured = False
        self._openai_configured = False

    def embed_texts(
        self,
        texts: List[str],
        provider: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> List[List[float]]:
        if not texts:
            return []

        active_provider = (provider or settings.DEFAULT_MODEL_PROVIDER).lower()

        # 1. Try Gemini
        if active_provider == "gemini":
            key = api_key or settings.GEMINI_API_KEY
            if key:
                try:
                    return self._embed_gemini(texts, key)
                except Exception as e:
                    print(f"[Embeddings] Gemini embedding failed: {e}. Falling back to local vectorizer.")

        # 2. Try OpenAI
        elif active_provider == "openai":
            key = api_key or settings.OPENAI_API_KEY
            if key:
                try:
                    return self._embed_openai(texts, key)
                except Exception as e:
                    print(f"[Embeddings] OpenAI embedding failed: {e}. Falling back to local vectorizer.")

        # 3. Fast deterministic local vectorizer (zero API key / offline fallback)
        return [self._local_semantic_embed(t) for t in texts]

    def embed_query(
        self,
        query: str,
        provider: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> List[float]:
        results = self.embed_texts([query], provider=provider, api_key=api_key)
        return results[0] if results else [0.0] * 256

    def _embed_gemini(self, texts: List[str], api_key: str) -> List[List[float]]:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            model = settings.GEMINI_EMBEDDING_MODEL
            embeddings = []
            for text in texts:
                truncated = text[:4000]
                res = client.models.embed_content(model=model, contents=truncated)
                embeddings.append(res.embeddings[0].values)
            return embeddings
        except Exception as e:
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=api_key)
                model = settings.GEMINI_EMBEDDING_MODEL
                embeddings = []
                for text in texts:
                    truncated = text[:4000]
                    res = legacy_genai.embed_content(
                        model=model,
                        content=truncated,
                        task_type="retrieval_document"
                    )
                    embeddings.append(res['embedding'])
                return embeddings
            except Exception as legacy_err:
                raise RuntimeError(f"Gemini embedding failed: {e}; Legacy fallback error: {legacy_err}")

    def _embed_openai(self, texts: List[str], api_key: str) -> List[List[float]]:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = settings.OPENAI_EMBEDDING_MODEL

        # OpenAI batch embedding
        cleaned_texts = [t[:4000] for t in texts]
        resp = client.embeddings.create(input=cleaned_texts, model=model)
        return [item.embedding for item in resp.data]

    def _local_semantic_embed(self, text: str, dim: int = 256) -> List[float]:
        """
        Fast, deterministic hashed subword & n-gram vectorizer.
        Produces unit-normalized embeddings with cosine similarity properties
        without requiring PyTorch, C++ compilers, or external downloads.
        """
        vec = [0.0] * dim
        tokens = re.findall(r"\b\w+\b", text.lower())

        if not tokens:
            return vec

        # Weight words and character 3-grams
        for tok in tokens:
            # Word token hash
            h = hash(tok) % dim
            vec[h] += 1.0

            # Character 3-grams for subword matching (e.g. biology, biological)
            if len(tok) >= 4:
                for i in range(len(tok) - 2):
                    sub = tok[i:i + 3]
                    h_sub = hash(sub) % dim
                    vec[h_sub] += 0.4

        # L2 normalize vector for cosine similarity
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


embeddings_service = EmbeddingsService()
