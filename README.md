# VoiceSafe AI — Voice Scam Analyzer

VoiceSafe AI is a prototype service that analyzes uploaded voice samples and estimates:

- Scam risk score
- AI-generated voice probability
- Vocal stress level

⚠️ This is a **prototype heuristic system**, not a forensic or certified detection tool.

---

## 🌍 Service Overview

The AI service receives an audio file, extracts acoustic features, and computes heuristic risk indicators.

Pipeline:

Upload → Audio normalization → Feature extraction → Heuristic scoring → JSON response

---

## 🚀 API Endpoints

### Health check
GET /

Returns service status.

Example response:

```json
{
  "ok": true,
  "service": "voicesafe-ai"
}