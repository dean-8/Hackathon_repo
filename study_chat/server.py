"""Secure Gemini study-chat backend. API key stays in .env — never sent to the browser."""
import json
import os
import random
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _clear_localhost_proxy_env() -> None:
    """IDE/sandbox tools may set a localhost proxy that is not running (causes Errno 61)."""
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        val = os.environ.get(var, "")
        if val and ("127.0.0.1" in val or "localhost" in val):
            print(f"[GEMINI DEBUG] removing broken proxy env {var}={val}")
            os.environ.pop(var, None)


_clear_localhost_proxy_env()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".csv", ".json",
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".doc", ".docx", ".ppt", ".pptx",
}

SYSTEM_INSTRUCTION = """You are a friendly study planning assistant for a learning game app.

Your role:
- Help the user clarify what they want to study (subject, goals, level, timeline, exam type, etc.)
- Ask thoughtful follow-up questions — one or two at a time, not a long interrogation
- When they upload study materials, read them and ask questions grounded in that content
- Suggest what topics might be worth turning into practice questions later

Internet / web search:
- You only have web access when the user's message says internet is ENABLED
- If internet is DISABLED, do not claim to have searched the web; rely on the conversation and uploaded files only
- If internet is ENABLED, you may use search to supplement answers

Tone: warm, concise, encouraging. Keep replies focused."""

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
# Persisted study topic so the game can read the latest context after chat updates.
CONTEXT_FILE = BASE_DIR.parent / "study_context.json"

app = FastAPI(title="Study Chat", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, dict] = {}
_ready_for_game = False
_study_session_id: str | None = None
_study_context: str | None = None
_study_focus: str | None = None
_asked_revision_questions: list[str] = []
_last_study_focus_for_questions: str | None = None


def _load_study_context_file() -> None:
    """Load persisted study context from disk (only when memory is empty)."""
    global _study_context, _study_focus, _study_session_id
    if _study_context:
        return
    if not CONTEXT_FILE.exists():
        return
    try:
        data = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        _study_context = data.get("study_context") or _study_context
        _study_focus = data.get("study_focus") or _study_focus
        if data.get("session_id"):
            _study_session_id = data["session_id"]
        print(
            "[REVISION DEBUG] loaded context from disk:",
            repr((_study_context or "")[:120]),
            "| focus:",
            repr((_study_focus or "")[:80]),
        )
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[REVISION DEBUG] could not load {CONTEXT_FILE}: {exc}")


def _save_study_context_file() -> None:
    """Write current study context so the game can read it even if server memory is stale."""
    if not _study_context:
        return
    try:
        CONTEXT_FILE.write_text(
            json.dumps(
                {
                    "study_context": _study_context,
                    "study_focus": _study_focus,
                    "session_id": _study_session_id,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "[REVISION DEBUG] saved context to disk:",
            repr(_study_context[:120]),
            "| focus:",
            repr((_study_focus or "")[:80]),
        )
    except OSError as exc:
        print(f"[REVISION DEBUG] could not save {CONTEXT_FILE}: {exc}")


def _sync_study_context(session_id: str | None) -> None:
    """Store full study context and the latest specific user focus."""
    global _study_context, _study_focus
    global _last_study_focus_for_questions, _asked_revision_questions
    if not session_id or session_id not in _sessions:
        return
    session = _sessions[session_id]
    user_lines = [t["text"].strip() for t in session.get("turns", []) if t["role"] == "user" and t["text"].strip()]
    if user_lines:
        new_focus = user_lines[-1]
        if _last_study_focus_for_questions and _last_study_focus_for_questions != new_focus:
            _asked_revision_questions = []
            print("[REVISION DEBUG] topic changed — cleared asked-question cache")
        _last_study_focus_for_questions = new_focus
        _study_context = "\n".join(user_lines)
        _study_focus = new_focus
        session["study_context"] = _study_context
        session["study_focus"] = _study_focus
        print(
            "[REVISION DEBUG] synced context from chat:",
            repr(_study_context[:120]),
            "| focus:",
            repr(_study_focus[:80]),
        )
        _save_study_context_file()


_gemini_client: genai.Client | None = None

GEMINI_UNAVAILABLE_REPLY = (
    "Gemini is unavailable right now, so fallback questions will be used. "
    "Your study topic has still been saved for the game."
)


def _reset_gemini_client() -> None:
    global _gemini_client
    _gemini_client = None


def _chat_fallback_reply(user_message: str) -> str:
    snippet = user_message.strip()[:160]
    if snippet:
        return f"{GEMINI_UNAVAILABLE_REPLY} I noted: \"{snippet}\""
    return GEMINI_UNAVAILABLE_REPLY


def _client() -> genai.Client:
    global _gemini_client
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_key_here":
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured. Copy .env.example to .env and add your key.",
        )
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def _gen_config(allow_internet: bool) -> types.GenerateContentConfig:
    config = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
    if allow_internet:
        config.tools = [types.Tool(google_search=types.GoogleSearch())]
    return config


def _ensure_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {"turns": [], "files": {}}
    return _sessions[session_id]


def _internet_prefix(allow_internet: bool) -> str:
    if allow_internet:
        return "[Internet search: ENABLED — you may use the web if helpful]\n\n"
    return "[Internet search: DISABLED — use only this chat and any attached files]\n\n"


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=8000)
    allow_internet: bool = False
    file_ids: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class SessionResponse(BaseModel):
    session_id: str


