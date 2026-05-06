from __future__ import annotations

import json
import os
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict

import time

from .doc_summarizer import summarize_document
from .intake_orchestrator import handle_message
from .llm_client import LLMClient
from .models import IntakeState
from .telemetry import TELEMETRY
from .tenant_config import load_tenants, resolve_tenant
from .voice_service import VoiceService
from .chart_agent import ChartAgent

BASE_DIR = Path(__file__).resolve().parent
TENANTS = load_tenants(BASE_DIR)

# Initialize voice service (optional - won't fail if keys not configured)
try:
	VOICE_SERVICE = VoiceService()
except ValueError:
	VOICE_SERVICE = None

DEFAULT_CORS_ORIGINS = [
	"http://localhost:5173",
	"http://127.0.0.1:5173",
	"http://localhost:4173",
	"http://127.0.0.1:4173",
	"http://127.0.0.1:5500",
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

SESSIONS: Dict[str, IntakeState] = {}
SESSION_START: Dict[str, float] = {}


class ChatHandler(BaseHTTPRequestHandler):
	def _set_cors(self) -> None:
		origin = self.headers.get("Origin")
		if origin and origin in CHAT_CORS_ORIGINS:
			self.send_header("Access-Control-Allow-Origin", origin)
		elif "*" in CHAT_CORS_ORIGINS:
			self.send_header("Access-Control-Allow-Origin", "*")
		self.send_header("Access-Control-Allow-Headers", "Content-Type")
		self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		self.send_header("Vary", "Origin")

	def _send_text(self, status: int, payload: str, content_type: str = "text/plain") -> None:
		data = payload.encode("utf-8")
		self.send_response(status)
		self._set_cors()
		self.send_header("Content-Type", content_type)
		self.send_header("Content-Length", str(len(data)))
		self.end_headers()
		self.wfile.write(data)

	def _send_binary(self, status: int, data: bytes, content_type: str = "application/octet-stream") -> None:
		self.send_response(status)
		self._set_cors()
		self.send_header("Content-Type", content_type)
		self.send_header("Content-Length", str(len(data)))
		self.end_headers()
		self.wfile.write(data)

	def _extract_text(self, filename: str, data: bytes) -> str:
		lower = filename.lower()
		if lower.endswith((".txt", ".md", ".csv", ".log")):
			try:
				return data.decode("utf-8")
			except Exception:
				return data.decode("latin-1", errors="ignore")
		if lower.endswith(".pdf"):
			try:
				from PyPDF2 import PdfReader  # type: ignore
				reader = PdfReader(BytesIO(data))
				pages = [page.extract_text() or "" for page in reader.pages]
				return "\n".join(pages).strip()
			except Exception:
				return ""
		return ""

	def _send_json(self, status: int, payload: dict) -> None:
		data = json.dumps(payload).encode("utf-8")
		self.send_response(status)
		self._set_cors()
		self.send_header("Content-Type", "application/json")
		self.send_header("Content-Length", str(len(data)))
		self.end_headers()
		self.wfile.write(data)

	def do_OPTIONS(self) -> None:  # noqa: N802
		self.send_response(204)
		self._set_cors()
		self.end_headers()

	@staticmethod
	def _parse_multipart(body: bytes, content_type: str) -> dict:
		result: dict = {"fields": {}, "files": {}}
		marker = "boundary="
		if marker not in content_type:
			return result
		boundary = content_type.split(marker, 1)[1]
		boundary = boundary.strip().strip('"')
		if not boundary:
			return result
		boundary_bytes = ("--" + boundary).encode("utf-8")
		parts = body.split(boundary_bytes)
		for part in parts:
			if not part or part in {b"--\r\n", b"--", b"\r\n"}:
				continue
			part = part.strip(b"\r\n")
			if part.endswith(b"--"):
				part = part[:-2]
			if b"\r\n\r\n" not in part:
				continue
			headers_blob, content = part.split(b"\r\n\r\n", 1)
			headers = headers_blob.decode("utf-8", errors="ignore").split("\r\n")
			header_map = {}
			for line in headers:
				if ":" in line:
					key, value = line.split(":", 1)
					header_map[key.strip().lower()] = value.strip()
			content = content.rstrip(b"\r\n")
			disp = header_map.get("content-disposition", "")
			if "name=" not in disp:
				continue
			name = None
			filename = None
			for piece in disp.split(";"):
				piece = piece.strip()
				if piece.startswith("name="):
					name = piece.split("=", 1)[1].strip('"')
				if piece.startswith("filename="):
					filename = piece.split("=", 1)[1].strip('"')
			if not name:
				continue
			if filename:
				result["files"][name] = {"filename": filename, "content": content}
			else:
				result["fields"][name] = content.decode("utf-8", errors="ignore")
		return result

	def do_GET(self) -> None:  # noqa: N802
		if self.path in {"/", "/chat"}:
			html = (BASE_DIR / "chat.html").read_text(encoding="utf-8")
			data = html.encode("utf-8")
			self.send_response(200)
			self.send_header("Content-Type", "text/html; charset=utf-8")
			self.send_header("Content-Length", str(len(data)))
			self.end_headers()
			self.wfile.write(data)
			return
		if self.path == "/telemetry":
			data = json.dumps(TELEMETRY.snapshot()).encode("utf-8")
			self.send_response(200)
			self.send_header("Content-Type", "application/json")
			self.send_header("Content-Length", str(len(data)))
			self.end_headers()
			self.wfile.write(data)
			return
		if self.path == "/session/new":
			new_id = f"sess_{int(time.time() * 1000)}"
			SESSIONS[new_id] = IntakeState()
			SESSION_START[new_id] = time.time()
			self._send_json(200, {"session_id": new_id})
			return
		if self.path.startswith("/session/"):
			session_id = self.path.split("/session/", 1)[1]
			state = SESSIONS.get(session_id)
			if not state:
				self._send_json(404, {"error": "session not found"})
				return
			self._send_json(
				200,
				{
					"session_id": session_id,
					"summary": state.session_summary,
					"handoff": state.handoff.__dict__,
					"document_summary": state.document_summary,
					"document_entities": state.document_entities,
				},
			)
			return
		if self.path == "/schema/consultant":
			schema = (BASE_DIR / "consultant_schema.json").read_text(encoding="utf-8")
			data = schema.encode("utf-8")
			self.send_response(200)
			self.send_header("Content-Type", "application/json")
			self.send_header("Content-Length", str(len(data)))
			self.end_headers()
			self.wfile.write(data)
			return
		if self.path == "/schema/routing":
			schema = (BASE_DIR / "routing_contract.json").read_text(encoding="utf-8")
			data = schema.encode("utf-8")
			self.send_response(200)
			self.send_header("Content-Type", "application/json")
			self.send_header("Content-Length", str(len(data)))
			self.end_headers()
			self.wfile.write(data)
			return
		self.send_error(404)

	def do_POST(self) -> None:  # noqa: N802
		if self.path == "/upload":
			try:
				length = int(self.headers.get("Content-Length", "0"))
				body = self.rfile.read(length)
				content_type = self.headers.get("Content-Type", "")
				parsed = self._parse_multipart(body, content_type)
				file_field = parsed.get("files", {}).get("file")
				if not file_field:
					self._send_json(400, {"error": "file is required"})
					return
				filename = file_field.get("filename") or "upload"
				data = file_field.get("content", b"")
				extracted = self._extract_text(filename, data)
				if not extracted:
					self._send_json(400, {"error": "Could not extract text from document."})
					return
				message = f"Document uploaded ({filename}).\n\n{extracted[:8000]}"
				session_id = str(parsed.get("fields", {}).get("session_id", "default")).strip() or "default"
				previous_state = SESSIONS.get(session_id)
				if session_id not in SESSION_START:
					SESSION_START[session_id] = time.time()
				tenant = resolve_tenant(self.headers.get("Host", ""), TENANTS)
				system_prompt = tenant.system_prompt_path.read_text(encoding="utf-8")
				knowledge_path = str(tenant.knowledge_path) if tenant.knowledge_path else None
				result = handle_message(
					message,
					previous_state=previous_state,
					system_prompt=system_prompt,
					knowledge_override=knowledge_path,
				)
				summary = summarize_document(extracted, llm=LLMClient())
				state = result.get("state")
				if isinstance(state, IntakeState):
					state.document_summary = summary.get("summary")
					state.document_entities = summary.get("entities", {})
					SESSIONS[session_id] = state
				TELEMETRY.record("doc_upload", {"tenant": tenant.name, "filename": filename})
				self._send_json(
					200,
					{
						"text": result.get("text"),
						"debug": result.get("debug"),
						"session_id": session_id,
						"document_summary": summary.get("summary"),
						"document_entities": summary.get("entities"),
						"extracted_preview": extracted[:2000],
					},
				)
			except Exception as exc:
				self._send_json(500, {"error": str(exc)})
			return
		if self.path == "/speech/synthesize":
			try:
				if not VOICE_SERVICE:
					self._send_json(503, {"error": "Voice service not configured. Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."})
					return
				length = int(self.headers.get("Content-Length", "0"))
				body = self.rfile.read(length).decode("utf-8")
				payload = json.loads(body) if body else {}
				text = str(payload.get("text", "")).strip()
				if not text:
					self._send_json(400, {"error": "text is required"})
					return
				audio_data = VOICE_SERVICE.text_to_speech(text)
				self._send_binary(200, audio_data, "audio/wav")
			except Exception as exc:
				self._send_json(500, {"error": str(exc)})
			return
		if self.path == "/speech/recognize":
			try:
				if not VOICE_SERVICE:
					self._send_json(503, {"error": "Voice service not configured. Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."})
					return
				length = int(self.headers.get("Content-Length", "0"))
				body = self.rfile.read(length)
				if not body:
					self._send_json(400, {"error": "audio data is required"})
					return
				text = VOICE_SERVICE.speech_to_text(body)
				self._send_json(200, {"text": text})
			except Exception as exc:
				self._send_json(500, {"error": str(exc)})
			return
		if self.path == "/chart":
			try:
				length = int(self.headers.get("Content-Length", "0"))
				body = self.rfile.read(length).decode("utf-8")
				payload = json.loads(body) if body else {}
				question = str(payload.get("question", "")).strip()
				if not question:
					self._send_json(400, {"error": "question is required"})
					return
				agent = ChartAgent()
				response = agent.answer(question)
				self._send_json(
					200,
					{
						"text": response.text,
						"tools_used": response.tools_used,
						"data": response.data,
					},
				)
			except Exception as exc:
				self._send_json(500, {"error": str(exc)})
			return
		if self.path not in {"/chat", "/api/chat"}:
			self.send_error(404)
			return
		try:
			start = time.time()
			length = int(self.headers.get("Content-Length", "0"))
			body = self.rfile.read(length).decode("utf-8")
			payload = json.loads(body) if body else {}
			message = str(payload.get("message", "")).strip()
			session_id = str(payload.get("session_id", "default")).strip() or "default"
			if session_id not in SESSION_START:
				SESSION_START[session_id] = time.time()
			tenant = resolve_tenant(self.headers.get("Host", ""), TENANTS)
			system_prompt = tenant.system_prompt_path.read_text(encoding="utf-8")
			knowledge_path = str(tenant.knowledge_path) if tenant.knowledge_path else None
			if not message:
				self._send_json(400, {"error": "message is required"})
				return

			previous_state = SESSIONS.get(session_id)
			result = handle_message(
				message,
				previous_state=previous_state,
				system_prompt=system_prompt,
				knowledge_override=knowledge_path,
			)
			state = result.get("state")
			if isinstance(state, IntakeState):
				SESSIONS[session_id] = state
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

			self._send_json(
				200,
				{
					"text": result.get("text"),
					"debug": result.get("debug"),
					"handoff": result.get("handoff"),
					"matching_weights": result.get("matching_weights"),
					"session_id": session_id,
					"session_summary": result.get("session_summary"),
					"telemetry": TELEMETRY.snapshot(),
				},
			)
		except Exception as exc:
			self._send_json(500, {"error": str(exc)})


def run(host: str = "127.0.0.1", port: int = 8001) -> None:
	server = HTTPServer((host, port), ChatHandler)
	print(f"Server running at http://{host}:{port}")
	server.serve_forever()


if __name__ == "__main__":
    import os
    port = int(os.getenv("WEBSITES_PORT", "8001"))
    run(host="0.0.0.0", port=port)
