from flask import Flask, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"

def ask_ollama(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3.2:3b",
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()

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

    result = ask_ollama(prompt)
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
        result = ask_ollama(prompt)
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
