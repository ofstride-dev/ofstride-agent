from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Optional
import os
import time
import json
from io import BytesIO

from new_agent.doc_summarizer import summarize_document
from new_agent.intake_orchestrator import handle_message
from new_agent.llm_client import LLMClient
from new_agent.models import IntakeState
from new_agent.telemetry import TELEMETRY
from new_agent.tenant_config import load_tenants, resolve_tenant
from new_agent.chart_agent import ChartAgent
try:
    from new_agent.voice_service import VoiceService
    _VOICE_IMPORT_OK = True
except (ImportError, ModuleNotFoundError):
    VoiceService = None  # type: ignore
    _VOICE_IMPORT_OK = False


# Request body models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChartRequest(BaseModel):
    question: str


class SynthesizeRequest(BaseModel):
    text: str


class InitSessionRequest(BaseModel):
    """Pre-fill Saarthi session from rule-based chatbot"""
    contact_name: Optional[str] = None
    work_email: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    company_name: Optional[str] = None
# Initialize voice service (optional — requires azure-cognitiveservices-speech)
VOICE_SERVICE = None
if _VOICE_IMPORT_OK and VoiceService is not None:
    try:
        VOICE_SERVICE = VoiceService()
    except Exception:
        VOICE_SERVICE = None


BASE_DIR = Path(__file__).resolve().parent / "new_agent"
TENANTS = load_tenants(BASE_DIR)

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:4173",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "https://fluffy-spork-r4jr99wp5qv63pw7p-5173.app.github.dev",
    "https://fluffy-spork-r4jr99wp5qv63pw7p-5174.app.github.dev",
]

CHAT_CORS_ORIGINS_RAW = os.getenv("CHAT_CORS_ORIGINS")
if CHAT_CORS_ORIGINS_RAW:
    CHAT_CORS_ORIGINS = [
        origin.strip()
        for origin in CHAT_CORS_ORIGINS_RAW.split(",")
        if origin.strip()
    ]
else:
    CHAT_CORS_ORIGINS = DEFAULT_CORS_ORIGINS

# Global session store
SESSIONS: Dict[str, IntakeState] = {}
SESSION_START: Dict[str, float] = {}

app = FastAPI(title="Ofstride Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_text(filename: str, data: bytes) -> str:
    """Extract text from uploaded documents"""
    lower = filename.lower()
    if lower.endswith((".txt", ".md", ".csv", ".log")):
        try:
            return data.decode("utf-8")
        except Exception:
            return data.decode("latin-1", errors="ignore")
    if lower.endswith(".pdf"):
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages).strip()
        except Exception:
            return ""
    return ""


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve chat.html"""
    try:
        html_path = BASE_DIR / "chat.html"
        return html_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return """
        <html>
            <body>
                <h1>Ofstride Saarthi Agent</h1>
                <p>Chat interface not found. Check that chat.html exists in new_agent/</p>
            </body>
        </html>
        """


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ofstride-agent"}


@app.get("/telemetry")
async def telemetry():
    """Get telemetry snapshot"""
    return TELEMETRY.snapshot()


@app.get("/session/new")
async def create_session():
    """Create a new chat session"""
    new_id = f"sess_{int(time.time() * 1000)}"
    SESSIONS[new_id] = IntakeState()
    SESSION_START[new_id] = time.time()
    return {"session_id": new_id}


@app.post("/session/init")
async def init_session(request: InitSessionRequest):
    """Initialize session from rule-based chatbot with pre-filled contact info"""
    new_id = f"sess_{int(time.time() * 1000)}"
    
    # Create new state and pre-fill with rule-based widget data
    state = IntakeState()
    state.case_brief.contact_name = request.contact_name
    state.case_brief.work_email = request.work_email
    state.case_brief.location = request.location
    state.case_brief.company_name = request.company_name
    
    # Update missing fields (skip LEAD stage since we have name + email)
    state.missing_fields = [
        f for f in ["problem_summary", "desired_outcome", "service", "urgency", 
                   "timeline", "business_impact", "decision_maker", "industry", 
                   "company_size", "role"]
        if f not in state.case_brief.__dict__ or getattr(state.case_brief, f) is None
    ]
    
    # Determine stage: skip LEAD since we have name + email
    from new_agent.question_policy import determine_stage
    state.stage = determine_stage(state.missing_fields)
    
    SESSIONS[new_id] = state
    SESSION_START[new_id] = time.time()
    
    # Return greeting + next question from DISCOVERY/CLASSIFICATION stage
    return {
        "session_id": new_id,
        "greeting": f"Great! I have your info, {request.contact_name}. Now, what brings you to Ofstride today? Tell me about the challenge you're facing or what you'd like to achieve.",
        "stage": state.stage.value,
        "missing_fields": state.missing_fields,
    }


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session state and metadata"""
    state = SESSIONS.get(session_id)
    if not state:
        return JSONResponse(
            status_code=404,
            content={"error": "session not found"}
        )
    return {
        "session_id": session_id,
        "summary": state.session_summary,
        "handoff": state.handoff.__dict__,
        "document_summary": state.document_summary,
        "document_entities": state.document_entities,
    }


