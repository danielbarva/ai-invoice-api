from flask import Flask, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

def ask_ai(prompt):
    response = requests.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gemma3:27b",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        timeout=120
    )

    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

@app.route("/ping", methods=["GET"])
def ping():
    return "pong",200

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat(),
        "author": "heslo"
    }), 200

@app.route("/ai", methods=["POST"])
def ai():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({
            "error": "Chybi pole 'text'"
        }), 400

    prompt = f"Odpovez jednou kratkou vetou:\n{text}"

    result = ask_ai(prompt)
    return jsonify({"response": result}), 200

@app.route("/invoice", methods=["POST"])
def invoice():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "Chybi pole 'text'"}), 400

    prompt = f"""
Vytvor fakturu z nasledujiciho textu.

Text:
{text}

Pravidla:
- pouzij pouze informace z textu
- nic nevysvetluj
- nic nevymyslej
- odpoved musi byt presne ve formatu nize

Forma:
Polozky:
- nazev | mnozstvi | cena za kus | celkem

Pokud je vice polozek, kazdou napis na novy radek.

Celkem:
celkova cena v Kc (soucet vsech polozek)
"""

    try:
        result = ask_ai(prompt)
        return jsonify({
            "invoice" :result
        }), 200
    except requests.RequestException as e:
        return jsonify({
            "error": "Nepodarilo se spojit s Ollamou",
            "detail": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
