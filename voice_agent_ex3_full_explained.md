
# EX3 Voice Agent — Full Explained Walkthrough (Line‑by‑Line)

This single document is a thorough, **line‑by‑line** explanation of your `eEx3_voice_agent` project.  
It covers the overall control flow, inputs/outputs, dependencies, and **annotated source for every file**:
- `main.py`
- `src/state.py`
- `src/asr.py`
- `src/llm.py`
- `src/tts.py`
- `client/index.html`
- Plus: dependency and environment notes, and end‑to‑end dataflow.

---

## 0) Big‑Picture Overview

### What it is
A **local, low‑latency voice agent** with:
- **ASR** (speech→text): Whisper (local) or Google SpeechRecognition (cloud)
- **LLM** (text→text): Ollama (local) or Hugging Face `transformers` fallback
- **TTS** (text→speech): `pyttsx3` (offline)
- **API/UI**: FastAPI backend with a minimalist web client

### Control Flow (end‑to‑end)
1. **Browser** captures mic audio while you hold the “Record” button.
2. **Browser** converts recorded WebM to **WAV** and POSTs to `POST /transcribe` with `engine` (`whisper` or `google`).
3. **Server** transcribes via **Whisper** or **Google** → returns `{ text, confidence }`.
4. **Server** appends `{role:user, content:text}` to **conversation state**.
5. **Server** calls **LLM** (Ollama or HF pipeline) with the **system prompt + history** → returns assistant reply.
6. **Server** appends `{role:assistant, content:reply}` to **conversation state**.
7. **Server** synthesizes reply via **TTS** → returns a WAV file.
8. **Browser** plays the WAV; loop repeats for 5+ turns.

### Inputs / Outputs (runtime)
- **Inputs**: user microphone audio (WAV), optional `engine`, ASR API key (for Google), env vars for models.
- **Outputs**: JSON (`/transcribe`, `/reply`), WAV binary (`/speak`), HTML UI at `/`.

---

## 1) Dependencies & Environment

### `requirements.txt`
```text
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9
pydantic==2.9.2
httpx==0.27.2
websockets==12.0
aiofiles==24.1.0

SpeechRecognition==3.10.4
openai-whisper==20231117
soundfile==0.12.1
pydub==0.25.1

transformers==4.44.2
accelerate==0.34.2

pyttsx3==2.98
numpy==1.26.4
```

### Environment variables used by the code
- `MAX_TURNS` — ring buffer size (pairs of user/assistant kept).
- `GOOGLE_SPEECH_API_KEY` — for `SpeechRecognition` → Google Web Speech.
- `LLM_BACKEND` — `"ollama"` or `"hf"` (default is `"hf"` in `src/llm.py`).
- `OLLAMA_URL` — defaults to `http://localhost:11434/api/chat`.
- `LLM_MODEL` — Ollama model name (`llama3` by default).
- `HF_MODEL` — HF text‑gen model (default: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`).
- `VOICE_RATE` — words per minute for pyttsx3 (default `"170"`).
- `VOICE_NAME` — optional substring to select a pyttsx3 voice.

> Note: README referenced a `.env.example`; if it’s not present, create `.env` yourself with the above.

---

## 2) `main.py` — FastAPI Server & Routes (Annotated)

```python
import os, uuid, tempfile, shutil                      # stdlib: env vars, unique IDs, temp dir mgmt, file ops
from pathlib import Path                                # convenient path handling
from fastapi import FastAPI, UploadFile, File, Form     # FastAPI primitives for app + typed request inputs
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse  # concrete response types
from fastapi.middleware.cors import CORSMiddleware      # enable CORS for local demo & simple clients
from pydantic import BaseModel                           # request body parsing / validation
from src.state import ConversationState                  # ring‑buffer conversation history
from src.asr import transcribe                           # ASR dispatcher (whisper/google)
from src.llm import chat                                 # LLM dispatcher (ollama/HF)
from src.tts import synthesize_to_wav                    # TTS synthesis

app = FastAPI(title="EX3 Voice Agent", version="1.0")   # create web app with metadata
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                                 # allow any origin for demo simplicity
    allow_credentials=True,
    allow_methods=["*"],                                 # allow all methods
    allow_headers=["*"],                                 # allow all headers
)

