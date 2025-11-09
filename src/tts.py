import os, tempfile
import pyttsx3

def synthesize_to_wav(text: str, out_path: str) -> str:
    engine = pyttsx3.init()
    # Optional tuning
    rate = int(os.environ.get("VOICE_RATE", "170"))
    engine.setProperty('rate', rate)
    voice_name = os.environ.get("VOICE_NAME")
    if voice_name:
        for v in engine.getProperty('voices'):
            if voice_name.lower() in (v.name or '').lower():
                engine.setProperty('voice', v.id)
                break
    engine.save_to_file(text, out_path)
    engine.runAndWait()
    return out_path
