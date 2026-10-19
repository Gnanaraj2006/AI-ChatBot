from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    chunks_count: int = 0
    pages_count: int = 1
    uploaded_at: str
    status: str = "ready"


class ChunkMetadata(BaseModel):
    doc_id: str
    filename: str
    page_number: int = 1
    chunk_index: int = 0


class DocumentChunk(BaseModel):
    id: str
    text: str
    metadata: ChunkMetadata
    score: Optional[float] = None


class Citation(BaseModel):
    doc_id: str
    filename: str
    page_number: int
    chunk_index: int
    text_snippet: str
    relevance_score: float = 0.0


class ChatMessage(BaseModel):
    role: str = "user"  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    query: str
    history: List[ChatMessage] = []
    doc_ids: Optional[List[str]] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    study_mode: str = "qa"  # "qa" | "eli5" | "exam_prep" | "summary"


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    provider_used: str
    model_used: str
    latency_seconds: float
    simulation_mode: bool = False


class Flashcard(BaseModel):
    id: int
    front: str
    back: str
    source: str = ""
    category: str = "Core Concept"


class FlashcardsRequest(BaseModel):
    doc_ids: Optional[List[str]] = None
    count: int = 5
    topic: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None


class FlashcardsResponse(BaseModel):
    topic: str
    flashcards: List[Flashcard]
    provider_used: str


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    correct_option_index: int
    explanation: str
    source: str = ""


class QuizRequest(BaseModel):
    doc_ids: Optional[List[str]] = None
    count: int = 5
    difficulty: str = "medium"  # "easy" | "medium" | "hard"
    provider: Optional[str] = None
    api_key: Optional[str] = None


class QuizResponse(BaseModel):
    title: str
    questions: List[QuizQuestion]
    provider_used: str


class SummaryRequest(BaseModel):
    doc_ids: Optional[List[str]] = None
    focus_topic: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None


class SummaryResponse(BaseModel):
    title: str
    summary_markdown: str
    key_takeaways: List[str]
    exam_tips: List[str]
    citations: List[Citation] = []
    provider_used: str


class SettingsUpdateRequest(BaseModel):
    provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None


class SystemStatusResponse(BaseModel):
    status: str = "ok"
    app_name: str
    active_provider: str
    is_docker: bool
    configured_providers: Dict[str, bool]
    documents_count: int
    total_chunks_count: int
    vector_backend: str
