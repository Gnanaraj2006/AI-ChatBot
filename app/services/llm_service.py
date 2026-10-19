import os
import re
import json
import httpx
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings
from app.models.schemas import Flashcard, QuizQuestion, Citation, DocumentChunk


class LLMService:
    """Multi-provider LLM orchestration supporting Gemini, OpenAI, Ollama, and Heuristic Fallback."""

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Tuple[str, str, str, bool]:
        """
        Executes a completion across available providers.
        Returns: (answer_text, provider_used, model_used, is_simulation)
        """
        active_provider = (provider or settings.DEFAULT_MODEL_PROVIDER).lower()

        # 1. Google Gemini
        if active_provider == "gemini":
            key = api_key or settings.GEMINI_API_KEY
            if key:
                try:
                    ans, model = self._complete_gemini(system_prompt, user_prompt, history, key, model_name)
                    return ans, "Google Gemini", model, False
                except Exception as e:
                    print(f"[LLM] Gemini call failed: {e}. Falling back.")

        # 2. OpenAI
        elif active_provider == "openai":
            key = api_key or settings.OPENAI_API_KEY
            if key:
                try:
                    ans, model = self._complete_openai(system_prompt, user_prompt, history, key, model_name)
                    return ans, "OpenAI", model, False
                except Exception as e:
                    print(f"[LLM] OpenAI call failed: {e}. Falling back.")

        # 3. Ollama
        elif active_provider == "ollama":
            try:
                ans, model = self._complete_ollama(system_prompt, user_prompt, history, model_name)
                return ans, "Ollama Local", model, False
            except Exception as e:
                print(f"[LLM] Ollama call failed: {e}. Falling back.")

        # 4. Fallback if user selected a provider without providing key, or key failed
        # Try any configured provider
        if settings.GEMINI_API_KEY:
            try:
                ans, model = self._complete_gemini(system_prompt, user_prompt, history, settings.GEMINI_API_KEY, None)
                return ans, "Google Gemini", model, False
            except Exception:
                pass

        if settings.OPENAI_API_KEY:
            try:
                ans, model = self._complete_openai(system_prompt, user_prompt, history, settings.OPENAI_API_KEY, None)
                return ans, "OpenAI", model, False
            except Exception:
                pass

        # 5. Intelligent Simulation Fallback Mode
        ans = self._simulate_chat_response(user_prompt, system_prompt)
        return ans, "Simulation Engine (Offline Mode)", "Heuristic-RAG-v1", True

    def _complete_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]],
        api_key: str,
        model_name: Optional[str]
    ) -> Tuple[str, str]:
        model_id = model_name or settings.GEMINI_MODEL
        if not model_id or any(old in model_id for old in ["gemini-1.5", "gemini-2.0", "gemini-2.5"]):
            model_id = "gemini-3.8-flash"

        # 1. Try modern google.genai SDK
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            full_contents = []
            if history:
                for msg in history[-6:]:
                    full_contents.append(f"{msg.get('role', 'user')}: {msg.get('content', '')}")
            full_contents.append(f"user: {user_prompt}")
            combined_prompt = "\n\n".join(full_contents)

            resp = client.models.generate_content(
                model=model_id,
                contents=combined_prompt,
                config={"system_instruction": system_prompt}
            )
            return resp.text, model_id
        except Exception as e:
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=api_key)
                model = legacy_genai.GenerativeModel(
                    model_name=model_id,
                    system_instruction=system_prompt
                )
                chat_history = []
                if history:
                    for msg in history[-6:]:
                        role = "user" if msg.get("role") == "user" else "model"
                        chat_history.append({"role": role, "parts": [msg.get("content", "")]})
                chat = model.start_chat(history=chat_history)
                resp = chat.send_message(user_prompt)
                return resp.text, model_id
            except Exception as legacy_err:
                raise RuntimeError(f"Gemini generation failed: {e}; Legacy error: {legacy_err}")

    def _complete_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]],
        api_key: str,
        model_name: Optional[str]
    ) -> Tuple[str, str]:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model_id = model_name or settings.OPENAI_MODEL

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history[-6:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": user_prompt})

        resp = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.3
        )
        return resp.choices[0].message.content or "", model_id

    def _complete_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]],
        model_name: Optional[str]
    ) -> Tuple[str, str]:
        model_id = model_name or settings.OLLAMA_MODEL
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"

        prompt = f"System: {system_prompt}\n\n"
        if history:
            for h in history[-4:]:
                prompt += f"{h.get('role', 'User')}: {h.get('content', '')}\n"
        prompt += f"User: {user_prompt}\nAssistant: "

        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, json={
                "model": model_id,
                "prompt": prompt,
                "stream": False
            })
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", ""), model_id

    def generate_flashcards(
        self,
        chunks: List[DocumentChunk],
        count: int = 5,
        topic: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Tuple[List[Flashcard], str]:
        combined_text = "\n\n".join([f"[{c.metadata.filename} - P.{c.metadata.page_number}]: {c.text}" for c in chunks[:8]])

        sys_prompt = (
            "You are an expert study assistant. Generate high-yield study flashcards based ONLY on the provided material. "
            f"Generate exactly {count} flashcards. "
            "Output valid JSON ONLY in this format: "
            '[{"id": 1, "front": "Question/Term", "back": "Clear concise answer/explanation", "source": "Source doc", "category": "Topic"}]'
        )
        user_prompt = f"Topic focus: {topic or 'Key Concepts'}\n\nMaterial:\n{combined_text}"

        raw_output, provider_used, _, is_sim = self.complete(
            sys_prompt, user_prompt, provider=provider, api_key=api_key
        )

        cards = []
        if not is_sim:
            try:
                # Extract JSON array
                json_match = re.search(r"\[.*\]", raw_output, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    for idx, item in enumerate(parsed):
                        cards.append(Flashcard(
                            id=idx + 1,
                            front=item.get("front", f"Concept {idx+1}"),
                            back=item.get("back", "Key explanation"),
                            source=item.get("source", "Study Material"),
                            category=item.get("category", "General")
                        ))
                    if cards:
                        return cards[:count], provider_used
            except Exception as e:
                print(f"[LLM] Error parsing LLM flashcards JSON: {e}")

        # Fallback heuristic flashcard generator
        return self._heuristic_flashcards(chunks, count), "Simulation Engine (Offline)"

    def generate_quiz(
        self,
        chunks: List[DocumentChunk],
        count: int = 5,
        difficulty: str = "medium",
        provider: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Tuple[List[QuizQuestion], str]:
        combined_text = "\n\n".join([f"[{c.metadata.filename} - P.{c.metadata.page_number}]: {c.text}" for c in chunks[:8]])

        sys_prompt = (
            f"You are a university professor creating a {difficulty} exam quiz. "
            f"Generate {count} multiple choice questions strictly based on the text. "
            "Return valid JSON ONLY with this structure: "
            '[{"id": 1, "question": "...", "options": ["A", "B", "C", "D"], "correct_option_index": 0, "explanation": "Why correct...", "source": "Source ref"}]'
        )
        user_prompt = f"Study Material:\n{combined_text}"

        raw_output, provider_used, _, is_sim = self.complete(
            sys_prompt, user_prompt, provider=provider, api_key=api_key
        )

        questions = []
        if not is_sim:
            try:
                json_match = re.search(r"\[.*\]", raw_output, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    for idx, q in enumerate(parsed):
                        questions.append(QuizQuestion(
                            id=idx + 1,
                            question=q.get("question", "Question text"),
                            options=q.get("options", ["Option 1", "Option 2", "Option 3", "Option 4"]),
                            correct_option_index=int(q.get("correct_option_index", 0)),
                            explanation=q.get("explanation", "Reference to study text."),
                            source=q.get("source", "Study Notes")
                        ))
                    if questions:
                        return questions[:count], provider_used
            except Exception as e:
                print(f"[LLM] Error parsing LLM quiz JSON: {e}")

        return self._heuristic_quiz(chunks, count), "Simulation Engine (Offline)"

    def generate_summary(
        self,
        chunks: List[DocumentChunk],
        focus_topic: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Tuple[str, List[str], List[str], str]:
        """Returns: (markdown_summary, key_takeaways, exam_tips, provider_used)"""
        combined_text = "\n\n".join([f"[{c.metadata.filename} - P.{c.metadata.page_number}]: {c.text}" for c in chunks[:10]])

        sys_prompt = (
            "You are an academic tutor preparing an executive revision guide. "
            "Structure your output cleanly with Markdown headers, bullet points, and key definitions. "
            "At the end of your response, output two JSON sections formatted as:\n"
            "```json\n"
            '{"key_takeaways": ["Point 1", "Point 2"], "exam_tips": ["Tip 1", "Tip 2"]}\n'
            "```"
        )
        user_prompt = f"Focus Topic: {focus_topic or 'Comprehensive Overview'}\n\nStudy Material:\n{combined_text}"

        raw_output, provider_used, _, is_sim = self.complete(
            sys_prompt, user_prompt, provider=provider, api_key=api_key
        )

        if not is_sim and raw_output:
            takeaways = []
            tips = []
            try:
                match = re.search(r"```json\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
                if match:
                    meta = json.loads(match.group(1))
                    takeaways = meta.get("key_takeaways", [])
                    tips = meta.get("exam_tips", [])
                    # Clean out the json code block from the markdown
                    clean_md = raw_output[:match.start()].strip()
                    return clean_md, takeaways, tips, provider_used
            except Exception:
                pass
            return raw_output, ["Review fundamental principles", "Understand underlying definitions"], ["Focus on formulas and key distinctions"], provider_used

        # Heuristic summary
        md, takeaways, tips = self._heuristic_summary(chunks, focus_topic)
        return md, takeaways, tips, "Simulation Engine (Offline)"

    # --- Heuristic Fallback Generators ---

    def _simulate_chat_response(self, query: str, system_prompt: str) -> str:
        # Extract context provided in system prompt
        context_match = re.search(r"--- CONTEXT START ---\s*(.*?)\s*--- CONTEXT END ---", system_prompt, re.DOTALL)
        context = context_match.group(1) if context_match else ""

        if not context.strip():
            return (
                "👋 **Welcome to StudySphere AI!**\n\n"
                "I haven't found any uploaded study materials yet, or no relevant sections matched your query.\n\n"
                "💡 **Quick Start Guide:**\n"
                "1. Click **'Upload Study Materials'** in the left sidebar to add your lecture notes, textbooks, or syllabus (PDF, DOCX, TXT).\n"
                "2. Or click the **'Load Sample Study Material'** button to explore with preloaded Computer Science & ML notes!\n"
                "3. Configure your **Google Gemini** or **OpenAI API key** in the Settings modal (⚙️) for full generative answers."
            )

        # Smart extraction from context
        sentences = re.split(r"(?<=[.!?])\s+", context)
        q_words = set(re.findall(r"\b\w{3,}\b", query.lower()))

        scored_sentences = []
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 25:
                continue
            s_words = set(re.findall(r"\b\w{3,}\b", s_clean.lower()))
            overlap = len(q_words.intersection(s_words))
            if overlap > 0:
                scored_sentences.append((s_clean, overlap))

        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in scored_sentences[:4]]

        if top_sentences:
            synthesis = " ".join(top_sentences)
            return (
                f"### Analysis & Key Insights\n\n"
                f"Based on your uploaded study notes:\n\n"
                f"> {synthesis}\n\n"
                f"**Key Concepts Identified:**\n"
                f"- Relevant principles matched directly against query parameters: *{', '.join(list(q_words)[:4])}*.\n"
                f"- For detailed exam review, refer to the cited source blocks below.\n\n"
                f"*(Note: Running in high-precision semantic simulation mode. Connect your Gemini or OpenAI API key in Settings for full free-form synthesis!)*"
            )

        return (
            f"Based on the reviewed documents, here is relevant context regarding your query:\n\n"
            f"{context[:450]}...\n\n"
            f"*Tip: Connect your Gemini or OpenAI API key in Settings for deep creative explanations.*"
        )

    def _heuristic_flashcards(self, chunks: List[DocumentChunk], count: int) -> List[Flashcard]:
        cards = []
        card_id = 1
        for chunk in chunks:
            # Look for lines with ":" or "-" or "is" or "defined as"
            lines = chunk.text.split("\n")
            for line in lines:
                line = line.strip()
                if ":" in line and len(line) > 20:
                    parts = line.split(":", 1)
                    term, definition = parts[0].strip(), parts[1].strip()
                    if 3 <= len(term) <= 50 and len(definition) > 15:
                        cards.append(Flashcard(
                            id=card_id,
                            front=f"What is {term}?",
                            back=definition,
                            source=f"{chunk.metadata.filename} (Page {chunk.metadata.page_number})",
                            category="Definitions"
                        ))
                        card_id += 1
                        if len(cards) >= count:
                            return cards

        # If not enough definitions found, generate conceptual cards from chunks
        for chunk in chunks:
            sentences = [s.strip() for s in chunk.text.split(".") if len(s.strip()) > 30]
            if sentences:
                cards.append(Flashcard(
                    id=card_id,
                    front=f"Explain: {sentences[0][:60]}...",
                    back=chunk.text[:200] + "...",
                    source=f"{chunk.metadata.filename} (Page {chunk.metadata.page_number})",
                    category="Key Concept"
                ))
                card_id += 1
                if len(cards) >= count:
                    break

        if not cards:
            cards.append(Flashcard(
                id=1,
                front="Study Material Overview",
                back="Upload lecture slides, textbooks, or notes to automatically generate active-recall flashcards.",
                source="System",
                category="General"
            ))
        return cards

    def _heuristic_quiz(self, chunks: List[DocumentChunk], count: int) -> List[QuizQuestion]:
        questions = []
        qid = 1

        for chunk in chunks:
            sentences = [s.strip() for s in chunk.text.split(".") if len(s.strip()) > 35]
            if len(sentences) >= 2:
                target = sentences[0]
                words = re.findall(r"\b[A-Za-z]{4,}\b", target)
                if words:
                    key_word = words[0]
                    masked_q = target.replace(key_word, "______", 1)
                    options = [
                        key_word,
                        f"Non-{key_word.lower()}",
                        f"Pseudo-{key_word.lower()}",
                        f"Static {key_word.lower()}"
                    ]
                    questions.append(QuizQuestion(
                        id=qid,
                        question=f"Fill in the blank based on your notes:\n'{masked_q}'",
                        options=options,
                        correct_option_index=0,
                        explanation=f"According to {chunk.metadata.filename}: '{target}'",
                        source=f"{chunk.metadata.filename} (Page {chunk.metadata.page_number})"
                    ))
                    qid += 1
                    if len(questions) >= count:
                        return questions

        if not questions:
            questions.append(QuizQuestion(
                id=1,
                question="What is the primary function of StudySphere AI?",
                options=[
                    "Retrieval-Augmented Generation for study materials",
                    "A video editor",
                    "A spreadsheet calculator",
                    "An image compressor"
                ],
                correct_option_index=0,
                explanation="StudySphere AI indexes study documents and enables conversational Q&A, flashcards, and quizzes.",
                source="System"
            ))
        return questions

    def _heuristic_summary(self, chunks: List[DocumentChunk], focus_topic: Optional[str]) -> Tuple[str, List[str], List[str]]:
        topic = focus_topic or "Uploaded Study Materials"
        md = f"## Comprehensive Revision Notes: {topic}\n\n"

        takeaways = []
        tips = [
            "Review core definitions and their distinguishing characteristics.",
            "Practice explaining the primary mechanisms in your own words.",
            "Verify all source references cited during revision."
        ]

        for idx, chunk in enumerate(chunks[:4]):
            first_line = chunk.text.split("\n")[0][:80]
            md += f"### Section {idx+1}: {chunk.metadata.filename} (Page {chunk.metadata.page_number})\n\n"
            md += f"{chunk.text[:350]}...\n\n"
            takeaways.append(first_line)

        return md, takeaways[:5], tips


llm_service = LLMService()
