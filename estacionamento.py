"""
ENCO6A – Estacionamento Campus
REQ-01 + REQ-04: visualização em tempo real com login persistente

Execute: python estacionamento.py  →  abra http://localhost:8000

Sessão persistida via cookie + session.json no servidor.
Sem dependências externas.
"""

import hashlib
import json
import os
import random
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8000
SESSION_FILE = "session.json"

USUARIOS = {
    "aluno1": hashlib.sha256("senha123".encode()).hexdigest(),
    "aluno2": hashlib.sha256("abc456".encode()).hexdigest(),
}

# ---------------------------------------------------------------------------
# Vagas (REQ-01)
# ---------------------------------------------------------------------------

TOTAL = 30
vagas = {f"V{i:02d}": random.choice(["livre", "ocupada"]) for i in range(1, TOTAL + 1)}
lock = threading.Lock()


def simular():
    """Altera 1–4 vagas aleatórias a cada 5 segundos."""
    while True:
        time.sleep(5)
        with lock:
            for v in random.sample(list(vagas), k=random.randint(1, 4)):
                vagas[v] = "livre" if vagas[v] == "ocupada" else "ocupada"


threading.Thread(target=simular, daemon=True).start()

# ---------------------------------------------------------------------------
# Persistência de sessão (REQ-04)
# ---------------------------------------------------------------------------

