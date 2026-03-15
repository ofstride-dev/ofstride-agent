# AI B2B Intake & Routing Engine (v1)

Minimal, testable architecture with strict separation of concerns.

## Modules
- `intake_orchestrator.py`: Thin controller wiring components.
- `domain_resolver.py`: **Only** module allowed to set `control_domain`.
- `case_brief_extractor.py`: Extracts structured case brief fields (no control domain).
- `conflict_detector.py`: Detects contradictions/ambiguity.
- `escalation_decider.py`: Pure decision logic from confidence/conflict/missing fields.
- `question_policy.py`: Decides next question based on state.

No RAG/knowledge enrichment in v1.

## Usage
Set env var `GOOGLE_API_KEY` and optionally `GEMINI_MODEL` (defaults to `gemini-2.5-flash`).

Use the trimmed state-machine prompt in `system_prompt.txt` (no knowledge usage).
Pass it to `handle_message(..., system_prompt=...)`.

See `intake_orchestrator.py` for wiring.
