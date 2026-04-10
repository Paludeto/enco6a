"""
ENCO6A - Aplicativo de Estacionamento no Campus
REQ-04: Interface web com login persistente

Servidor embutido na stdlib (http.server). Sem dependências externas.
Acesse: http://localhost:8000

Sessão persistida via cookie + session.json no servidor.
"""

import hashlib
import json
import os
import secrets
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

SESSION_FILE = "session.json"
PORT = 8000

USUARIOS = {
    "aluno1": hashlib.sha256("senha123".encode()).hexdigest(),
    "aluno2": hashlib.sha256("abc456".encode()).hexdigest(),
}


# ---------------------------------------------------------------------------
# Persistência de sessão
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
    """Retorna o usuário se o token for válido, senão None."""
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

ESTILO = """
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
  .btn-outline {
    background: transparent; color: #4f46e5;
    border: 1px solid #4f46e5; margin-top: 10px;
  }
  .btn-outline:hover { background: #eef2ff; }
  .erro { color: #dc2626; font-size: 0.85rem; margin-bottom: 14px; }
  .bem-vindo { font-size: 0.95rem; color: #555; margin-bottom: 20px; }
  .placeholder {
    background: #f8f9fa; border: 1px dashed #ccc;
    border-radius: 8px; padding: 20px;
    text-align: center; color: #aaa;
    font-size: 0.85rem; margin-bottom: 20px;
  }
"""


def pagina_login(erro: str = "") -> bytes:
    erro_html = f'<p class="erro">{erro}</p>' if erro else ""
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Estacionamento Campus</title>
  <style>{ESTILO}</style>
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


def pagina_principal(usuario: str) -> bytes:
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Estacionamento Campus</title>
  <style>{ESTILO}</style>
</head>
<body>
  <div class="card">
    <h1>Estacionamento Campus</h1>
    <p class="bem-vindo">Bem-vindo, <strong>{usuario}</strong>!</p>
    <div class="placeholder">
      Vagas disponíveis em tempo real<br>
      <small>[conteúdo do REQ-01 a REQ-03 aqui]</small>
    </div>
    <form method="POST" action="/logout">
      <button class="btn btn-outline" type="submit">Sair (logout)</button>
    </form>
  </div>
</body>
</html>"""
    return html.encode()


# ---------------------------------------------------------------------------
# Servidor HTTP
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    def _usuario_autenticado(self) -> str | None:
        cookie = self.headers.get("Cookie", "")
        token = obter_token_do_cookie(cookie)
        return validar_sessao(token)

    def _redirecionar(self, destino: str) -> None:
        self.send_response(303)
        self.send_header("Location", destino)
        self.end_headers()

    def _responder(self, corpo: bytes, status: int = 200,
                   headers_extras: list[tuple] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        for chave, valor in (headers_extras or []):
            self.send_header(chave, valor)
        self.end_headers()
        self.wfile.write(corpo)

    # GET /
    def do_GET(self):
        usuario = self._usuario_autenticado()
        if self.path == "/logout":
            self._redirecionar("/")
            return
        if usuario:
            self._responder(pagina_principal(usuario))
        else:
            self._responder(pagina_login())

    # POST /login  e  POST /logout
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
                self._redirecionar("/")
                # Precisamos enviar o cookie junto com o redirect
                self.send_response(303)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", cookie)
                self.end_headers()
            else:
                self._responder(pagina_login("Usuário ou senha inválidos."), status=401)

        elif self.path == "/logout":
            cookie_header = self.headers.get("Cookie", "")
            token = obter_token_do_cookie(cookie_header)
            remover_sessao(token)
            # Expira o cookie no navegador
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "sessao=; Path=/; Max-Age=0")
            self.end_headers()

    def log_message(self, *_):
        # Silencia o log padrão do servidor para manter o terminal limpo
        pass


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    servidor = HTTPServer(("localhost", PORT), Handler)
    print(f"Servidor rodando em http://localhost:{PORT}")
    print("Ctrl+C para encerrar.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
