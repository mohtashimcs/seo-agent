#!/usr/bin/env python3
"""
run_dashboard.py — Rebuilds the dashboard from the latest reports and serves
it on localhost, opening it in the browser.

Usage:
    python scripts/run_dashboard.py            # rebuild from existing reports, serve
    python scripts/run_dashboard.py --full     # run all four weekly scripts first
    python scripts/run_dashboard.py --port 9000 --no-open
"""

import argparse
import functools
import http.server
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"

WEEKLY_SCRIPTS = ["gap_finder.py", "competitor_intel.py", "content_plan.py"]


def run_script(name):
    print(f"▶️  {name}")
    result = subprocess.run([sys.executable, "-W", "ignore", str(ROOT / "scripts" / name)], cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f"❌ {name} failed (exit {result.returncode}). Fix it and re-run.")


def latest_dashboard():
    dashboards = sorted(REPORTS.glob("dashboard-*.html"), reverse=True)
    return dashboards[0].name if dashboards else None


def make_handler(dashboard_name):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self.send_response(302)
                self.send_header("Location", f"/{dashboard_name}")
                self.end_headers()
                return
            super().do_GET()

        def log_message(self, *args):
            pass

    return functools.partial(Handler, directory=str(REPORTS))


def main():
    parser = argparse.ArgumentParser(description="Serve the SEO dashboard in the browser.")
    parser.add_argument("--full", action="store_true", help="run gap finder, competitor intel and content plan first")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true", help="don't open the browser automatically")
    args = parser.parse_args()

    if args.full:
        for name in WEEKLY_SCRIPTS:
            run_script(name)
    run_script("build_dashboard.py")

    dashboard = latest_dashboard()
    if not dashboard:
        sys.exit("❌ No dashboard found in reports/. Run the weekly scripts first.")

    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(dashboard))
    except OSError as e:
        sys.exit(f"❌ Could not bind port {args.port}: {e}. Try --port <other>.")

    url = f"http://127.0.0.1:{args.port}/"
    print(f"\n🌐 Serving {dashboard} at {url}  (Ctrl+C to stop)")
    if not args.no_open:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
