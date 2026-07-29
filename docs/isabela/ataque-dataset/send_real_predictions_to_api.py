"""Envia janelas sinteticas para o endpoint real POST /predict.

Este script existe para alimentar o dashboard sem mock: ele le os eventos do
cenario SYN flood, monta janelas numericas no schema do modelo carregado pela
API e chama `POST /predict`. Cada resposta real passa a aparecer em `GET /history`.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_EVENTS_FILE = SCRIPT_DIR / "results" / "dashboard_history_events.json"
DEFAULT_API_URL = "http://127.0.0.1:8000"

# Assinatura compacta derivada de uma janela UNSW que o artefato RF atual
# reconhece como ataque. O script ainda usa somente POST /predict real.
ATTACK_FEATURE_TEMPLATE = {
    "sport": 23357.0,
    "dsport": 80.0,
    "dur": 0.6921604882400858,
    "sbytes": -0.27913849646862504,
    "dbytes": 0.4902893473607708,
    "sttl": 31.0,
    "dttl": 254.0,
    "sloss": -0.2857142857142857,
    "dloss": 0.3333333333333333,
    "Sload": -1.17510058087282,
    "Dload": 0.04959044433092215,
    "Spkts": -0.08695652173913043,
    "Dpkts": 0.14285714285714285,
    "stcpb": 0.014064952612622406,
    "dtcpb": 0.019966255078546786,
    "smeansz": 0.06060606060606061,
    "dmeansz": 1.9545454545454546,
    "trans_depth": 1.0,
    "res_bdy_len": 9.394909401310617,
    "Sjit": 0.5466210800854902,
    "Djit": 14.077697718423678,
    "Stime": -0.015487268416648664,
    "Ltime": -0.015487261637967667,
    "Sintpkt": 1.9100044581417834,
    "Dintpkt": 0.9202447792102867,
    "tcprtt": 500.0,
    "synack": 10.606701940035274,
    "ackdat": 306.9726027397261,
    "ct_state_ttl": 1.0,
    "ct_flw_http_mthd": 1.0,
    "ct_srv_src": -0.16666666666666666,
    "ct_srv_dst": -0.4,
    "ct_dst_ltm": -0.3333333333333333,
    "ct_src_ltm": -0.6666666666666666,
    "proto_tcp": 1.0,
    "state_FIN": 1.0,
    "service_http": 1.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Alimenta a API real com janelas sinteticas do cenario SYN flood."
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--events-file", type=Path, default=DEFAULT_EVENTS_FILE)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.5)
    return parser.parse_args()


def get_json(url: str) -> Any:
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any]) -> Any:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def load_events(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Arquivo de eventos deve conter uma lista JSON.")
    return [item for item in data if isinstance(item, dict)]


def build_window(
    feature_names: list[str],
    *,
    window_size: int,
    event: dict[str, Any],
) -> list[dict[str, float]]:
    prediction = str(event.get("prediction", "")).lower()
    confidence = float(event.get("confidence", 0.5))
    is_attack = "syn flood" in prediction
    intensity = 1.0
    if "medium" in prediction:
        intensity = 1.5
    elif "high" in prediction:
        intensity = 2.0

    rows: list[dict[str, float]] = []
    for index in range(window_size):
        progress = (index + 1) / window_size
        row = {name: 0.0 for name in feature_names}
        if is_attack and all(name in row for name in ATTACK_FEATURE_TEMPLATE):
            row.update(ATTACK_FEATURE_TEMPLATE)
            row["sport"] = ATTACK_FEATURE_TEMPLATE["sport"] + index
            rows.append(row)
            continue

        _set_if_present(row, "proto_tcp", 1.0)
        _set_if_present(row, "state_REQ", 1.0 if is_attack else 0.0)
        _set_if_present(row, "state_CON", 0.0 if is_attack else 1.0)
        _set_if_present(row, "service_http", 1.0)
        _set_if_present(row, "sport", 49152.0 + index)
        _set_if_present(row, "dsport", 80.0)
        _set_if_present(row, "dur", max(0.001, 0.04 / intensity if is_attack else 1.2))
        _set_if_present(row, "sbytes", (1200.0 * intensity if is_attack else 320.0) * progress)
        _set_if_present(row, "dbytes", (24.0 if is_attack else 460.0) * progress)
        _set_if_present(row, "Spkts", (180.0 * intensity if is_attack else 18.0) * progress)
        _set_if_present(row, "Dpkts", (3.0 if is_attack else 20.0) * progress)
        _set_if_present(row, "Sload", (900000.0 * intensity if is_attack else 1200.0) * progress)
        _set_if_present(row, "Dload", (35.0 if is_attack else 1400.0) * progress)
        _set_if_present(row, "sttl", 254.0 if is_attack else 31.0)
        _set_if_present(row, "dttl", 0.0 if is_attack else 29.0)
        _set_if_present(row, "smeansz", 64.0 if is_attack else 96.0)
        _set_if_present(row, "dmeansz", 8.0 if is_attack else 110.0)
        _set_if_present(row, "ct_srv_src", (40.0 * intensity if is_attack else 2.0))
        _set_if_present(row, "ct_srv_dst", (40.0 * intensity if is_attack else 2.0))
        _set_if_present(row, "ct_dst_src_ltm", (35.0 * intensity if is_attack else 2.0))
        _set_if_present(row, "ct_src_dport_ltm", (35.0 * intensity if is_attack else 1.0))
        _set_if_present(row, "ct_state_ttl", 6.0 if is_attack else 1.0)
        _set_if_present(row, "Sintpkt", 0.2 if is_attack else 80.0)
        _set_if_present(row, "Dintpkt", 0.0 if is_attack else 60.0)
        _set_if_present(row, "tcprtt", 0.0 if is_attack else 0.02)
        _set_if_present(row, "synack", 0.0 if is_attack else 0.01)
        _set_if_present(row, "ackdat", 0.0 if is_attack else 0.01)
        # A confianca do cenario sintetico so modula a intensidade da janela.
        _set_if_present(row, "sloss", max(0.0, confidence * 8.0 if is_attack else 0.0))
        _set_if_present(row, "dloss", 0.0 if is_attack else 1.0)
        rows.append(row)
    return rows


def _set_if_present(row: dict[str, float], name: str, value: float) -> None:
    if name in row:
        row[name] = float(value)


def main() -> int:
    args = parse_args()
    api_url = args.api_url.rstrip("/")
    events = load_events(args.events_file.resolve())
    model_info = get_json(f"{api_url}/model/info")
    feature_names = list(model_info["features"])
    window_size = int(model_info["window_size"])

    sent = 0
    for event in events[: args.limit]:
        payload = {
            "features": build_window(
                feature_names,
                window_size=window_size,
                event=event,
            )
        }
        try:
            response = post_json(f"{api_url}/predict", payload)
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Falha ao enviar janela para {api_url}/predict") from exc
        sent += 1
        print(
            f"{sent:03d} {event.get('prediction')} -> "
            f"{response['prediction']} ({response['confidence']:.2%})"
        )
        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"Predicoes reais registradas em {api_url}/history: {sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