class UploadResponse(BaseModel):
    file_id: str
    name: str
    mime_type: str


class ReadyRequest(BaseModel):
    session_id: str | None = None


class RevisionQuestionResponse(BaseModel):
    question: str
    options: list[str]
    correct: int
    source: str


class RevisionQuizResponse(BaseModel):
    questions: list[RevisionQuestionResponse]
    source: str


FALLBACK_REVISIONS = [
    {
        "question": "In A-level Computer Science, what is the main function of the ALU?",
        "options": ["Long-term storage", "Arithmetic and logic operations", "Network routing", "Display output"],
        "correct": 1,
        "source": "fallback",
    },
    {
        "question": "Which component temporarily holds data and instructions the CPU is currently using?",
        "options": ["Hard disk", "RAM", "Optical drive", "Power supply"],
        "correct": 1,
        "source": "fallback",
    },
    {
        "question": "In the fetch-decode-execute cycle, what happens during the decode stage?",
        "options": [
            "The instruction is carried out",
            "The instruction is copied from memory to the CPU",
            "The CPU interprets the instruction",
            "The program is saved to storage",
        ],
        "correct": 2,
        "source": "fallback",
    },
    {
        "question": "How many bits are in one byte?",
        "options": ["4", "8", "16", "32"],
        "correct": 1,
        "source": "fallback",
    },
    {
        "question": "Which of these is an example of secondary storage?",
        "options": ["Cache", "Register", "SSD", "Control unit"],
        "correct": 2,
        "source": "fallback",
    },
]


@app.get("/api/health")
def health():
    configured = bool(GEMINI_API_KEY and GEMINI_API_KEY != "your_key_here")
    return {"ok": True, "gemini_configured": configured, "model": MODEL}


@app.get("/api/ready-for-game")
def ready_for_game_status():
    return {"ready": _ready_for_game}


@app.post("/api/ready-for-game")
def ready_for_game(body: ReadyRequest | None = None):
    global _ready_for_game, _study_session_id
    _ready_for_game = True
    if body and body.session_id:
        _study_session_id = body.session_id
        _sync_study_context(body.session_id)
    return {"ok": True}


