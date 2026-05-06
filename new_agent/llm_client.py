from __future__ import annotations

import os
import json
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
	"""
	Azure AI Foundry OpenAI-compatible Chat Completions client.

	Env vars:
	- AZURE_API_KEY: API key for Azure Foundry (required)
	- API_URL: Azure endpoint URL (required)
	- GPT_MODEL: Model name, defaults to gpt-oss-120b
	"""

	def __init__(
		self,
		api_key: Optional[str] = None,
		api_url: Optional[str] = None,
		model: Optional[str] = None,
	) -> None:
		self.api_key = api_key or os.getenv("AZURE_API_KEY")
		self.api_url = (api_url or os.getenv("API_URL")).strip() if (api_url or os.getenv("API_URL")) else None
		self.model = (model or os.getenv("GPT_MODEL") or "gpt-oss-120b").strip()
		
		if not self.api_key:
			raise ValueError("Missing AZURE_API_KEY environment variable.")
		if not self.api_url:
			raise ValueError("Missing API_URL environment variable.")

	def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
		payload = {
			"model": self.model,
			"messages": [
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			"temperature": float(temperature),
		}

		headers = {
			"Authorization": f"Bearer {self.api_key}",
			"Content-Type": "application/json",
		}
		
		resp = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
		resp.raise_for_status()
		data = resp.json()

		choices = data.get("choices", [])
		if not choices:
			return ""

		msg = choices[0].get("message", {})
		content = msg.get("content", "")
		return str(content or "").strip()

	def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> Dict[str, Any]:
		text = self.generate_text(system_prompt, user_prompt, temperature=temperature)
		return _extract_json_object(text)


def _extract_json_object(text: str) -> Dict[str, Any]:
	start = text.find("{")
	end = text.rfind("}")
	if start == -1 or end == -1 or end <= start:
		return {}
	try:
		return json.loads(text[start : end + 1])
	except Exception:
		return {}
