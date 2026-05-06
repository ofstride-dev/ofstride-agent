# Voice Support Quick Setup

## TL;DR - 3 Steps to Enable Voice

### Step 1: Get Azure Speech Keys
1. Go to https://portal.azure.com
2. Create a resource → Search "Speech" → Create
3. Go to Keys & Endpoint (left sidebar)
4. Note down: **Key** and **Region** (e.g., "eastus")

### Step 2: Add to Environment
Create/update `.env`:
```env
AZURE_SPEECH_KEY=your-key-from-step-1
AZURE_SPEECH_REGION=eastus
```

### Step 3: Install & Run
```bash
pip install -r new_agent/requirements.txt
python main.py
```

## That's It! 🎉

Open the web UI at `http://localhost:8001/chat` and:
- **Toggle "Voice Response"** to hear AI responses read aloud
- **Click "🎤 Speak"** to ask questions by voice

## What If I Don't Have Azure?

**Free option**: Skip voice for now - it's completely optional. Text chat works great without it.

**Free credits**: New Azure accounts get $200-300 free credits + free tier speech services.

## Help & Detailed Config

See [VOICE_CONFIG.md](./VOICE_CONFIG.md) for:
- Detailed setup with screenshots
- Pricing information
- Troubleshooting guide
- API endpoint documentation
- Python SDK usage examples
