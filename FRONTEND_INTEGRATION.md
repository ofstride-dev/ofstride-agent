# Saarthi Integration Guide for Frontend Chat Widget

## Overview
Your existing rule-based chatbot collects basic info (name, email, phone, city). This guide shows how to **hand off to Saarthi AI agent** after initial collection.

---

## Integration Flow

```
Rule-Based Widget (Form)         Saarthi AI Agent
─────────────────────────────────────────────────────
1. Ask name                       
2. Ask email         
3. Ask phone         
4. Ask city          
                                  → POST /session/init
5. Show "Start AI Chat"       
                                  ← Get session_id + greeting
6. Switch to Saarthi UI       
7. Display greeting             
8. Keep chatting                → POST /chat (session_id, message)
                                  ← Get response + handoff
```

---

## Endpoints

### 1. Initialize Session (from your rule-based widget)
**POST** `http://your-api:8001/session/init`

**Request Body:**
```json
{
  "contact_name": "Yuvraj",
  "work_email": "yuvraj17nov@gmail.com",
  "phone_number": "9742214570",
  "location": "San Francisco",
  "company_name": "Google"
}
```

**Response:**
```json
{
  "session_id": "sess_1712856000000",
  "greeting": "Great! I have your info, Yuvraj. Now, what brings you to Ofstride today?",
  "stage": "DISCOVERY",
  "missing_fields": ["problem_summary", "desired_outcome", "service", "urgency", ...]
}
```

**Use the `session_id` for all subsequent chat messages.**

---

### 2. Send Chat Message
**POST** `http://your-api:8001/chat`

**Request Body:**
```json
{
  "message": "I need help automating HR onboarding",
  "session_id": "sess_1712856000000"
}
```

**Response:**
```json
{
  "text": "Great! Automating HR onboarding can save...",
  "handoff": {
    "intent_bucket": "AI/Tech",
    "summary": "...",
    "contact_name": "Yuvraj",
    "work_email": "yuvraj17nov@gmail.com",
    ...
  },
  "session_id": "sess_1712856000000",
  "session_summary": "User is looking for...",
  "stage": "QUALIFICATION"
}
```

---

### 3. Get Session State Anytime
**GET** `http://your-api:8001/session/{session_id}`

**Response:**
```json
{
  "session_id": "sess_1712856000000",
  "summary": "Yuvraj from Google wants HR onboarding automation...",
  "handoff": {
    "intent_bucket": "AI/Tech",
    "requirements": [...],
    "timeline": "...",
    ...
  },
  "document_summary": null,
  "document_entities": {}
}
```

---

## Frontend Implementation Example

### JavaScript/React
```javascript
// Step 1: Collect user data with rule-based form
const collectedData = {
  contact_name: "Yuvraj",
  work_email: "yuvraj17nov@gmail.com",
  phone_number: "9742214570",
  location: "San Francisco",
  company_name: "Google"
};

// Step 2: Initialize Saarthi session
const initResponse = await fetch('http://localhost:8001/session/init', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(collectedData)
});

const { session_id, greeting } = await initResponse.json();

// Step 3: Display Saarthi greeting
console.log(greeting); // "Great! I have your info, Yuvraj..."

// Step 4: Start chatting
async function sendMessage(message) {
  const response = await fetch('http://localhost:8001/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      session_id: session_id
    })
  });
  
  const { text, handoff, session_summary } = await response.json();
  
  console.log(text); // Saarthi's response
  
  // Check if conversation is ready for handoff
  if (handoff.intent_bucket && handoff.summary) {
    console.log("Ready to handoff to consultant");
  }
}

sendMessage("I need help with automated HR onboarding");
```

---

## Stage Progression

Saarthi advances through **6 stages** automatically:

| Stage | What Saarthi Does |
|-------|-------------------|
| **LEAD** | Asks for name + email (skipped if pre-filled) |
| **DISCOVERY** | Understands the problem & desired outcome |
| **CLASSIFICATION** | Identifies service domain (AI, HR, Finance, Legal, etc.) |
| **QUALIFICATION** | Asks about urgency, timeline, business impact |
| **IDENTITY** | Collects company info (name, size, industry, role) |
| **READY** | Ready to handoff to specialist consultant |

---

## When to Trigger "Talk to Consultant"

After each chat response, check the `handoff` field:

```javascript
if (response.handoff.summary && response.handoff.timeline) {
  // Conversation is qualified - show "Schedule Consultant Call" button
  showConsultantButton();
}
```

**At READY stage**, you have everything needed:
- Intent bucket (service domain)
- Problem summary
- Desired outcome
- Timeline & urgency
- Company info
- Contact details

---

## CORS Configuration

The agent API supports CORS from:
- `http://localhost:5173` (Vite dev)
- `http://localhost:4173` (Vite preview)
- `http://localhost:3000` (React dev)
- Your production domain (set `CHAT_CORS_ORIGINS` env var)

To add your domain:
```bash
export CHAT_CORS_ORIGINS="http://yoursite.com,https://yoursite.com"
```

---

## Error Handling

Always check `error` field in responses:

```javascript
if (response.status !== 200) {
  console.error(response.error);
  showErrorMessage("Failed to process message. Try again.");
}
```

---

## Tips for Best UX

1. **Pre-fill with rule-based data** → Skip repetitive LEAD questions
2. **Show stage progress** → "Step 2 of 6: Tell us more..."
3. **Save session_id in localStorage** → Resume conversations
4. **Auto-trigger consultant call** → Don't wait for READY stage
5. **Show typing indicator** → While waiting for Saarthi response
6. **Disable escalation** → UI waits for handoff package before offering call

---

## Conversation Quality Rating: 7.5/10

**What went well:**
✅ Natural progression (LEAD → DISCOVERY → CLASSIFICATION → QUALIFICATION)  
✅ No repetitive questions  
✅ Good conversational tone  
✅ Identified service correctly (Agentic AI)  

**What to improve:**
❌ Missing phone field capture in state  
❌ Didn't push urgency/timeline harder  
❌ Didn't reach READY stage (incomplete hand-fill)  
❌ Could offer document upload for detailed requirements  

---

## API Reference

### All Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Serve chat.html |
| GET | `/health` | Server health check |
| GET | `/telemetry` | Analytics snapshot |
| GET | `/session/new` | Create blank session |
| POST | `/session/init` | Create + pre-fill session |
| GET | `/session/{id}` | Get session state |
| POST | `/chat` | Send message |
| POST | `/upload` | Upload document (PDF/TXT) |
| POST | `/chart` | Analytics question |

---

## Next Steps

1. **Update your rule-based widget** to call `/session/init` instead of creating a blank session
2. **Pass collected data** (name, email, phone, city) to Saarthi
3. **Store session_id** and use it for all subsequent /chat calls
4. **Show consultant call button** when handoff package is ready
5. **Test end-to-end** flow with the agent

Good luck! 🚀
