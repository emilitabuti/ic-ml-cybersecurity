"""Envia eventos simulados de SYN flood para o historico do dashboard.

Uso esperado:
1. Iniciar a API FastAPI em http://127.0.0.1:8000.
2. Iniciar o dashboard.
3. Executar este script para publicar os alertas simulados.

O script nao executa ataque real. Ele apenas envia eventos HTTP para o endpoint
de demonstracao da API.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_API_URL = "http://127.0.0.1:8000"
MODEL_NAME = "syn-flood-dashboard-demo-v1"

EVENT_SEQUENCE = [
    {"prediction": "Normal Traffic", "confidence": 0.42},
    {"prediction": "SYN Flood - Low Intensity", "confidence": 0.77},
    {"prediction": "SYN Flood - Medium Intensity", "confidence": 0.86},
    {"prediction": "SYN Flood - High Intensity", "confidence": 0.95},
    {"prediction": "SYN Flood - High Intensity", "confidence": 0.97},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publica uma sequencia simples de alertas SYN flood no dashboard."
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"URL base da API. Padrao: {DEFAULT_API_URL}",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Intervalo em segundos entre os eventos. Use 0 para enviar tudo de uma vez.",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Nao limpa os eventos de demo antes de publicar a sequencia.",
    )
    return parser.parse_args()


def request_json(method: str, url: str, body: dict[str, object] | None = None) -> object:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=10) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload) if payload else None


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def build_event(template: dict[str, object]) -> dict[str, object]:
    return {
        "prediction": template["prediction"],
        "confidence": template["confidence"],
        "model": MODEL_NAME,
        "timestamp": utc_timestamp(),
    }


def main() -> int:
    args = parse_args()
    api_url = args.api_url.rstrip("/")
    demo_url = f"{api_url}/history/demo"

    try:
        if not args.no_clear:
            request_json("DELETE", demo_url)
            print("Historico de demo limpo.")

        for index, template in enumerate(EVENT_SEQUENCE, start=1):
            event = build_event(template)
            request_json("POST", demo_url, event)
            confidence = int(float(event["confidence"]) * 100)
            print(f"{index}/{len(EVENT_SEQUENCE)} enviado: {event['prediction']} ({confidence}%)")
            if args.delay > 0 and index < len(EVENT_SEQUENCE):
                time.sleep(args.delay)
    except HTTPError as exc:
        print(f"Erro HTTP {exc.code} ao chamar {exc.url}: {exc.reason}")
        return 1
    except URLError as exc:
        print(f"Nao foi possivel conectar na API em {api_url}: {exc.reason}")
        return 1

    print("Eventos enviados. O dashboard deve exibir os alertas via GET /history.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
