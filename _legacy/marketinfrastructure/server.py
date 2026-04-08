from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .html_views import render_dashboard, render_detail
from .service import MarketInfrastructureService


def run_server(*, service: MarketInfrastructureService, host: str, port: int) -> None:
    handler = build_handler(service)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"MarketInfrastructure running at http://{host}:{port}")
    server.serve_forever()


def build_handler(service: MarketInfrastructureService):
    project_root = service.project_root

    class MarketInfrastructureHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._handle_dashboard(parsed.query)
                return
            if parsed.path.startswith("/symbol/"):
                symbol = parsed.path.split("/symbol/", 1)[1].strip().upper()
                self._handle_detail(symbol=symbol, query=parsed.query)
                return
            if parsed.path == "/api/candidates":
                self._handle_candidates_api(parsed.query)
                return
            if parsed.path == "/api/golden-hour-contract":
                self._send_json(
                    HTTPStatus.GONE,
                    {
                        "error": "Premarket-only mode is active. Intraday timing is handled by a separate system.",
                    },
                )
                return
            if parsed.path.startswith("/static/"):
                self._handle_static(parsed.path, project_root)
                return
            self._send_error_page(HTTPStatus.NOT_FOUND, "Page not found.")

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/golden-hour":
                self._send_json(
                    HTTPStatus.GONE,
                    {
                        "error": "Premarket-only mode is active here. Send intraday timing data to the separate phase-two system instead.",
                    },
                )
                return
            self._send_error_page(HTTPStatus.NOT_FOUND, "Endpoint not found.")

        def _handle_dashboard(self, query: str) -> None:
            params = normalize_query(query)
            candidates = service.list_candidates(
                search=params.get("search", ""),
                category=params.get("category", ""),
                action=params.get("action", ""),
                risk_bucket=params.get("risk_bucket", ""),
                status=params.get("status", ""),
                sort_by=params.get("sort", ""),
                sort_dir=params.get("direction", ""),
                limit=parse_limit(params.get("limit", "100")),
            )
            html_body = render_dashboard(
                candidates=candidates,
                filters=service.available_filters(),
                query=params,
            )
            self._send_html(HTTPStatus.OK, html_body)

        def _handle_detail(self, *, symbol: str, query: str) -> None:
            params = normalize_query(query)
            trade_date = params.get("trade_date", "")
            candidate = service.get_candidate(symbol=symbol, trade_date=trade_date)
            if candidate is None:
                self._send_error_page(
                    HTTPStatus.NOT_FOUND,
                    f"No candidate found for {symbol} on {trade_date or 'the requested date'}.",
                )
                return
            self._send_html(HTTPStatus.OK, render_detail(candidate))

        def _handle_candidates_api(self, query: str) -> None:
            params = normalize_query(query)
            candidates = service.list_candidates(
                search=params.get("search", ""),
                category=params.get("category", ""),
                action=params.get("action", ""),
                risk_bucket=params.get("risk_bucket", ""),
                status=params.get("status", ""),
                sort_by=params.get("sort", ""),
                sort_dir=params.get("direction", ""),
                limit=parse_limit(params.get("limit", "100")),
            )
            self._send_json(
                HTTPStatus.OK,
                {
                    "count": len(candidates),
                    "candidates": [candidate.to_dict() for candidate in candidates],
                },
            )

        def _handle_static(self, path: str, project_root: Path) -> None:
            static_path = project_root / "marketinfrastructure" / path.lstrip("/")
            if not static_path.exists() or not static_path.is_file():
                self._send_error_page(HTTPStatus.NOT_FOUND, "Static asset not found.")
                return
            content = static_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _send_html(self, status: HTTPStatus, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_json(self, status: HTTPStatus, payload: dict) -> None:
            encoded = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_error_page(self, status: HTTPStatus, message: str) -> None:
            body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{status.value} {status.phrase}</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <main class="page-shell narrow">
    <h1>{status.value} {status.phrase}</h1>
    <p>{message}</p>
    <p><a href="/">Return to dashboard</a></p>
  </main>
</body>
</html>"""
            self._send_html(status, body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return MarketInfrastructureHandler


def normalize_query(query: str) -> dict[str, str]:
    return {key: values[-1] for key, values in parse_qs(query).items()}


def parse_limit(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return 100
    return min(max(parsed, 1), 500)
