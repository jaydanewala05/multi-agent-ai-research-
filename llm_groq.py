import os
import requests

# ------------------------------
# LOAD GROQ API KEY FROM ENV
# ------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in environment variables")

# GROQ API URL
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model
MODEL_NAME = "llama-3.1-8b-instant"


def groq_generate(prompt, max_tokens=300):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"Groq API Error: {response.text}")

    return response.json()["choices"][0]["message"]["content"]