@app.get("/schema/consultant")
async def get_consultant_schema():
    """Get consultant schema"""
    try:
        schema_path = BASE_DIR / "consultant_schema.json"
        schema_text = schema_path.read_text(encoding="utf-8")
        return JSONResponse(content=json.loads(schema_text))
    except FileNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": "consultant schema not found"}
        )


@app.get("/schema/routing")
async def get_routing_schema():
    """Get routing contract schema"""
    try:
        schema_path = BASE_DIR / "routing_contract.json"
        schema_text = schema_path.read_text(encoding="utf-8")
        return JSONResponse(content=json.loads(schema_text))
    except FileNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": "routing schema not found"}
        )


@app.post("/chat")
async def chat(request: ChatRequest, host: Optional[str] = Header(None)):
    """Main chat endpoint - process user message and update intake state"""
    try:
        start = time.time()
        
        message = request.message.strip()
        session_id = (request.session_id or "default").strip() or "default"
        
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "message is required"}
            )
        
        if session_id not in SESSION_START:
            SESSION_START[session_id] = time.time()
        
        # Resolve tenant
        tenant = resolve_tenant(host or "", TENANTS)
        system_prompt = tenant.system_prompt_path.read_text(encoding="utf-8")
        knowledge_path = str(tenant.knowledge_path) if tenant.knowledge_path else None
        
        # Get previous state
        previous_state = SESSIONS.get(session_id)
        
        # Process message through intake orchestrator
        result = handle_message(
            message,
            previous_state=previous_state,
            system_prompt=system_prompt,
            knowledge_override=knowledge_path,
        )
        
        # Update session state
        state = result.get("state")
        if isinstance(state, IntakeState):
            SESSIONS[session_id] = state
        
        # Record telemetry
        elapsed_ms = (time.time() - start) * 1000
        TELEMETRY.record("chat_turn", {"tenant": tenant.name})
        TELEMETRY.record_timing("chat_turn_ms", elapsed_ms)
        
        if state and state.stage.value == "READY":
            start_time = SESSION_START.get(session_id)
            if start_time:
                TELEMETRY.record_timing("resolution_time_ms", (time.time() - start_time) * 1000)
            TELEMETRY.record("conversion_ready", {"tenant": tenant.name})
        
        missing_count = len(state.missing_fields) if state else 0
        handoff_quality = max(0.0, 1.0 - (missing_count / 11.0))
        TELEMETRY.record_timing("handoff_quality", handoff_quality * 100)
        
        return {
            "text": result.get("text"),
            "debug": result.get("debug"),
            "handoff": result.get("handoff"),
            "matching_weights": result.get("matching_weights"),
            "session_id": session_id,
            "session_summary": result.get("session_summary"),
            "telemetry": TELEMETRY.snapshot(),
        }
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)}
        )


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
    host: Optional[str] = Header(None)
):
    """Upload and process a document"""
    try:
        session_id = session_id or "default"
        
        # Read file content
        content = await file.read()
        filename = file.filename or "upload"
        
        # Extract text from document
        extracted = _extract_text(filename, content)
        if not extracted:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not extract text from document."}
            )
        
        # Create message from document
        message = f"Document uploaded ({filename}).\n\n{extracted[:8000]}"
        
        if session_id not in SESSION_START:
            SESSION_START[session_id] = time.time()
        
        # Resolve tenant
        tenant = resolve_tenant(host or "", TENANTS)
        system_prompt = tenant.system_prompt_path.read_text(encoding="utf-8")
        knowledge_path = str(tenant.knowledge_path) if tenant.knowledge_path else None
        
        previous_state = SESSIONS.get(session_id)
        
        # Process document through intake orchestrator
        result = handle_message(
            message,
            previous_state=previous_state,
            system_prompt=system_prompt,
            knowledge_override=knowledge_path,
        )
        
        # Summarize document
        summary = summarize_document(extracted, llm=LLMClient())
        
        # Update session with document info
        state = result.get("state")
        if isinstance(state, IntakeState):
            state.document_summary = summary.get("summary")
            state.document_entities = summary.get("entities", {})
            SESSIONS[session_id] = state
        
        TELEMETRY.record("doc_upload", {"tenant": tenant.name, "filename": filename})
        
        return {
            "text": result.get("text"),
            "debug": result.get("debug"),
            "session_id": session_id,
            "document_summary": summary.get("summary"),
            "document_entities": summary.get("entities"),
            "extracted_preview": extracted[:2000],
        }
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)}
        )


