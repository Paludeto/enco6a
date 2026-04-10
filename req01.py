"""
REQ-01 – Visualização de vagas em tempo real
Execute: python req01.py  →  abra http://localhost:8000
"""

import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- Vagas ---
TOTAL = 30
vagas = {f"V{i:02d}": random.choice(["livre", "ocupada"]) for i in range(1, TOTAL + 1)}
lock = threading.Lock()


def simular():
    """Altera 1-4 vagas aleatórias a cada 5 segundos."""
    while True:
        time.sleep(5)
        with lock:
            for v in random.sample(list(vagas), k=random.randint(1, 4)):
                vagas[v] = "livre" if vagas[v] == "ocupada" else "ocupada"


threading.Thread(target=simular, daemon=True).start()

# --- Interface ---
HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="5">
  <title>Estacionamento Campus</title>
  <style>
    body    {{ font-family: sans-serif; background: #f3f4f6; padding: 24px; margin: 0; }}
    h1      {{ color: #1a56db; margin-bottom: 4px; }}
    .resumo {{ margin-bottom: 20px; color: #374151; }}

    /* Mapa */
    .mapa {{
      display: inline-block;
      background: #4b5563;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    }}

    /* Edifícios */
    .edificio {{
      background: #1f2937;
      color: #d1d5db;
      text-align: center;
      padding: 12px 0;
      border-radius: 6px;
      font-weight: bold;
      font-size: 0.85em;
      letter-spacing: 1px;
      margin-bottom: 10px;
    }}
    .edificios {{ display: flex; gap: 8px; margin-bottom: 10px; }}
    .edificios .edificio {{ flex: 1; margin-bottom: 0; }}

    /* Rua principal (entrada) */
    .rua {{
      height: 36px;
      background: #374151;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 10px;
      margin-bottom: 6px;
      position: relative;
    }}
    .rua::after {{
      content: '';
      position: absolute;
      left: 10px; right: 10px; top: 50%;
      border-top: 2px dashed #fbbf24;
    }}
    .tag {{
      background: #fbbf24;
      color: #000;
      font-size: 0.65em;
      font-weight: bold;
      padding: 2px 8px;
      border-radius: 3px;
      z-index: 1;
    }}

    /* Fileiras de vagas */
    .fileira {{ display: flex; gap: 3px; margin: 2px 0; }}

    /* Corredor interno entre fileiras */
    .corredor {{
      height: 28px;
      background: #374151;
      border-radius: 2px;
      margin: 3px 0;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }}
    .corredor::after {{
      content: '';
      position: absolute;
      left: 8px; right: 8px; top: 50%;
      border-top: 2px dashed #fbbf2466;
    }}
    .corredor-nome {{
      font-size: 0.6em;
      color: #9ca3af;
      z-index: 1;
      background: #374151;
      padding: 0 6px;
    }}

    /* Vagas individuais */
    .vaga {{
      width: 50px; height: 76px;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      border: 2px solid rgba(255,255,255,0.25);
      border-radius: 3px;
      color: #fff; font-weight: bold;
      font-size: 0.72em;
    }}
    .livre   {{ background: #16a34a; }}
    .ocupada {{ background: #dc2626; }}
    .vaga .num    {{ font-size: 1.1em; }}
    .vaga .status {{ font-size: 0.75em; margin-top: 3px; opacity: 0.85; }}

    .legenda {{
      display: flex; gap: 16px; margin-top: 10px; align-items: center;
    }}
    .legenda-item {{ display: flex; align-items: center; gap: 5px; font-size: 0.8em; color: #374151; }}
    .dot {{ width: 12px; height: 12px; border-radius: 3px; }}

    footer {{ margin-top: 20px; color: #9ca3af; font-size: 0.8em; }}
  </style>
</head>
<body>
  <h1>Estacionamento Campus</h1>
  <p class="resumo">
    <strong style="color:#16a34a">{livres} livres</strong> &nbsp;·&nbsp;
    <strong style="color:#dc2626">{ocupadas} ocupadas</strong> &nbsp;·&nbsp;
    {total} total
  </p>

  <div class="mapa">

    <!-- Edificios no topo -->
    <div class="edificios">
      <div class="edificio">BLOCO A</div>
      <div class="edificio">BIBLIOTECA</div>
      <div class="edificio">BLOCO B</div>
    </div>

    <!-- Rua de entrada -->
    <div class="rua">
      <span class="tag">ENTRADA &rarr;</span>
      <span class="tag">&larr; SAIDA</span>
    </div>

    <!-- Fileira A: V01–V10 -->
    <div class="fileira">{fileira_a}</div>

    <div class="corredor">
      <span class="corredor-nome">CORREDOR A &ndash; B</span>
    </div>

    <!-- Fileira B: V11–V20 -->
    <div class="fileira">{fileira_b}</div>

    <div class="corredor">
      <span class="corredor-nome">CORREDOR B &ndash; C</span>
    </div>

    <!-- Fileira C: V21–V30 -->
    <div class="fileira">{fileira_c}</div>

  </div>

  <div class="legenda">
    <div class="legenda-item"><div class="dot" style="background:#16a34a"></div> Livre</div>
    <div class="legenda-item"><div class="dot" style="background:#dc2626"></div> Ocupada</div>
  </div>

  <footer>Atualizado a cada 5 s &nbsp;&middot;&nbsp; REQ-01 &ndash; ENCO6A</footer>
</body>
</html>"""


def _fileira(snapshot, inicio, fim):
    return "".join(
        f'<div class="vaga {snapshot[vid]}">'
        f'<span class="num">{vid}</span>'
        f'<span class="status">{"livre" if snapshot[vid] == "livre" else "ocupada"}</span>'
        f'</div>'
        for vid in sorted(snapshot)[inicio:fim]
    )


def renderizar(snapshot):
    livres = sum(1 for s in snapshot.values() if s == "livre")
    return HTML.format(
        livres=livres,
        ocupadas=len(snapshot) - livres,
        total=len(snapshot),
        fileira_a=_fileira(snapshot, 0, 10),
        fileira_b=_fileira(snapshot, 10, 20),
        fileira_c=_fileira(snapshot, 20, 30),
    )


# --- Servidor ---
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # silencia logs no terminal

    def do_GET(self):
        with lock:
            snapshot = dict(vagas)

        if self.path == "/api/vagas":
            body = json.dumps(snapshot).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        else:
            body = renderizar(snapshot).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")

        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("localhost", 8000), Handler)
    print("Rodando em http://localhost:8000 — Ctrl+C para encerrar.")
    server.serve_forever()
