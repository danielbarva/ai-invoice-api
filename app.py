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
        <title>AI Invoice & Text Processing API</title>
        <meta charset="utf-8">
        <style>
          body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            line-height: 1.6;
            padding: 0 16px;
            background: #f8f9fb;
            color: #222;
          }
          h1 {
            margin-bottom: 10px;
          }
          .box {
            background: white;
            border: 1px solid #ddd;
            padding: 20px;
            border-radius: 12px;
            margin-top: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
          }
          textarea {
            width: 100%;
            min-height: 140px;
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 8px;
            font-size: 16px;
            resize: vertical;
            box-sizing: border-box;
          }
          select, button {
            padding: 10px 14px;
            font-size: 16px;
            border-radius: 8px;
            border: 1px solid #ccc;
          }
          button {
            background: #2563eb;
            color: white;
            border: none;
            cursor: pointer;
          }
          button:hover {
            background: #1d4ed8;
          }
          .row {
            display: flex;
            gap: 12px;
            align-items: center;
            margin: 14px 0;
            flex-wrap: wrap;
          }
          pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            background: #111827;
            color: #f9fafb;
            padding: 16px;
            border-radius: 10px;
            min-height: 80px;
          }
          .small {
            color: #666;
            font-size: 14px;
          }
          code {
            background: #eef2ff;
            padding: 3px 7px;
            border-radius: 6px;
          }
        </style>
      </head>
      <body>
        <h1>AI Invoice & Text Processing API</h1>
        <p>Aplikace běží úspěšně. Zadej text nebo otázku, vyber režim a odešli požadavek.</p>

        <div class="box">
          <label for="text"><strong>Vstupní text / otázka:</strong></label>
          <textarea id="text" placeholder="Např. 2x monitor 5000 Kč, 1x myš 1000 Kč nebo Co je Python?"></textarea>

          <div class="row">
            <label for="mode"><strong>Režim:</strong></label>
            <select id="mode">
              <option value="ai">Shrnutí</option>
              <option value="invoice">Faktura</option>
              <option value="chat">Otázka / chat</option>
            </select>

            <button onclick="sendRequest()">Odeslat</button>
          </div>

          <p class="small">
            Režimy používají endpointy <code>/ai</code>, <code>/invoice</code> a <code>/chat</code>.
          </p>
        </div>

        <div class="box">
          <h3>Výstup:</h3>
          <pre id="output">Zatím žádná odpověď.</pre>
        </div>

        <div class="box">
          <h3>Dostupné endpointy:</h3>
          <ul>
            <li><code>/ping</code></li>
            <li><code>/status</code></li>
            <li><code>/ai</code></li>
            <li><code>/invoice</code></li>
            <li><code>/chat</code></li>
          </ul>
        </div>

        <script>
          async function sendRequest() {
            const text = document.getElementById("text").value.trim();
            const mode = document.getElementById("mode").value;
            const output = document.getElementById("output");

            if (!text) {
              output.textContent = "Zadej nejdřív nějaký text nebo otázku.";
              return;
            }

            output.textContent = "Načítám odpověď...";

            try {
              const response = await fetch("/" + mode, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json"
                },
                body: JSON.stringify({ text: text })
              });

              const data = await response.json();

              if (!response.ok) {
                output.textContent = JSON.stringify(data, null, 2);
                return;
              }

              if (mode === "ai") {
                output.textContent = data.response || "Žádná odpověď.";
              } else if (mode === "invoice") {
                output.textContent = data.invoice || "Žádná odpověď.";
              } else if (mode === "chat") {
                output.textContent = data.answer || "Žádná odpověď.";
              } else {
                output.textContent = JSON.stringify(data, null, 2);
              }
            } catch (error) {
              output.textContent = "Chyba při komunikaci se serverem: " + error;
            }
          }
        </script>
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


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({
            "error": "Chybi pole 'text'"
        }), 400

    prompt = f"""
Odpovez cesky jasne a vecne na nasledujici otazku nebo zadani.

{text}
"""

    try:
        result = ask_ai(prompt)
        return jsonify({
            "answer": result
        }), 200
    except requests.RequestException as e:
        return jsonify({
            "error": "Nepodarilo se spojit s AI API",
            "detail": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    app.run(host="0.0.0.0", port=port)
