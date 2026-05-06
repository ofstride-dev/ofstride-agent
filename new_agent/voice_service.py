from __future__ import annotations

import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()


class VoiceService:
	"""Handles text-to-speech and speech-to-text using Azure Cognitive Services."""

	def __init__(
		self,
		speech_key: Optional[str] = None,
		speech_region: Optional[str] = None,
	) -> None:
		self.speech_key = speech_key or os.getenv("AZURE_SPEECH_KEY")
		self.speech_region = speech_region or os.getenv("AZURE_SPEECH_REGION")

		if not self.speech_key:
			raise ValueError("Missing AZURE_SPEECH_KEY environment variable.")
		if not self.speech_region:
			raise ValueError("Missing AZURE_SPEECH_REGION environment variable.")

		self.speech_config = speechsdk.SpeechConfig(
			subscription=self.speech_key,
			region=self.speech_region,
		)
		self.speech_config.speech_synthesis_voice_name = "en-US-AvaMultilingualNeural"

	def text_to_speech(self, text: str) -> bytes:
		"""
		Convert text to speech audio (WAV format).

		Args:
			text: Text to synthesize

		Returns:
			Audio data in WAV format
		"""
		# Use a temporary file for the audio output
		with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
			temp_path = tmp.name
		
		try:
			audio_config = speechsdk.audio.AudioConfig(filename=temp_path)
			
			# Create synthesizer
			synthesizer = speechsdk.SpeechSynthesizer(
				speech_config=self.speech_config,
				audio_config=audio_config,
			)

			# Synthesize the text
			result = synthesizer.speak_text(text)

			if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
				# Read the audio file
				with open(temp_path, 'rb') as f:
					audio_data = f.read()
				return audio_data
			elif result.reason == speechsdk.ResultReason.Canceled:
				cancellation_details = result.cancellation_details
				raise RuntimeError(
					f"Speech synthesis canceled: {cancellation_details.reason} - "
					f"{cancellation_details.error_details}"
				)
			else:
				raise RuntimeError(f"Unexpected speech synthesis result: {result.reason}")
		finally:
			# Clean up temp file
			Path(temp_path).unlink(missing_ok=True)

	def speech_to_text(self, audio_data: bytes) -> str:
		"""
		Convert speech audio to text.

		Args:
			audio_data: Audio data in WAV format

		Returns:
			Recognized text
		"""
		# Create audio stream from bytes using PushAudioInputStream
		push_stream = speechsdk.audio.PushAudioInputStream()
		push_stream.write(audio_data)
		push_stream.close()
		
		audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

		# Create recognizer
		recognizer = speechsdk.SpeechRecognizer(
			speech_config=self.speech_config,
			audio_config=audio_config,
		)

		# Recognize speech
		result = recognizer.recognize_once()

		if result.reason == speechsdk.ResultReason.RecognizedSpeech:
			return result.text
		elif result.reason == speechsdk.ResultReason.NoMatch:
			return ""
		elif result.reason == speechsdk.ResultReason.Canceled:
			cancellation_details = result.cancellation_details
			raise RuntimeError(
				f"Speech recognition canceled: {cancellation_details.reason} - "
				f"{cancellation_details.error_details}"
			)
		else:
			raise RuntimeError(f"Unexpected speech recognition result: {result.reason}")
