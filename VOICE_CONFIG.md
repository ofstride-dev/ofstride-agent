# Voice Support Configuration

This agent now includes text-to-speech (TTS) and speech-to-text (STT) capabilities using Azure Cognitive Services.

## Setup Instructions

### 1. Get Azure Speech Service Credentials

**Option 1: Using Azure Portal (Recommended)**

1. Go to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" → Search for "Speech"
3. Select "Speech" and click Create
4. Fill in the form:
   - **Resource group**: Create new (e.g., "ofstride-voice")
   - **Region**: Choose closest to you (e.g., "East US", "UK South")
   - **Name**: e.g., "ofstride-speech"
   - **Pricing tier**: Free (F0) for testing, Standard (S0) for production
5. Click Review + create → Create
6. Go to the resource → Keys and Endpoint (left sidebar)
7. Copy:
   - **Key 1** → `AZURE_SPEECH_KEY`
   - **Location/Region** → `AZURE_SPEECH_REGION` (use the lowercase code like "eastus", "uksouth")

**Option 2: Using Azure CLI**

```bash
# Login to Azure
az login

# Create resource group
az group create --name ofstride-voice --location eastus

# Create Speech service
az cognitiveservices account create \
  --name ofstride-speech \
  --resource-group ofstride-voice \
  --kind Speech \
  --sku F0 \
  --location eastus

# Get keys
az cognitiveservices account keys list \
  --name ofstride-speech \
  --resource-group ofstride-voice
```

### 2. Configure Environment Variables

Add to your `.env` file:

```env
AZURE_SPEECH_KEY=your-api-key-here
AZURE_SPEECH_REGION=eastus
```

Or set as system environment variables:

```bash
export AZURE_SPEECH_KEY="your-api-key-here"
export AZURE_SPEECH_REGION="eastus"
```

### 3. Install Dependencies

```bash
pip install -r new_agent/requirements.txt
```

This includes `azure-cognitiveservices-speech>=1.35.0`

## Usage

### Web UI (chat.html)

1. **Text-to-Speech (TTS)**
   - Toggle "Voice Response" switch ON
   - Send a message
   - Agent response will be played as audio
   - Use the audio player to control playback

2. **Speech-to-Text (STT)**
   - Click "🎤 Speak" button to record
   - Speak your question/message
   - Click "⏹️ Stop Recording"
   - Transcribed text will appear in input field
   - Message auto-submits if text is recognized

### Python API

```python
from new_agent.voice_service import VoiceService

service = VoiceService()

# Text to Speech
audio_bytes = service.text_to_speech("Hello, how can I help you?")
# audio_bytes can be sent to client or saved to file

# Speech to Text
text = service.speech_to_text(audio_bytes)
print(text)  # Recognized text
```

### Server Endpoints

#### POST /speech/synthesize
Convert text to speech audio.

**Request:**
```json
{
  "text": "Your message here"
}
```

**Response:** WAV audio file

**Example:**
```bash
curl -X POST http://localhost:8001/speech/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello there"}' \
  -o response.wav
```

#### POST /speech/recognize
Convert speech audio to text.

**Request:** WAV audio data

**Response:**
```json
{
  "text": "Recognized text here"
}
```

**Example:**
```bash
curl -X POST http://localhost:8001/speech/recognize \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

## Voice Configuration

The agent uses:
- **Voice**: en-US-AvaMultilingualNeural (Ava, female voice with multilingual support)
- **Language**: English (US)
- **Format**: WAV (16-bit PCM, 16kHz)

To use a different voice, edit `new_agent/voice_service.py`:

```python
# Line 33: Change this to a different voice name
self.speech_config.speech_synthesis_voice_name = "en-US-AmberNeural"  # Or another voice
```

Available voices: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts

## Pricing

- **Free Tier (F0)**: 0.5M characters/month (speech synthesis), 1 hour/month (speech recognition) - good for testing
- **Standard (S0)**: Pay-as-you-go (~$1 per 1M characters for TTS, ~$1 per 1000 requests for STT)

## Troubleshooting

### "Voice service not configured" error
- Check that `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` are set
- Verify the values are correct (no extra spaces)
- Restart the server after changing environment variables

### "Microphone access denied"
- Browser permission issue
- Allow microphone access when prompted
- Check browser settings → Privacy & Security → Microphone

### "No speech detected"
- Microphone not working properly
- Speak louder/closer to microphone
- Check microphone volume levels

### Audio playback not working
- Browser audio permissions needed
- Check if audio output device is working
- Try playing a different audio file

## API Pricing Estimate

**Usage scenario**: 100 users/day, 10 turns each, mix of text and voice

- TTS: ~100 responses × 100 chars average = 10,000 chars/day = ~$0.30/month
- STT: ~50 voice inputs/day = ~$1.50/month (1000 requests = $1)
- **Total**: ~$2/month at Standard pricing

Free tier recommended for development/testing.

## Additional Resources

- [Azure Speech Services Docs](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/)
- [Python SDK Reference](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/)
- [Supported Voices](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts)