# Single in-memory conversation (for demo purposes)      # no DB; just a process-local state ring buffer
state = ConversationState(max_turns=int(os.environ.get("MAX_TURNS","8")))

class TextIn(BaseModel):                                 # pydantic model for JSON body with a single field
    text: str

@app.get("/")                                            # GET / — serve demo client
def home():
    html = Path("client/index.html").read_text(encoding="utf-8")  # read static HTML
    return HTMLResponse(html)                            # return raw HTML

@app.post("/reset")                                      # POST /reset — clear history
def reset():
    state.reset()                                        # drop all past messages
    return {"ok": True}                                  # confirm

@app.post("/transcribe")                                 # POST /transcribe — ASR endpoint
async def asr_endpoint(engine: str = Form("whisper"),    # engine from form field (default: whisper)
                       file: UploadFile = File(...)):    # wav file uploaded by client
    tmp = Path(tempfile.mkdtemp())                       # create temp dir for this request
    wav_path = tmp / f"in_{uuid.uuid4().hex}.wav"        # unique filename for uploaded audio
    with open(wav_path, "wb") as f:                      # write uploaded bytes to disk
        f.write(await file.read())
    text, conf = transcribe(                             # run ASR (whisper/google)
        str(wav_path),
        engine=engine,
        api_key=os.environ.get("GOOGLE_SPEECH_API_KEY")  # only used for google engine
    )
    shutil.rmtree(tmp, ignore_errors=True)               # cleanup temp dir
    return {"text": text, "confidence": conf}            # JSON result back to client

@app.post("/reply")                                      # POST /reply — LLM turn
async def reply_endpoint(data: TextIn):                  # body: {"text": "<user utterance>"}
    state.add_user(data.text)                            # add user message to history
    reply = chat(state.get_messages())                   # call LLM with system + history
    state.add_assistant(reply)                           # append assistant reply to history
    return {"reply": reply}                              # JSON reply (text only)

@app.post("/speak")                                      # POST /speak — TTS synthesis
async def speak_endpoint(data: TextIn):                  # body: {"text": "<assistant reply>"}
    tmp = Path(tempfile.mkdtemp())                       # fresh temp dir for output
    out_wav = tmp / f"tts_{uuid.uuid4().hex}.wav"        # unique target path
    synthesize_to_wav(data.text, str(out_wav))           # synthesize WAV with pyttsx3
    return FileResponse(                                 # return audio as a file download/stream
        str(out_wav), media_type="audio/wav", filename="reply.wav"
    )
```

**Key takeaways**
- The app exposes **four** routes: `/`, `/reset`, `/transcribe`, `/reply`, `/speak`.
- Conversation memory lives **in‑process** via `ConversationState`.
- Temporary files are cleaned up immediately after use for ASR, but TTS temp dirs are not deleted here (returned file remains accessible until OS/temp cleanup). If you want explicit cleanup, you can stream bytes then remove files.

---

## 3) `src/state.py` — Ring‑Buffer Conversation Memory (Annotated)

```python
from collections import deque                            # double‑ended queue for efficient pops from left
from typing import List, Dict, Any

class ConversationState:
    """Ring buffer conversation memory (system + N turns)."""
    def __init__(self, max_turns: int = 8,               # pairs of user/assistant to retain
                 system_prompt: str | None = None):
        self.max_turns = max_turns
        self.system_prompt = system_prompt or (          # default system prompt for the assistant
            "You are a helpful, concise voice assistant. "
            "Keep replies short (1-3 sentences) and ask clarifying questions when needed."
        )
        self.history: deque[Dict[str, str]] = deque()    # stores messages as dicts {role, content}

    def reset(self):                                     # remove entire history
        self.history.clear()

    def add_user(self, text: str):                       # append user message
        self.history.append({ "role": "user", "content": text })
        self._trim()

    def add_assistant(self, text: str):                  # append assistant message
        self.history.append({ "role": "assistant", "content": text })
        self._trim()

    def get_messages(self) -> List[Dict[str, str]]:      # system prompt + rolling history
        msgs = [{"role":"system","content": self.system_prompt}]
        msgs.extend(list(self.history))
        return msgs

    def _trim(self):                                     # enforce ring size: keep last max_turns pairs
        while len(self.history) > self.max_turns * 2:    # user + assistant = 2 per turn
            self.history.popleft()
