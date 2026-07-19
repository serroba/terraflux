"""Headless smoke test for the published docs/ pages.

Serves the committed docs/ folder and loads each page in a real (headless) browser,
asserting it renders the expected flux numbers with no uncaught JS errors. This
exercises the parts CI otherwise never touches: DuckDB-WASM, the d3 map, and the
WebGL globe.

Named ``smoke_*`` so it is excluded from the fast unit-test run (``test_*``); it needs
a browser and network (CDN) and is run as its own CI step:

    uv run playwright install --with-deps chromium
    uv run python -m unittest discover -p "smoke_*.py"
"""

import functools
import threading
import unittest
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs"
PAGE_TIMEOUT_MS = 60_000


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # silence access logs
        pass


class SiteSmokeTest(unittest.TestCase):
    httpd: HTTPServer
    port: int

    @classmethod
    def setUpClass(cls) -> None:
        handler = functools.partial(_QuietHandler, directory=str(DOCS_DIR))
        cls.httpd = HTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._browser.close()
        cls._pw.stop()
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _load(self, path: str, needle: str) -> str:
        """Load a page, wait for `needle` to appear, and assert no JS errors."""
        page = self._browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.goto(f"http://127.0.0.1:{self.port}/{path}", wait_until="load")
            page.wait_for_function(
                "text => document.body.innerText.includes(text)",
                arg=needle,
                timeout=PAGE_TIMEOUT_MS,
            )
            body = page.inner_text("body")
        finally:
            page.close()
        self.assertEqual(errors, [], msg=f"{path} raised JS errors: {errors}")
        return body

    def test_table_renders_the_aggregate(self) -> None:
        body = self._load("table.html", "45,212,000")
        self.assertIn("32,214,000", body)

    def test_flat_map_renders(self) -> None:
        body = self._load("flat.html", "77.4 PJ")
        self.assertIn("strait of hormuz", body)
        self.assertIn("strait of malacca", body)

    def test_globe_renders(self) -> None:
        # Reaching the final status means globe.gl (WebGL) initialised without error.
        self._load("index.html", "77.4 PJ")


if __name__ == "__main__":
    unittest.main()
