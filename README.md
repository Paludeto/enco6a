# enco6a — Estacionamento Campus

Sistema de monitoramento de vagas de estacionamento com autenticação.

## Como executar

```bash
python estacionamento.py
```

Acesse `http://localhost:8000`. Faça login para visualizar as vagas.

**Credenciais:** `aluno1 / senha123` · `aluno2 / abc456`

## Requisitos implementados

| # | Descrição |
|---|-----------|
| REQ-01 | Visualização em tempo real das vagas (livre/ocupada), atualizada a cada 5 segundos |
| REQ-04 | Login persistente via cookie de sessão, com logout |