```

---

## 4) `src/asr.py` — Speech‑to‑Text Engines (Annotated)

```python
import os, io                                            # stdlib (io not used directly, safe to remove)
from typing import Tuple
import speech_recognition as sr                          # SpeechRecognition wrapper for Google Web Speech

def transcribe_google(wav_path: str, api_key: str | None = None) -> Tuple[str, float]:
    recognizer = sr.Recognizer()                         # initialize recognizer
    with sr.AudioFile(wav_path) as source:               # open WAV
        audio = recognizer.record(source)                # read whole file
    try:
        text = recognizer.recognize_google(audio, key=api_key)  # send to Google Web Speech
        conf = 0.8  # Google Web Speech via SR does not return confidence; use a placeholder
        return text, conf
    except sr.UnknownValueError:                         # no transcription
        return "", 0.0
    except sr.RequestError as e:                         # network/API error
        raise RuntimeError(f"Google ASR request error: {e}")

def transcribe_whisper(wav_path: str, model_name: str = "base") -> Tuple[str, float]:
    import whisper                                       # lazy import: heavy dependency
    model = whisper.load_model(model_name)               # load local model (downloads once)
    result = model.transcribe(wav_path)                  # run transcription
    text = (result.get("text") or "").strip()            # normalized transcript
    # confidence proxy (avg no-speech prob) – Whisper doesn’t return a real conf score
    conf = 1.0 - float(result.get("segments", [{}])[0].get("no_speech_prob", 0.2))
    return text, conf

def transcribe(wav_path: str, engine: str = "whisper", api_key: str | None = None) -> Tuple[str, float]:
    engine = (engine or "whisper").lower()               # normalize selector
    if engine == "google":
        return transcribe_google(wav_path, api_key=api_key)
    return transcribe_whisper(wav_path)                  # default → whisper
```

**Notes**
- `conf` for Whisper is a **heuristic** using `no_speech_prob`. Treat it as a rough indicator.
- For faster Whisper, you can switch to **`tiny`** or **`base`** and/or use **FasterWhisper**.

---

## 5) `src/llm.py` — LLM Backends (Annotated)

```python
import os, json, httpx                                   # httpx used for Ollama HTTP API
from typing import List, Dict

def chat_ollama(messages: List[Dict[str,str]], model: str = "llama3") -> str:
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")  # Ollama chat endpoint
    payload = { "model": model, "messages": messages, "stream": False }    # non-streaming request
    with httpx.Client(timeout=60) as client:             # short-lived client
        r = client.post(url, json=payload)               # POST to Ollama
        r.raise_for_status()                             # raise on 4xx/5xx
        data = r.json()                                  # parse JSON
        return data.get("message", {}).get("content", "")# extract assistant content

def chat_hf(messages: List[Dict[str,str]], model: str = "distilgpt2") -> str:
    # Simple HF pipeline fallback; concatenates dialog into a prompt
    from transformers import pipeline, set_seed          # pipeline auto-downloads model/weights
    prompt = ""
    for m in messages:                                   # rebuild conversation prompt
        role = m["role"]
        if role == "system":
            continue
        prefix = "User" if role == "user" else "Assistant"
        prompt += f"{prefix}: {m['content']}
"

    prompt += "Assistant: "                              # where generation starts
    gen = pipeline("text-generation", model=model, device_map="auto")  # auto place on CPU/GPU
    out = gen(prompt, max_new_tokens=128, do_sample=True, temperature=0.7)[0]["generated_text"]
    return out.split("Assistant:",1)[-1].strip()         # simple post-process

def chat(messages):
    backend = os.environ.get("LLM_BACKEND", "hf").lower() # default is HF unless env says otherwise
    if backend == "hf":
        return chat_hf(messages, os.environ.get("HF_MODEL","TinyLlama/TinyLlama-1.1B-Chat-v1.0"))
    return chat_ollama(messages, os.environ.get("LLM_MODEL","llama3"))
```

**Notes**
- For **deterministic** behavior, add `seed` and disable sampling.
- Ollama expects **chat‑style** messages `[{role, content}]`—we reuse state’s `get_messages()`.

---

## 6) `src/tts.py` — Text‑to‑Speech (Annotated)

```python
import os, tempfile                                     # tempfile not used in this version (safe to remove)
import pyttsx3                                          # offline TTS engine (system voices)