def _ler_sessoes() -> dict:
    if not os.path.exists(SESSION_FILE):
        return {}
    try:
        with open(SESSION_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _salvar_sessoes(sessoes: dict) -> None:
    with open(SESSION_FILE, "w") as f:
        json.dump(sessoes, f)


def criar_sessao(usuario: str) -> str:
    token = secrets.token_hex(32)
    sessoes = _ler_sessoes()
    sessoes[token] = usuario
    _salvar_sessoes(sessoes)
    return token


def validar_sessao(token: str) -> str | None:
    if not token:
        return None
    return _ler_sessoes().get(token)


def remover_sessao(token: str) -> None:
    sessoes = _ler_sessoes()
    sessoes.pop(token, None)
    _salvar_sessoes(sessoes)


def obter_token_do_cookie(cookie_header: str) -> str:
    for parte in cookie_header.split(";"):
        chave, _, valor = parte.strip().partition("=")
        if chave == "sessao":
            return valor
    return ""

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

ESTILO_LOGIN = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: Arial, sans-serif;
    background: #f0f2f5;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
  }
  .card {
    background: #fff;
    border-radius: 12px;
    padding: 36px 40px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.10);
    width: 340px;
  }
  h1 { font-size: 1.3rem; color: #1a1a2e; margin-bottom: 6px; }
  .subtitle { font-size: 0.85rem; color: #888; margin-bottom: 24px; }
  label { display: block; font-size: 0.85rem; color: #444; margin-bottom: 4px; }
  input[type=text], input[type=password] {
    width: 100%; padding: 10px 12px;
    border: 1px solid #ddd; border-radius: 8px;
    font-size: 0.95rem; margin-bottom: 16px;
    outline: none; transition: border 0.2s;
  }
  input:focus { border-color: #4f46e5; }
  .btn {
    width: 100%; padding: 11px;
    background: #4f46e5; color: #fff;
    border: none; border-radius: 8px;
    font-size: 1rem; cursor: pointer;
    transition: background 0.2s;
  }
  .btn:hover { background: #4338ca; }
  .erro { color: #dc2626; font-size: 0.85rem; margin-bottom: 14px; }
"""

HTML_MAPA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="5">
  <title>Estacionamento Campus</title>
  <style>
    body    {{ font-family: sans-serif; background: #f3f4f6; padding: 24px; margin: 0; }}
    h1      {{ color: #1a56db; margin-bottom: 4px; }}
    .topbar {{ display: flex; align-items: baseline; justify-content: space-between;
               margin-bottom: 4px; flex-wrap: wrap; gap: 8px; }}
    .resumo {{ margin-bottom: 20px; color: #374151; }}
    .usuario {{ font-size: 0.85em; color: #555; }}

    .mapa {{
      display: inline-block;
      background: #4b5563;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    }}
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
    .fileira {{ display: flex; gap: 3px; margin: 2px 0; }}
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
    .btn-logout {{
      margin-top: 16px;
      padding: 8px 18px;
      background: transparent;
      color: #4f46e5;
      border: 1px solid #4f46e5;
      border-radius: 8px;
      font-size: 0.9rem;
      cursor: pointer;
      transition: background 0.2s;
    }}
    .btn-logout:hover {{ background: #eef2ff; }}
    footer {{ margin-top: 20px; color: #9ca3af; font-size: 0.8em; }}
  </style>
</head>
<body>
  <div class="topbar">
    <h1>Estacionamento Campus</h1>
    <span class="usuario">Logado como <strong>{usuario}</strong></span>
  </div>
  <p class="resumo">
    <strong style="color:#16a34a">{livres} livres</strong> &nbsp;&middot;&nbsp;
    <strong style="color:#dc2626">{ocupadas} ocupadas</strong> &nbsp;&middot;&nbsp;
    {total} total
  </p>

  <div class="mapa">
    <div class="edificios">
      <div class="edificio">BLOCO A</div>
      <div class="edificio">BIBLIOTECA</div>
      <div class="edificio">BLOCO B</div>
    </div>
    <div class="rua">
      <span class="tag">ENTRADA &rarr;</span>
      <span class="tag">&larr; SAIDA</span>
    </div>
    <div class="fileira">{fileira_a}</div>
    <div class="corredor">
      <span class="corredor-nome">CORREDOR A &ndash; B</span>
    </div>
    <div class="fileira">{fileira_b}</div>
    <div class="corredor">
      <span class="corredor-nome">CORREDOR B &ndash; C</span>
    </div>
    <div class="fileira">{fileira_c}</div>
  </div>

  <div class="legenda">
    <div class="legenda-item"><div class="dot" style="background:#16a34a"></div> Livre</div>
    <div class="legenda-item"><div class="dot" style="background:#dc2626"></div> Ocupada</div>
  </div>

  <form method="POST" action="/logout">
    <button class="btn-logout" type="submit">Sair (logout)</button>
  </form>

  <footer>Atualizado a cada 5 s &nbsp;&middot;&nbsp; ENCO6A</footer>
</body>
</html>"""


def pagina_login(erro: str = "") -> bytes:
    erro_html = f'<p class="erro">{erro}</p>' if erro else ""
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Estacionamento Campus</title>
  <style>{ESTILO_LOGIN}</style>
</head>
<body>
  <div class="card">
    <h1>Estacionamento Campus</h1>
    <p class="subtitle">Faça login para continuar</p>
    {erro_html}
    <form method="POST" action="/login">
      <label for="usuario">Usuário</label>
      <input id="usuario" name="usuario" type="text" autofocus required>
      <label for="senha">Senha</label>
      <input id="senha" name="senha" type="password" required>
      <button class="btn" type="submit">Entrar</button>
    </form>
  </div>
</body>
</html>"""
    return html.encode()


def _fileira(snapshot, inicio, fim):
    return "".join(
        f'<div class="vaga {snapshot[vid]}">'
        f'<span class="num">{vid}</span>'
        f'<span class="status">{"livre" if snapshot[vid] == "livre" else "ocupada"}</span>'
        f'</div>'
        for vid in sorted(snapshot)[inicio:fim]
    )


def pagina_mapa(usuario: str, snapshot: dict) -> bytes:
    livres = sum(1 for s in snapshot.values() if s == "livre")
    return HTML_MAPA.format(
        usuario=usuario,
        livres=livres,
        ocupadas=len(snapshot) - livres,
        total=len(snapshot),
        fileira_a=_fileira(snapshot, 0, 10),
        fileira_b=_fileira(snapshot, 10, 20),
        fileira_c=_fileira(snapshot, 20, 30),
    ).encode()

# ---------------------------------------------------------------------------
# Servidor HTTP
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    def _usuario_autenticado(self) -> str | None:
        token = obter_token_do_cookie(self.headers.get("Cookie", ""))
        return validar_sessao(token)

    def _redirecionar(self, destino: str, set_cookie: str = "") -> None:
        self.send_response(303)
        self.send_header("Location", destino)
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()

    def _responder(self, corpo: bytes, status: int = 200,
                   content_type: str = "text/html; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        usuario = self._usuario_autenticado()

        if self.path == "/api/vagas":
            if not usuario:
                self._redirecionar("/")
                return
            with lock:
                snapshot = dict(vagas)
            self._responder(json.dumps(snapshot).encode(), content_type="application/json")
            return

        if usuario:
            with lock:
                snapshot = dict(vagas)
            self._responder(pagina_mapa(usuario, snapshot))
        else:
            self._responder(pagina_login())

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = self.rfile.read(tamanho).decode()
        dados = urllib.parse.parse_qs(corpo)

        if self.path == "/login":
            usuario = dados.get("usuario", [""])[0].strip()
            senha = dados.get("senha", [""])[0]
            hash_ok = USUARIOS.get(usuario) == hashlib.sha256(senha.encode()).hexdigest()
            if hash_ok:
                token = criar_sessao(usuario)
                cookie = f"sessao={token}; Path=/; HttpOnly; SameSite=Strict"
                self._redirecionar("/", set_cookie=cookie)
            else:
                self._responder(pagina_login("Usuário ou senha inválidos."), status=401)

        elif self.path == "/logout":
            token = obter_token_do_cookie(self.headers.get("Cookie", ""))
            remover_sessao(token)
            self._redirecionar("/", set_cookie="sessao=; Path=/; Max-Age=0")

    def log_message(self, *_):
        pass

# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    servidor = HTTPServer(("localhost", PORT), Handler)
    print(f"Servidor rodando em http://localhost:{PORT}")
    print("Usuários: aluno1 / senha123  |  aluno2 / abc456")
    print("Ctrl+C para encerrar.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
