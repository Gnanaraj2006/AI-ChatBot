import os
import uuid
import time
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, BASE_DIR
from app.models.schemas import (
    DocumentInfo, ChatRequest, ChatResponse,
    FlashcardsRequest, FlashcardsResponse,
    QuizRequest, QuizResponse,
    SummaryRequest, SummaryResponse,
    SettingsUpdateRequest, SystemStatusResponse
)
from app.services.document_parser import DocumentParser
from app.services.text_splitter import TextSplitter
from app.services.embeddings import embeddings_service
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from app.services.rag_engine import rag_engine

# Initialize FastAPI Application
app = FastAPI(
    title=settings.APP_NAME,
    description="Docker-Enabled AI Chatbot for Study Material Q&A on Cloud with Multi-Provider Support",
    version="1.0.0"
)

# Enable CORS for cloud & local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets
static_path = BASE_DIR / "app" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


def is_running_in_docker() -> bool:
    """Detect if running inside Docker container."""
    return os.path.exists("/.dockerenv") or os.environ.get("IS_DOCKER") == "true"


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = BASE_DIR / "app" / "templates" / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>StudySphere AI is initializing...</h1>", status_code=200)
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/health", response_model=SystemStatusResponse)
async def health_check():
    stats = vector_store.get_stats()
    return SystemStatusResponse(
        status="ok",
        app_name=settings.APP_NAME,
        active_provider=settings.DEFAULT_MODEL_PROVIDER,
        is_docker=is_running_in_docker(),
        configured_providers={
            "gemini": bool(settings.GEMINI_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
            "ollama": True,
            "simulation": settings.ENABLE_SIMULATION_MODE
        },
        documents_count=stats["documents_count"],
        total_chunks_count=stats["chunks_count"],
        vector_backend=stats["backend"]
    )


@app.post("/api/upload", response_model=List[DocumentInfo])
async def upload_documents(files: List[UploadFile] = File(...)):
    """Uploads one or more study documents, parses text, splits into chunks, and vectorizes."""
    uploaded_docs: List[DocumentInfo] = []
    text_splitter = TextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)

    for file in files:
        if not file.filename:
            continue

        ext = Path(file.filename).suffix.lower()
        if ext not in DocumentParser.SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}'. Allowed: {', '.join(DocumentParser.SUPPORTED_EXTENSIONS)}"
            )

        doc_id = str(uuid.uuid4())[:8]
        save_path = Path(settings.UPLOAD_DIR) / f"{doc_id}_{file.filename}"

        # Save file to disk
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(save_path)

        # Parse document into pages
        pages = DocumentParser.parse_file(str(save_path))
        chunks = text_splitter.split_pages(doc_id=doc_id, filename=file.filename, pages=pages)

        if not chunks:
            # Fallback single chunk if file is small
            from app.models.schemas import DocumentChunk, ChunkMetadata
            chunks = [DocumentChunk(
                id=f"{doc_id}_0",
                text="Document uploaded successfully.",
                metadata=ChunkMetadata(doc_id=doc_id, filename=file.filename, page_number=1, chunk_index=0)
            )]

        # Generate vector embeddings
        chunk_texts = [c.text for c in chunks]
        embeddings = embeddings_service.embed_texts(chunk_texts)

        doc_info = DocumentInfo(
            id=doc_id,
            filename=file.filename,
            file_type=ext.replace(".", "").upper(),
            file_size_bytes=file_size,
            chunks_count=len(chunks),
            pages_count=len(pages),
            uploaded_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            status="ready"
        )

        vector_store.add_chunks(chunks, embeddings, doc_info)
        uploaded_docs.append(doc_info)

    return uploaded_docs


@app.post("/api/sample/load", response_model=List[DocumentInfo])
async def load_sample_materials():
    """Loads sample study materials (OS Guide & ML Essentials) for immediate exploration."""
    sample_dir = BASE_DIR / "sample_materials"
    if not sample_dir.exists():
        raise HTTPException(status_code=404, detail="Sample materials directory not found.")

    text_splitter = TextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
    results = []

    for sample_file in sample_dir.glob("*.*"):
        if sample_file.suffix.lower() not in DocumentParser.SUPPORTED_EXTENSIONS:
            continue

        # Check if already indexed
        existing = [d for d in vector_store.list_documents() if d.filename == sample_file.name]
        if existing:
            results.append(existing[0])
            continue

        doc_id = str(uuid.uuid4())[:8]
        pages = DocumentParser.parse_file(str(sample_file))
        chunks = text_splitter.split_pages(doc_id=doc_id, filename=sample_file.name, pages=pages)

        chunk_texts = [c.text for c in chunks]
        embeddings = embeddings_service.embed_texts(chunk_texts)

        doc_info = DocumentInfo(
            id=doc_id,
            filename=sample_file.name,
            file_type=sample_file.suffix.replace(".", "").upper(),
            file_size_bytes=sample_file.stat().st_size,
            chunks_count=len(chunks),
            pages_count=len(pages),
            uploaded_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            status="ready"
        )
        vector_store.add_chunks(chunks, embeddings, doc_info)
        results.append(doc_info)

    return results