def _parse_revision_json(raw: str) -> dict:
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _generate_one_revision_question() -> RevisionQuestionResponse:
    global _asked_revision_questions

    session_id = _study_session_id
    if session_id and session_id in _sessions:
        _sync_study_context(session_id)
    elif not _study_context:
        for sid, data in _sessions.items():
            if data.get("turns"):
                _sync_study_context(sid)
                session_id = sid
                break

    session = _sessions.get(session_id) if session_id else None
    study_context = _study_context or (session or {}).get("study_context") or ""
    study_focus = _study_focus or (session or {}).get("study_focus") or study_context
    print(
        "[REVISION DEBUG] revision-question request | stored context:",
        repr(study_context[:120]),
        "| focus:",
        repr(study_focus[:80]),
    )
    if not study_context.strip():
        print("[GEMINI DEBUG] no study context — using fallback revision question")
        return _next_fallback_question(set())

    turns = (session or {}).get("turns", [])
    conversation = "\n".join(f"{t['role']}: {t['text']}" for t in turns[-16:])
    print("[REVISION DEBUG] context passed to Gemini:", repr(study_context[:200]))
    print("[REVISION DEBUG] focus passed to Gemini:", repr(study_focus[:120]))
    previous = _asked_revision_questions[-20:]
    previous_block = json.dumps(previous) if previous else "[]"

    prompt = (
        "Generate one multiple-choice revision question based specifically on this study context:\n"
        f"{study_context}\n\n"
        "MOST RECENT SPECIFIC FOCUS (primary topic — the question MUST test THIS, not a broader category):\n"
        f"{study_focus}\n\n"
        "Ask a question about the specific topic/context above, not a generic question about the broader subject. "
        "Focus on the most specific topics mentioned. Do not replace a specific topic with a broad category.\n\n"
        "Supporting conversation (for extra detail only — do not broaden the topic):\n"
        f"{conversation}\n\n"
        "Rules:\n"
        "- Exactly 4 options, exactly 1 correct answer (correct = index 0-3).\n"
        "- Works for any subject the student named — follow their context exactly.\n"
        "- Keep question and options concise.\n"
        f"- Do NOT repeat or closely paraphrase these earlier questions: {previous_block}\n\n"
        "Return ONLY valid JSON, no markdown:\n"
        '{"question": "...", "options": ["...", "...", "...", "..."], "correct": 0}'
    )
    try:
        print("[GEMINI DEBUG] calling Gemini for revision question")
        response = _client().models.generate_content(
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
        )
        data = _parse_revision_json((response.text or "").strip())
        options = data["options"]
        correct = int(data["correct"])
        question = str(data["question"]).strip()
        if len(options) != 4 or not (0 <= correct <= 3) or not question:
            raise ValueError("invalid shape")
        _asked_revision_questions.append(question)
        print("[GEMINI DEBUG] revision question succeeded:", repr(question))
        return RevisionQuestionResponse(
            question=question,
            options=[str(o) for o in options],
            correct=correct,
            source="gemini",
        )
    except HTTPException as exc:
        print(f"[GEMINI DEBUG] revision question failed (HTTP): {exc.detail}")
        _reset_gemini_client()
        return _next_fallback_question(set())
    except Exception as exc:
        print(f"[GEMINI DEBUG] revision question failed: {exc}")
        _reset_gemini_client()
        return _next_fallback_question(set())


def _next_fallback_question(used_questions: set[str]) -> RevisionQuestionResponse:
    for fb in FALLBACK_REVISIONS:
        if fb["question"] not in used_questions:
            used_questions.add(fb["question"])
            return RevisionQuestionResponse(**fb)
    fb = FALLBACK_REVISIONS[len(used_questions) % len(FALLBACK_REVISIONS)]
    return RevisionQuestionResponse(**fb)


@app.get("/api/revision-question", response_model=RevisionQuestionResponse)
def revision_question():
    return _generate_one_revision_question()


