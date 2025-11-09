import os, io
from typing import Tuple
import speech_recognition as sr

def transcribe_google(wav_path: str, api_key: str | None = None) -> Tuple[str, float]:
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, key=api_key)
        conf = 0.8  # Google Web Speech doesn't return conf via SpeechRecognition
        return text, conf
    except sr.UnknownValueError:
        return "", 0.0
    except sr.RequestError as e:
        raise RuntimeError(f"Google ASR request error: {e}")

def transcribe_whisper(wav_path: str, model_name: str = "base") -> Tuple[str, float]:
    import whisper  # pip install whisper
    model = whisper.load_model(model_name)
    result = model.transcribe(wav_path)
    text = (result.get("text") or "").strip()
    # confidence proxy (avg no-speech prob) – not provided directly
    conf = 1.0 - float(result.get("segments", [{}])[0].get("no_speech_prob", 0.2))
    return text, conf

def transcribe(wav_path: str, engine: str = "whisper", api_key: str | None = None) -> Tuple[str, float]:
    engine = (engine or "whisper").lower()
    if engine == "google":
        return transcribe_google(wav_path, api_key=api_key)
    return transcribe_whisper(wav_path)
