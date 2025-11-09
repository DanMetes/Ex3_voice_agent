import os, json, httpx
from typing import List, Dict

def chat_ollama(messages: List[Dict[str,str]], model: str = "llama3") -> str:
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
    payload = { "model": model, "messages": messages, "stream": False }
    with httpx.Client(timeout=60) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "")

def chat_hf(messages: List[Dict[str,str]], model: str = "distilgpt2") -> str:
    # Simple HF pipeline fallback; concatenates dialog to a prompt
    from transformers import pipeline, set_seed
    prompt = ""
    for m in messages:
        role = m["role"]
        if role == "system":
            continue
        prefix = "User" if role == "user" else "Assistant"
        prompt += f"{prefix}: {m['content']}\n"

    prompt += "Assistant: "
    gen = pipeline("text-generation", model=model, device_map="auto")
    out = gen(prompt, max_new_tokens=128, do_sample=True, temperature=0.7)[0]["generated_text"]
    return out.split("Assistant:",1)[-1].strip()

def chat(messages):
    backend = os.environ.get("LLM_BACKEND", "hf").lower()  # change default to "hf"
    if backend == "hf":
        return chat_hf(messages, os.environ.get("HF_MODEL","TinyLlama/TinyLlama-1.1B-Chat-v1.0"))
    return chat_ollama(messages, os.environ.get("LLM_MODEL","llama3"))
