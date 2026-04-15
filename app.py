from flask import Flask, request, jsonify
import requests
from datetime import datetime
import os
import time
from sqlalchemy import create_engine, text

app = Flask(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///local.db")

engine = create_engine(DATABASE_URL)


def wait_for_db():
    for _ in range(10):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception:
            time.sleep(2)
    raise Exception("Nepodarilo se pripojit k databazi.")


def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                input_text TEXT NOT NULL,
                output_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()


def save_history(request_type, input_text, output_text):
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO history (type, input_text, output_text)
                VALUES (:type, :input_text, :output_text)
            """),
            {
                "type": request_type,
                "input_text": input_text,
                "output_text": output_text
            }
        )
        conn.commit()


def load_history():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, type, input_text, output_text, created_at
            FROM history
            ORDER BY created_at DESC
            LIMIT 20
        """))
        rows = []
        for row in result:
            rows.append({
                "id": row[0],
                "type": row[1],
                "input_text": row[2],
                "output_text": row[3],
                "created_at": str(row[4])
            })
        return rows


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
            max-width: 1000px;
            margin: 40px auto;
            line-height: 1.6;
            padding: 0 16px;
            background: #f8f9fb;
            color: #222;
          }
          h1 { margin-bottom: 10px; }
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
          button:hover { background: #1d4ed8; }
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
          .small { color: #666; font-size: 14px; }
          code {
            background: #eef2ff;
            padding: 3px 7px;
            border-radius: 6px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
          }
          th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            vertical-align: top;
          }
          th { background: #f3f4f6; }
        </style>
      </head>
      <body>
        <h1>AI Invoice & Text Processing API</h1>
        <p>Aplikace zpracovává text pomocí AI a ukládá historii do PostgreSQL databáze.</p>

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
            <button onclick="loadHistory()">Načíst historii</button>
          </div>

          <p class="small">
            Režimy používají endpointy <code>/ai</code>, <code>/invoice</code>, <code>/chat</code> a historie se ukládá do databáze.
          </p>
        </div>

        <div class="box">
          <h3>Výstup:</h3>
          <pre id="output">Zatím žádná odpověď.</pre>
        </div>

        <div class="box">
          <h3>Historie z databáze:</h3>
          <div id="history">Zatím nenačteno.</div>
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
                headers: { "Content-Type": "application/json" },
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
              }
            } catch (error) {
              output.textContent = "Chyba při komunikaci se serverem: " + error;
            }
          }

          async function loadHistory() {
            const historyDiv = document.getElementById("history");
            historyDiv.innerHTML = "Načítám historii...";

            try {
              const response = await fetch("/history");
              const data = await response.json();

              if (!response.ok) {
                historyDiv.textContent = JSON.stringify(data, null, 2);
                return;
              }

              if (!data.length) {
                historyDiv.textContent = "V databázi zatím nejsou žádná data.";
                return;
              }

              let html = "<table><tr><th>ID</th><th>Typ</th><th>Vstup</th><th>Výstup</th><th>Čas</th></tr>";
              for (const row of data) {
                html += `<tr>
                  <td>${row.id}</td>
                  <td>${row.type}</td>
                  <td>${row.input_text}</td>
                  <td>${row.output_text}</td>
                  <td>${row.created_at}</td>
                </tr>`;
              }
              html += "</table>";
              historyDiv.innerHTML = html;
            } catch (error) {
              historyDiv.textContent = "Chyba při načítání historie: " + error;
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


@app.route("/history", methods=["GET"])
def history():
    try:
        return jsonify(load_history()), 200
    except Exception as e:
        return jsonify({
            "error": "Nepodarilo se nacist historii z databaze",
            "detail": str(e)
        }), 500


@app.route("/ai", methods=["POST"])
def ai():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "Chybi pole 'text'"}), 400

    prompt = f"""
Zkrat nasledujici text na jednu kratkou vetu.

Text:
{text}
"""

    try:
        result = ask_ai(prompt)
        save_history("ai", text, result)
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
        save_history("invoice", text, result)
        return jsonify({"invoice": result}), 200
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
        return jsonify({"error": "Chybi pole 'text'"}), 400

    prompt = f"""
Odpovez cesky jasne a vecne na nasledujici otazku nebo zadani.

{text}
"""

    try:
        result = ask_ai(prompt)
        save_history("chat", text, result)
        return jsonify({"answer": result}), 200
    except requests.RequestException as e:
        return jsonify({
            "error": "Nepodarilo se spojit s AI API",
            "detail": str(e)
        }), 500


wait_for_db()
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