@app.get("/api/documents", response_model=List[DocumentInfo])
async def get_documents():
    """Lists all active study materials indexed in the vector store."""
    return vector_store.list_documents()


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Deletes a document and its embeddings from the vector store."""
    vector_store.delete_document(doc_id)
    return {"status": "success", "message": f"Document {doc_id} removed"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_query(request: ChatRequest):
    """Retrieves relevant study notes and answers user questions with citations."""
    return rag_engine.answer_query(request)


@app.post("/api/study/flashcards", response_model=FlashcardsResponse)
async def generate_flashcards(request: FlashcardsRequest):
    """Generates active-recall flashcards from uploaded study notes."""
    chunks = vector_store.get_all_chunks_for_docs(request.doc_ids)
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No study materials found. Please upload documents or load sample materials first."
        )

    cards, provider_used = llm_service.generate_flashcards(
        chunks=chunks,
        count=request.count,
        topic=request.topic,
        provider=request.provider,
        api_key=request.api_key
    )

    return FlashcardsResponse(
        topic=request.topic or "Key Concepts",
        flashcards=cards,
        provider_used=provider_used
    )


@app.post("/api/study/quiz", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    """Generates interactive multiple-choice practice questions from study materials."""
    chunks = vector_store.get_all_chunks_for_docs(request.doc_ids)
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No study materials found. Please upload documents or load sample materials first."
        )

    questions, provider_used = llm_service.generate_quiz(
        chunks=chunks,
        count=request.count,
        difficulty=request.difficulty,
        provider=request.provider,
        api_key=request.api_key
    )

    return QuizResponse(
        title=f"Practice Quiz ({request.difficulty.capitalize()})",
        questions=questions,
        provider_used=provider_used
    )


@app.post("/api/study/summary", response_model=SummaryResponse)
async def generate_summary(request: SummaryRequest):
    """Generates structured revision notes with takeaways and exam tips."""
    chunks = vector_store.get_all_chunks_for_docs(request.doc_ids)
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No study materials found. Please upload documents or load sample materials first."
        )

    md, takeaways, tips, provider_used = llm_service.generate_summary(
        chunks=chunks,
        focus_topic=request.focus_topic,
        provider=request.provider,
        api_key=request.api_key
    )

    return SummaryResponse(
        title=f"Revision Guide: {request.focus_topic or 'Comprehensive Summary'}",
        summary_markdown=md,
        key_takeaways=takeaways,
        exam_tips=tips,
        citations=[],
        provider_used=provider_used
    )


@app.get("/api/settings")
async def get_settings():
    """Returns active runtime provider configuration."""
    def mask_key(k: str) -> str:
        if not k:
            return ""
        if len(k) <= 8:
            return "********"
        return k[:4] + "..." + k[-4:]

    return {
        "active_provider": settings.DEFAULT_MODEL_PROVIDER,
        "gemini": {
            "model": settings.GEMINI_MODEL,
            "has_key": bool(settings.GEMINI_API_KEY),
            "masked_key": mask_key(settings.GEMINI_API_KEY)
        },
        "openai": {
            "model": settings.OPENAI_MODEL,
            "has_key": bool(settings.OPENAI_API_KEY),
            "masked_key": mask_key(settings.OPENAI_API_KEY)
        },
        "ollama": {
            "model": settings.OLLAMA_MODEL,
            "base_url": settings.OLLAMA_BASE_URL
        },
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "simulation_enabled": settings.ENABLE_SIMULATION_MODE
    }


@app.post("/api/settings")
async def update_settings(update: SettingsUpdateRequest):
    """Updates runtime provider and keys without server restart."""
    if update.provider:
        settings.DEFAULT_MODEL_PROVIDER = update.provider.lower()
    if update.gemini_api_key is not None:
        settings.GEMINI_API_KEY = update.gemini_api_key.strip()
    if update.gemini_model:
        settings.GEMINI_MODEL = update.gemini_model.strip()
    if update.openai_api_key is not None:
        settings.OPENAI_API_KEY = update.openai_api_key.strip()
    if update.openai_model:
        settings.OPENAI_MODEL = update.openai_model.strip()
    if update.ollama_base_url:
        settings.OLLAMA_BASE_URL = update.ollama_base_url.strip()
    if update.ollama_model:
        settings.OLLAMA_MODEL = update.ollama_model.strip()

    return {"status": "success", "message": "Settings updated successfully"}
