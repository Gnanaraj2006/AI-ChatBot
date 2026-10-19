import time
from typing import List, Optional, Dict, Any
from app.config import settings
from app.models.schemas import (
    ChatRequest, ChatResponse, Citation, DocumentChunk
)
from app.services.embeddings import embeddings_service
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service


class RAGEngine:
    """End-to-end Retrieval-Augmented Generation pipeline for Study Materials."""

    STUDY_MODE_PROMPTS = {
        "qa": (
            "You are StudySphere AI, a brilliant university tutor and academic research assistant. "
            "Your mission is to help students thoroughly understand their study materials. "
            "Use the provided context chunks to answer the user's question accurately, with clear explanations. "
            "If the answer is found in the context, be thorough and explain key concepts. "
            "Always cite the source document and page number where appropriate (e.g. [Page X of document]). "
            "If the context does not contain the answer, state that clearly and provide helpful guidance."
        ),
        "eli5": (
            "You are an intuitive teacher who explains complex study topics simply (Explain Like I'm 5). "
            "Break down the material into clear, simple analogies and relatable examples without jargon. "
            "Reference key points from the provided context."
        ),
        "exam_prep": (
            "You are an exam prep coach. Focus on high-yield exam topics, likely exam questions, "
            "core definitions to memorize, formulas, and common pitfalls students make on this topic. "
            "Format your answer with bold headings, bullet points, and high-yield notes."
        ),
        "summary": (
            "You are an academic summarizer. Provide a crisp, structured overview with key definitions, "
            "the core thesis, and bulleted takeaways based directly on the provided context."
        )
    }

    def answer_query(self, request: ChatRequest) -> ChatResponse:
        start_time = time.time()

        # 1. Embed query
        query_emb = embeddings_service.embed_query(
            request.query,
            provider=request.provider,
            api_key=request.api_key
        )

        # 2. Retrieve top-k relevant chunks
        top_k = settings.TOP_K_CHUNKS
        scored_chunks = vector_store.search(
            query_embedding=query_emb,
            top_k=top_k,
            doc_ids=request.doc_ids
        )

        # 3. Build context & citations
        context_blocks = []
        citations: List[Citation] = []

        for chunk, score in scored_chunks:
            meta = chunk.metadata
            snippet = chunk.text[:220] + ("..." if len(chunk.text) > 220 else "")
            citations.append(Citation(
                doc_id=meta.doc_id,
                filename=meta.filename,
                page_number=meta.page_number,
                chunk_index=meta.chunk_index,
                text_snippet=snippet,
                relevance_score=round(score, 3)
            ))

            context_blocks.append(
                f"[Source: {meta.filename} | Page {meta.page_number} | Score: {round(score, 2)}]:\n{chunk.text}"
            )

        formatted_context = "\n\n---\n\n".join(context_blocks)

        # 4. Craft system prompt
        base_instruction = self.STUDY_MODE_PROMPTS.get(request.study_mode, self.STUDY_MODE_PROMPTS["qa"])
        system_prompt = (
            f"{base_instruction}\n\n"
            f"--- CONTEXT START ---\n"
            f"{formatted_context}\n"
            f"--- CONTEXT END ---\n"
            "Answer the student's question based on the context above."
        )

        # 5. Execute LLM completion
        history_dicts = [{"role": m.role, "content": m.content} for m in request.history]

        answer_text, provider_used, model_used, is_sim = llm_service.complete(
            system_prompt=system_prompt,
            user_prompt=request.query,
            history=history_dicts,
            provider=request.provider,
            api_key=request.api_key
        )

        latency = round(time.time() - start_time, 2)

        return ChatResponse(
            answer=answer_text,
            citations=citations,
            provider_used=provider_used,
            model_used=model_used,
            latency_seconds=latency,
            simulation_mode=is_sim
        )


rag_engine = RAGEngine()
