from flask import Flask, request, jsonify
import requests
from datetime import datetime
import os

app = Flask(__name__)

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


@app.route("/", methods=["GET"])
def home():
    return """
    <html>
      <head>
        <title>AI Invoice API</title>
        <style>
          body {
            font-family: Arial;
            max-width: 800px;
            margin: 40px auto;
            line-height: 1.6;
          }
          h1 { color: #333; }
          code {
            background: #f4f4f4;
            padding: 4px 8px;
            border-radius: 6px;
          }
          .box {
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
          }
        </style>
      </head>
      <body>
        <h1>AI Invoice & Text Processing API</h1>
        <p>Aplikace běží úspěšně.</p>

        <div class="box">
          <h3>Endpointy:</h3>
          <ul>
            <li><code>/ping</code></li>
            <li><code>/status</code></li>
            <li><code>/ai</code></li>
            <li><code>/invoice</code></li>
          </ul>
        </div>
      </body>
    </html>
    """


@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200


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

    prompt = f"""
Zkrat nasledujici text na jednu kratkou vetu.

Text:
{text}
"""

    try:
        result = ask_ai(prompt)
        return jsonify({"response": result}), 200
    except requests.RequestException as e:
        return jsonify({
            "error": "Nepodarilo se spojit s AI API",
            "detail": str(e)
        }), 500


@app.route("/invoice", methods=["POST"])
def invoice():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "Chybi pole 'text'"}), 400

    prompt = f"""
Odpovidej POUZE vystupem, bez komentaru.

Vytvor fakturu z nasledujiciho textu.

Text:
{text}

Pravidla:
- pouzij pouze informace z textu
- kazdou polozku napis na novy radek
- nic nevymyslej
- nepouzivej "..."

Format:
Polozky:
- nazev | mnozstvi | cena za kus | celkem

Celkem:
celkova cena v Kc
"""

    try:
        result = ask_ai(prompt)
        return jsonify({
            "invoice": result
        }), 200
    except requests.RequestException as e:
        return jsonify({
            "error": "Nepodarilo se spojit s AI API",
            "detail": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    app.run(host="0.0.0.0", port=port)