def synthesize_to_wav(text: str, out_path: str) -> str:
    engine = pyttsx3.init()                             # init engine
    # Optional tuning
    rate = int(os.environ.get("VOICE_RATE", "170"))     # speaking rate (words per minute-ish)
    engine.setProperty('rate', rate)
    voice_name = os.environ.get("VOICE_NAME")           # optional voice selection by substring
    if voice_name:
        for v in engine.getProperty('voices'):
            if voice_name.lower() in (v.name or '').lower():
                engine.setProperty('voice', v.id)
                break
    engine.save_to_file(text, out_path)                 # synthesize to disk (non-blocking enqueue)
    engine.runAndWait()                                 # block until TTS completes
    return out_path                                     # return path for FileResponse
```

**Notes**
- On Windows/macOS/Linux, available voices differ. Use `VOICE_NAME` to pick a distinct system voice.

---

## 7) `client/index.html` — Browser UI & Recorder (Annotated)

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>EX3 Voice Agent Demo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; }
    .bubble { padding: .6rem .8rem; border-radius: 10px; margin: .4rem 0; }
    .user { background: #e8f1ff; }
    .bot { background: #f4f4f4; }
    button { padding: .6rem 1rem; margin-right: .5rem; }
    #log { white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>EX3 Voice Agent</h1>
  <p>Hold <b>Record</b>, speak, then release. The server will transcribe your audio, generate a reply, and speak it back. At least 5 turns should work.</p>
  <div>
    <button id="record">🎙️ Record</button>
    <select id="asr">
      <option value="whisper">whisper</option>
      <option value="google">google</option>
    </select>
    <button id="reset">Reset</button>
  </div>
  <div id="chat"></div>
  <audio id="player" controls></audio>

<script>
  const btn = document.getElementById('record');    // record button
  const asrSel = document.getElementById('asr');    // ASR engine selector
  const chat = document.getElementById('chat');     // chat container
  const player = document.getElementById('player'); // audio player for TTS
  const resetBtn = document.getElementById('reset');// reset conversation

  function addBubble(text, who) {                   // render helper
    const div = document.createElement('div');
    div.className = 'bubble ' + (who === 'user' ? 'user' : 'bot');
    div.textContent = text;
    chat.appendChild(div);
    window.scrollTo(0, document.body.scrollHeight);
  }

  let mediaRecorder, chunks = [];                   // Web MediaRecorder state

  async function startRecording() {                 // begin mic capture
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    chunks = [];
    mediaRecorder.ondataavailable = e => chunks.push(e.data);
    mediaRecorder.onstop = onStop;                  // callback when user releases button
    mediaRecorder.start();
  }

  async function onStop() {                         // when recording ends
    const blob = new Blob(chunks, { type: 'audio/webm' });  // audio in webm
    const wavBlob = await blobToWav(blob);                  // convert to WAV in browser
    const fd = new FormData();
    fd.append('engine', asrSel.value);                      // "whisper" or "google"
    fd.append('file', wavBlob, 'input.wav');                // attach WAV
    const t = await fetch('/transcribe', { method: 'POST', body: fd }).then(r=>r.json());
    if (!t.text) return;                                    // no text -> stop
    addBubble(t.text, 'user');                              // show user text
    const r = await fetch('/reply', {                       // ask LLM for a reply
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({text: t.text})
    }).then(r=>r.json());
    addBubble(r.reply, 'bot');                              // show assistant text
    const audio = await fetch('/speak', {                   // synthesize speech for reply
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({text: r.reply})
    });
    const aBlob = await audio.blob();                       // get WAV blob
    player.src = URL.createObjectURL(aBlob);                // set audio src
    player.play();                                          // play
  }

  btn.onmousedown = startRecording;                         // mouse press = start
  btn.onmouseup = () => mediaRecorder && mediaRecorder.stop();  // mouse release = stop
  btn.ontouchstart = (e)=>{ e.preventDefault(); startRecording(); };  // mobile touch start
  btn.ontouchend = (e)=>{ e.preventDefault(); mediaRecorder && mediaRecorder.stop(); }; // touch end

  resetBtn.onclick = async () => {                          // clear history on server and UI
    await fetch('/reset', { method: 'POST' });
    chat.innerHTML = '';
  };

  // Convert WebM to WAV in browser
  async function blobToWav(blob) {
    const arrayBuffer = await blob.arrayBuffer();           // read webm to ArrayBuffer
    // Decode via WebAudio then re-encode PCM WAV
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const audioBuf = await audioCtx.decodeAudioData(arrayBuffer);  // decode compressed
    const wavBuffer = audioBufferToWav(audioBuf);                  // encode PCM WAV
    return new Blob([wavBuffer], { type: 'audio/wav' });
  }

  // Minimal WAV encoder (mono)
  function audioBufferToWav(buffer, opt) {
    opt = opt || {}
    var numChannels = 1
    var sampleRate = buffer.sampleRate
    var format = 1
    var bitDepth = 16

    var samples = buffer.getChannelData(0)
    var blockAlign = numChannels * bitDepth / 8
    var byteRate = sampleRate * blockAlign
    var dataSize = samples.length * blockAlign

    var buffer2 = new ArrayBuffer(44 + dataSize)
    var view = new DataView(buffer2)

    function writeString(view, offset, string) {
      for (var i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i))
      }
    }

    var offset = 0
    writeString(view, 0, 'RIFF'); offset += 4
    view.setUint32(offset, 36 + dataSize, true); offset += 4
    writeString(view, offset, 'WAVE'); offset += 4
    writeString(view, offset, 'fmt '); offset += 4
    view.setUint32(offset, 16, true); offset += 4
    view.setUint16(offset, format, true); offset += 2
    view.setUint16(offset, numChannels, true); offset += 2
    view.setUint32(offset, sampleRate, true); offset += 4
    view.setUint32(offset, byteRate, true); offset += 4
    view.setUint16(offset, blockAlign, true); offset += 2
    view.setUint16(offset, bitDepth, true); offset += 2
    writeString(view, offset, 'data'); offset += 4
    view.setUint32(offset, dataSize, true); offset += 4

    // PCM samples
    var idx = 44
    for (var i = 0; i < samples.length; i++, idx += 2) {
      var s = Math.max(-1, Math.min(1, samples[i]))
      view.setInt16(idx, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
    }
    return buffer2
  }
</script>
</body>
</html>
```

