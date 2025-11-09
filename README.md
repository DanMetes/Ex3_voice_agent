# EX 3 – Voice Agent (FastAPI)

This is a **complete, low‑latency voice agent** that meets the exercise goals:

- FastAPI server to handle requests
- ASR via **Whisper** (local) or **Google SpeechRecognition**
- Local dialogue engine using **Ollama** (LLM3/8B or any chat model) or a small HF pipeline fallback
- TTS via **pyttsx3** (offline) to synthesize replies
- Web client demonstrating **5+ back‑and‑forth turns** in one session

> The repo is intentionally lightweight and runs fully on your machine. Swap engines as needed in `.env`.

---

## 1) Setup

```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env
```

### Engines (choose defaults in `.env`)

- **ASR**: `ASR_ENGINE=whisper` (downloads a small model at first run) or `google` (uses SpeechRecognition).
- **LLM**: `LLM_BACKEND=ollama` (recommended; install Ollama and `ollama run llama3`), or `hf` (falls back to `HF_MODEL=distilgpt2`).
- **TTS**: `pyttsx3` (offline). Optional `VOICE_NAME` and `VOICE_RATE` in `.env`.

> If using Google SpeechRecognition with an API key, set `GOOGLE_SPEECH_API_KEY` in `.env`.

## 2) Run the server

```bash
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/ to use the demo UI.

## 3) What happens in the loop?

1. Browser records your voice (WebAudio) and sends a WAV to `/transcribe`.
2. Server transcribes using Whisper or Google.
3. Conversation state keeps context for N turns (default 8).
4. LLM (Ollama or HF pipeline) generates the assistant reply `/reply`.
5. TTS synthesizes the voice response `/speak` and returns WAV to play in browser.

## 4) 5+ Continuous Turns

Click **Record**, speak, release; repeat at least 5 times. The server maintains the dialog state and keeps context.

## 5) Files & Structure

```
voice_agent_ex3/
├── client/
│   └── index.html         # simple demo UI
├── src/
│   ├── asr.py             # Whisper & Google ASR
│   ├── llm.py             # Ollama chat or HF pipeline fallback
│   ├── state.py           # ring-buffer conversation memory
│   └── tts.py             # pyttsx3 TTS
├── main.py                # FastAPI app (routes: /, /transcribe, /reply, /speak, /reset)
├── requirements.txt
├── .env.example
└── README.md
```

## 6) Notes & Tips

- Whisper model size can be selected in `src/asr.py` (`base` by default). For faster latency try `tiny`.
- For better TTS, you can swap `pyttsx3` with [coqui-ai/TTS] or [edge-tts]. The `/speak` route only expects a WAV file path.
- For **LLM speed**, Ollama + a small quantized model (e.g., `llama3:instruct` or `mistral`) is ideal.
- The architecture is modular to make it easy to plug **whisper.cpp**, **FasterWhisper**, or cloud STT/TTS later.

## 7) Demo Script (CLI)

```bash
# Reset history
curl -X POST http://localhost:8000/reset

# Send text (bypass ASR for testing)
curl -s -X POST http://localhost:8000/reply -H "Content-Type: application/json" -d '{"text": "Hello, who are you?"}'
```

Enjoy!
