import os, uuid, tempfile, shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.state import ConversationState
from src.asr import transcribe
from src.llm import chat
from src.tts import synthesize_to_wav

app = FastAPI(title="EX3 Voice Agent", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single in-memory conversation (for demo purposes)
state = ConversationState(max_turns=int(os.environ.get("MAX_TURNS","8")))

class TextIn(BaseModel):
    text: str

@app.get("/")
def home():
    html = Path("client/index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)

@app.post("/reset")
def reset():
    state.reset()
    return {"ok": True}

@app.post("/transcribe")
async def asr_endpoint(engine: str = Form("whisper"), file: UploadFile = File(...)):
    tmp = Path(tempfile.mkdtemp())
    wav_path = tmp / f"in_{uuid.uuid4().hex}.wav"
    with open(wav_path, "wb") as f:
        f.write(await file.read())
    text, conf = transcribe(str(wav_path), engine=engine, api_key=os.environ.get("GOOGLE_SPEECH_API_KEY"))
    shutil.rmtree(tmp, ignore_errors=True)
    return {"text": text, "confidence": conf}

@app.post("/reply")
async def reply_endpoint(data: TextIn):
    state.add_user(data.text)
    reply = chat(state.get_messages())
    state.add_assistant(reply)
    return {"reply": reply}

@app.post("/speak")
async def speak_endpoint(data: TextIn):
    tmp = Path(tempfile.mkdtemp())
    out_wav = tmp / f"tts_{uuid.uuid4().hex}.wav"
    synthesize_to_wav(data.text, str(out_wav))
    return FileResponse(str(out_wav), media_type="audio/wav", filename="reply.wav")
