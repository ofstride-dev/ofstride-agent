from __future__ import annotations

import os
import json
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
	"""
	GitHub Models (models.github.ai) or Azure AI Model Inference OpenAI-compatible Chat Completions.

	Env vars:
	- For GitHub: GITHUB_PAT or GITHUB_INFERENCE_API_KEY (PAT must have models scope)
	- For Azure: AZURE_API_KEY or AZURE_INFERENCE_API_KEY
	- API_URL (optional) default: GitHub URL, or set to Azure URL
	- GPT_MODEL (optional) default: openai/gpt-4.1 for GitHub, gpt-4 for Azure
	"""

	def __init__(
		self,
		api_key: Optional[str] = None,
		api_url: Optional[str] = None,
		model: Optional[str] = None,
	) -> None:
		self.api_url = (api_url or os.getenv("API_URL") or os.getenv("GITHUB_MODELS_URL") or "https://models.github.ai/inference/chat/completions").strip()
		self.is_azure = "azure.com" in self.api_url.lower()
		
		if self.is_azure:
			self.api_key = api_key or os.getenv("AZURE_API_KEY") or os.getenv("AZURE_INFERENCE_API_KEY")
			self.model = (model or os.getenv("GPT_MODEL") or "gpt-4").strip()
		else:
			self.api_key = api_key or os.getenv("GITHUB_PAT") or os.getenv("GITHUB_INFERENCE_API_KEY")
			self.model = (model or os.getenv("GPT_MODEL") or "openai/gpt-4.1").strip()
		
		# Determine primary provider: Azure if AZURE_API_KEY is set, else GitHub
		self.primary_azure = bool(os.getenv("AZURE_API_KEY") or os.getenv("AZURE_INFERENCE_API_KEY"))
		
		if not (self.api_key or os.getenv("GITHUB_PAT") or os.getenv("GITHUB_INFERENCE_API_KEY")):
			raise ValueError("Missing API key. Set AZURE_API_KEY for Azure or GITHUB_PAT for GitHub.")

	def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
		payload = {
			"model": self.model,
			"messages": [
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			"temperature": float(temperature),
		}

		# Try primary provider (Azure if AZURE_API_KEY set, else GitHub)
		try:
			return self._generate_with_provider(payload, self.primary_azure)
		except requests.HTTPError as e:
			if e.response.status_code in (400, 404, 403):  # Bad request, not found, forbidden
				# Fallback to the other provider
				try:
					return self._generate_with_provider(payload, not self.primary_azure)
				except requests.HTTPError:
					# If both fail, raise the original error
					raise e
			else:
				# For other errors (500, etc.), don't retry
				raise

	def _generate_with_provider(self, payload: Dict[str, Any], use_azure: bool) -> str:
		if use_azure:
			api_url = os.getenv("API_URL", "https://models.inference.ai.azure.com/chat/completions").strip()
			api_key = os.getenv("AZURE_API_KEY") or os.getenv("AZURE_INFERENCE_API_KEY")
			model = os.getenv("GPT_MODEL", "gpt-4").strip()
			headers = {
				"Authorization": f"Bearer {api_key}",
				"Content-Type": "application/json",
			}
		else:
			api_url = os.getenv("GITHUB_MODELS_URL", "https://models.github.ai/inference/chat/completions").strip()
			api_key = os.getenv("GITHUB_PAT") or os.getenv("GITHUB_INFERENCE_API_KEY")
			model = os.getenv("GPT_MODEL", "openai/gpt-4.1").strip()
			headers = {
				"Accept": "application/vnd.github+json",
				"Authorization": f"Bearer {api_key}",
				"X-GitHub-Api-Version": "2022-11-28",
				"Content-Type": "application/json",
			}
		
		if not api_key:
			provider = "Azure" if use_azure else "GitHub"
			raise ValueError(f"Missing API key for {provider}.")

		payload["model"] = model
		resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
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
