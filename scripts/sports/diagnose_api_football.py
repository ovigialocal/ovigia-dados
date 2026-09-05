# /// script
# requires-python = ">=3.12"
# ///
"""Sonda descartável: descobre plano, cobertura e IDs reais na API-Football."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from ovigia_dados.sports.client import ApiFootballAuthError, ApiFootballClient

# A mesma assinatura é vendida por dois canais, com host e header próprios.
# A chave só vale no canal onde foi emitida, então o erro é idêntico ao de uma
# chave inválida quando ela é apresentada ao canal errado.
CHANNELS = {
    "direto (api-sports)": (
        "https://v3.football.api-sports.io/status",
        "x-apisports-key",
    ),
    "rapidapi": (
        "https://api-football-v1.p.rapidapi.com/v3/status",
        "x-rapidapi-key",
    ),
}

TEAM_NAMES = [
    "Porto Velho",
    "Ji-Parana",
    "Genus",
    "Guajara",
    "Real Ariquemes",
    "Uniao Cacoalense",
    "Vilhenense",
]


def show(label: str, payload: dict) -> None:
    print(f"\n=== {label}", flush=True)
    print(f"results={payload.get('results')} errors={payload.get('errors')}", flush=True)


def describe_key(key: str) -> str:
    """Descreve o formato da chave sem nunca revelar o valor.

    Chave direta da API-Sports e chave da RapidAPI têm comprimentos e
    alfabetos distintos, então o formato sozinho já indica a origem.
    """
    if not key:
        return "ausente"

    shape = "hexadecimal" if all(c in "0123456789abcdefABCDEF" for c in key) else "alfanumérica"
    return f"{len(key)} caracteres, {shape}"


def probe_channels(key: str) -> None:
    """Apresenta a mesma chave aos dois canais e relata qual a reconhece."""
    for label, (url, header) in CHANNELS.items():
        headers = {header: key, "Accept": "application/json"}
        if "rapidapi" in url:
            headers["x-rapidapi-host"] = "api-football-v1.p.rapidapi.com"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as http_error:
            # O corpo é o que distingue "chave recusada" de "endpoint errado".
            try:
                detail = http_error.read().decode("utf-8", errors="replace")[:300]
            except Exception:  # noqa: BLE001 - o código HTTP ainda informa
                detail = "(sem corpo)"
            print(
                f"{label}: HTTP {http_error.code} {http_error.reason} — {detail}",
                flush=True,
            )
            continue
        except Exception as failure:  # noqa: BLE001 - a sonda relata qualquer falha
            print(f"{label}: {failure}", flush=True)
            continue

        errors = payload.get("errors")
        if errors:
            print(f"{label}: recusada — {errors}", flush=True)
            continue

        account = payload.get("response", {})
        print(f"{label}: ACEITA — {json.dumps(account, ensure_ascii=False)}", flush=True)


def main() -> int:
    # A sonda faz nove requests e precisa caber na janela antes de qualquer kill,
    # então dispensa o throttle conservador do pipeline diário.
    client = ApiFootballClient(requests_per_minute=60)

    try:
        status = client.get("status")
    except ApiFootballAuthError as refusal:
        # Relatar a recusa é o resultado da sonda, não uma falha dela.
        print(f"=== chave recusada no canal do pipeline\n{refusal}", flush=True)
        raw_key = (os.environ.get("API_FOOTBALL_KEY") or "").strip()
        print(f"\n=== formato da chave recebida: {describe_key(raw_key)}", flush=True)
        if raw_key:
            print("\n=== qual canal reconhece esta chave", flush=True)
            probe_channels(raw_key)
        return 0

    print("=== status", flush=True)
    print(json.dumps(status.get("response", {}), ensure_ascii=False, indent=2), flush=True)

    leagues = client.get("leagues", {"search": "Rondoniense"})
    show("leagues search=Rondoniense", leagues)
    for item in leagues.get("response", []):
        league = item.get("league", {})
        seasons = [s.get("year") for s in item.get("seasons", []) or []]
        print(
            f"league_id={league.get('id')} name={league.get('name')} seasons={seasons}",
            flush=True,
        )

    for name in TEAM_NAMES:
        payload = client.get("teams", {"search": name})
        show(f"teams search={name}", payload)
        for item in payload.get("response", []):
            team = item.get("team", {})
            venue = item.get("venue", {})
            print(
                f"team_id={team.get('id')} name={team.get('name')} "
                f"country={team.get('country')} city={venue.get('city')}",
                flush=True,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