@app.post("/chart")
async def chart_answer(request: ChartRequest):
    """Get analytics chart data and answer"""
    try:
        question = request.question.strip()
        if not question:
            return JSONResponse(
                status_code=400,
                content={"error": "question is required"}
            )
        
        agent = ChartAgent()
        response = agent.answer(question)
        
        return {
            "text": response.text,
            "tools_used": response.tools_used,
            "data": response.data,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)}
        )


@app.post("/speech/synthesize")
async def synthesize_speech(request: SynthesizeRequest):
    """Convert text to speech (TTS)"""
    try:
        if not VOICE_SERVICE:
            return JSONResponse(
                status_code=503,
                content={"error": "Voice service not configured. Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."}
            )
        
        text = request.text.strip()
        if not text:
            return JSONResponse(
                status_code=400,
                content={"error": "text is required"}
            )
        
        audio_data = VOICE_SERVICE.text_to_speech(text)
        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=response.wav"}
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)}
        )


@app.post("/speech/recognize")
async def recognize_speech(file: UploadFile = File(...)):
    """Convert speech to text (STT)"""
    try:
        if not VOICE_SERVICE:
            return JSONResponse(
                status_code=503,
                content={"error": "Voice service not configured. Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."}
            )
        
        audio_data = await file.read()
        if not audio_data:
            return JSONResponse(
                status_code=400,
                content={"error": "audio data is required"}
            )
        
        text = VOICE_SERVICE.speech_to_text(audio_data)
        return {"text": text}
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)}
        )

@app.post("/api/chat")
async def api_chat(request: ChatRequest, host: Optional[str] = Header(None)):
    """Alias for /chat — matches frontend's fetch(`${leadApiBase}/api/chat`)"""
    return await chat(request, host)


@app.post("/api/leads")
async def api_leads(request: dict = None):
    """Receives intake form data from frontend. Extend to write to CRM/DB."""
    TELEMETRY.record("lead_saved", {})
    return {"status": "ok"}


@app.post("/api/consultant")
async def api_consultant(request: dict = None):
    """
    Consultant matching. Reads public/data/consultants.csv.
    Falls back to a generic response if file not found.
    """
    import csv as csv_module
    csv_path = Path(__file__).resolve().parent / "public" / "data" / "consultants.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="No consultant data found")
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv_module.DictReader(f)
        consultants = list(reader)
    if not consultants:
        raise HTTPException(status_code=404, detail="No consultants available")
    return {"consultant": consultants[0]}


@app.post("/api/notify")
async def api_notify(request: dict = None):
    """Logs consultant notification. Wire to email/Slack in production."""
    TELEMETRY.record("notify_requested", {})
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEBSITES_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)