@app.get("/api/revision-quiz", response_model=RevisionQuizResponse)
def revision_quiz(count: int = Query(default=5, ge=1, le=10)):
    """Generate a batch of revision questions for a between-wave quiz."""
    questions: list[RevisionQuestionResponse] = []
    used_texts: set[str] = set()
    gemini_count = 0

    for i in range(count):
        try:
            q = _generate_one_revision_question()
            if q.question in used_texts:
                raise ValueError("duplicate question in quiz batch")
            used_texts.add(q.question)
            questions.append(q)
            if q.source == "gemini":
                gemini_count += 1
        except (HTTPException, Exception) as exc:
            detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
            print(f"[GEMINI DEBUG] quiz Q{i + 1} failed ({detail}) — using fallback")
            _reset_gemini_client()
            fb = _next_fallback_question(used_texts)
            questions.append(fb)

    if gemini_count == count:
        source = "gemini"
    elif gemini_count == 0:
        source = "fallback"
    else:
        source = "mixed"
    print(f"[REVISION DEBUG] quiz ready: {len(questions)} questions, source={source}")
    return RevisionQuizResponse(questions=questions, source=source)


@app.post("/api/session", response_model=SessionResponse)
def create_session():
    session_id = str(uuid.uuid4())
    _ensure_session(session_id)
    return SessionResponse(session_id=session_id)


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(session_id: str = Query(...), file: UploadFile = File(...)):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")

    _ensure_session(session_id)
    file_id = str(uuid.uuid4())
    safe_name = Path(file.filename or "upload").name.replace("..", "_")
    local_path = UPLOAD_DIR / f"{session_id}_{file_id}_{safe_name}"
    local_path.write_bytes(raw)

    try:
        print(f"[GEMINI DEBUG] calling Gemini file upload: {safe_name}")
        gemini_file = _client().files.upload(file=str(local_path))
        print("[GEMINI DEBUG] file upload succeeded")
    except Exception as exc:
        print(f"[GEMINI DEBUG] file upload failed: {exc}")
        _reset_gemini_client()
        gemini_file = None

    _sessions[session_id]["files"][file_id] = {
        "gemini_file": gemini_file,
        "name": safe_name,
        "mime_type": file.content_type or "application/octet-stream",
    }
    return UploadResponse(file_id=file_id, name=safe_name, mime_type=file.content_type or "application/octet-stream")


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    session = _ensure_session(body.session_id)
    global _study_session_id

    session["turns"].append({"role": "user", "text": body.message})
    _study_session_id = body.session_id
    _sync_study_context(body.session_id)
    print("[GEMINI DEBUG] chat request | context/focus:", repr(body.message[:120]))

    user_parts: list = []
    for fid in body.file_ids:
        meta = session["files"].get(fid)
        if meta and meta.get("gemini_file"):
            user_parts.append(meta["gemini_file"])
    user_parts.append(types.Part.from_text(text=_internet_prefix(body.allow_internet) + body.message))

    contents: list[types.Content] = []
    for turn in session["turns"][:-1]:
        contents.append(types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])]))
    contents.append(types.Content(role="user", parts=user_parts))

    reply = None
    try:
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_key_here":
            raise RuntimeError("Gemini API key not configured")
        print("[GEMINI DEBUG] calling Gemini for chat")
        response = _client().models.generate_content(
            model=MODEL,
            contents=contents,
            config=_gen_config(body.allow_internet),
        )
        reply = (response.text or "").strip()
        if not reply:
            raise ValueError("empty Gemini response")
        print("[GEMINI DEBUG] chat succeeded")
    except HTTPException as exc:
        print(f"[GEMINI DEBUG] chat failed (HTTP): {exc.detail}")
        _reset_gemini_client()
        reply = _chat_fallback_reply(body.message)
    except Exception as exc:
        print(f"[GEMINI DEBUG] chat failed: {exc}")
        _reset_gemini_client()
        reply = _chat_fallback_reply(body.message)

    session["turns"].append({"role": "model", "text": reply})
    return ChatResponse(reply=reply, session_id=body.session_id)


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_load_study_context_file()

if __name__ == "__main__":
    import webbrowser

    import uvicorn

    port = int(os.getenv("STUDY_CHAT_PORT", "8765"))
    url = f"http://127.0.0.1:{port}"
    print(f"Study chat: {url}")
    print("Set GEMINI_API_KEY in .env (never committed to git).")
    webbrowser.open(url)
    uvicorn.run(app, host="127.0.0.1", port=port)