---

## 8) API Contracts (I/O Summary)

| Endpoint | Method | Request | Response | Notes |
|---|---|---|---|---|
| `/` | GET | – | HTML page | Demo client UI |
| `/reset` | POST | – | `{ ok: true }` | Clears conversation state |
| `/transcribe` | POST | `multipart/form-data` with `engine`, `file` (WAV) | `{ text: str, confidence: float }` | `engine` ∈ {`whisper`,`google`} |
| `/reply` | POST | JSON `{ "text": str }` | `{ reply: str }` | LLM based on `LLM_BACKEND` |
| `/speak` | POST | JSON `{ "text": str }` | **WAV** | WAV of assistant reply |

---

## 9) Data Flow & Artifacts

- **Temp WAVs (ASR)**: created under OS temp; **deleted** right after transcription.
- **Temp WAVs (TTS)**: created and returned; consider adding periodic cleanup if storing many replies.
- **State**: conversation is **in memory** (resets on process restart). If you need persistence, add a DB or session store.

---

## 10) How to Run (recap)

```bash
python -m venv .venv && source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
# (optional) create .env with LLM/ASR/TTS choices (see env list above)
uvicorn main:app --reload --port 8000
# open http://localhost:8000/
```

- For **Ollama** backend, install Ollama and pull a small model, e.g. `ollama run llama3`.
- For **Whisper**, the first run downloads the model; choose a smaller size for speed.

---

## 11) Troubleshooting

- **No audio**: ensure mic permissions are granted in the browser; try Chrome/Edge/Firefox.
- **Whisper slow**: set engine to `tiny` or `base`; consider FasterWhisper.
- **Ollama errors**: confirm `OLLAMA_URL`, that the model is pulled, and the service is running.
- **Voices**: on some OS configurations, `pyttsx3` may expose limited voices; set `VOICE_NAME` to select.

---

## 12) What to Modify Next

- Add **streaming** responses (server‑sent events) for partial transcripts or token‑streamed LLM output.
- Swap **TTS** module to a neural voice (e.g., Coqui‑TTS or Edge‑TTS) while keeping `/speak` contract.
- Persist state per session/user via cookies + KV store.

---

**End of document.**
