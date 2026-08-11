#!/usr/bin/env python3
"""Gera o data.json com a classificacao jornada a jornada.

Correr a partir da pasta external/:

    python3 atualizar.py            # liga 1406
    python3 atualizar.py 1406       # liga a escolha

Porque e que este ficheiro existe: a API da Liga Portugal nao envia cabecalhos
CORS, por isso o browser bloqueia pedidos feitos diretamente de um dominio
Vercel. A app resolve isso de duas maneiras -- le este data.json (mesma origem,
sempre funciona) e, se estiver publicada no Vercel, pode pedir dados frescos a
funcao serverless em api/standings.js. Este script cobre o primeiro caso: os
dados ficam embutidos no deploy, portanto a tabela nunca aparece vazia.

Um pedido por equipa, porque a classificacao so traz o total acumulado; os
pontos de cada jornada vem do historico individual de cada equipa.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://fantasy.ligaportugal.pt/api"
CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
LIGA_POR_OMISSAO = 1406


def obter(url: str) -> dict:
    pedido = urllib.request.Request(url, headers=CABECALHOS)
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def recolher(id_liga: int) -> dict:
    """Junta a classificacao da liga com o historico de cada equipa."""
    equipas: list[dict] = []
    liga: dict = {}
    pagina = 1
    while True:
        dados = obter(f"{BASE}/leagues-classic/{id_liga}/standings/?page_standings={pagina}")
        liga = liga or dados.get("league", {})
        bloco = dados.get("standings", {})
        equipas.extend(bloco.get("results", []))
        if not bloco.get("has_next"):
            break
        pagina += 1

    # Quantas jornadas tem a epoca, e quais ja terminaram. Serve para a tabela
    # desenhar as colunas todas (J1..J34) mesmo antes de serem jogadas.
    bootstrap = obter(f"{BASE}/bootstrap-static/")
    eventos = bootstrap.get("events", [])
    total_jornadas = len(eventos)
    jornadas_terminadas = [e["id"] for e in eventos if e.get("finished")]

    linhas = []
    for i, equipa in enumerate(equipas, 1):
        historico = obter(f"{BASE}/entry/{equipa['entry']}/history/")
        por_jornada = {
            g["event"]: {"pontos": g.get("points", 0), "total": g.get("total_points", 0)}
            for g in historico.get("current", [])
        }
        linhas.append(
            {
                "id_equipa": equipa["entry"],
                "equipa": equipa["entry_name"],
                "jogador": equipa["player_name"],
                "posicao": equipa["rank"],
                "total": equipa["total"],
                "jornadas": por_jornada,
            }
        )
        print(f"  [{i}/{len(equipas)}] {equipa['entry_name']}", flush=True)
        time.sleep(0.15)  # nao martelar o servidor da Liga

    return {
        "id_liga": liga.get("id", id_liga),
        "nome_liga": liga.get("name", ""),
        "atualizado_em": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_jornadas": total_jornadas,
        "jornadas_terminadas": jornadas_terminadas,
        "equipas": linhas,
    }


def main() -> int:
    id_liga = int(sys.argv[1]) if len(sys.argv) > 1 else LIGA_POR_OMISSAO
    print(f"A recolher a liga {id_liga}...")
    dados = recolher(id_liga)
    destino = Path(__file__).resolve().parent / "data.json"
    destino.write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"\nEscrito {destino.name}: {len(dados['equipas'])} equipas, "
        f"{len(dados['jornadas_terminadas'])} jornada(s) jogada(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
