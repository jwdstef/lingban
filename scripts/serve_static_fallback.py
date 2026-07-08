"""Serve a static directory with index.html fallback for client-side routing."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


class FallbackHandler(SimpleHTTPRequestHandler):
    def send_head(self):  # noqa: N802 - stdlib method name
        parsed = urlparse(self.path)
        requested = Path(unquote(parsed.path.lstrip("/")))
        candidate = Path(self.directory, requested)

        if not candidate.exists() and not candidate.is_file():
            self.path = "/index.html"

        return super().send_head()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="Directory to serve.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5200)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    directory = str(Path(args.directory).resolve())
    handler = partial(FallbackHandler, directory=directory)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving {directory} at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
