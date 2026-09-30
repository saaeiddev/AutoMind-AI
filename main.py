from __future__ import annotations

import argparse
import ctypes
import logging
import os
import sys
import tempfile
from pathlib import Path

from app.version import VERSION
from logging_ext.setup import configure_logging


def _enable_windows_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def self_test() -> int:
    """Packaged-runtime smoke test used by CI and installer QA."""
    from core.config import ConfigManager
    from database.repository import DatabaseRepository
    from app.controller import AutoMindController

    with tempfile.TemporaryDirectory(prefix="automind-selftest-") as td:
        root = Path(td)
        config = ConfigManager(root / "settings.json")
        db = DatabaseRepository(root / "automind.db")
        controller = AutoMindController(config=config, db=db)
        session = controller.start_simulation("lean")
        assert session.connection_mode == "simulation"
        assert any(d.code == "P0171" for d in session.dtcs)
        assert session.live_data.get("010C") is not None
        report = controller.generate_report(root / "smoke-report.pdf")
        assert report.exists() and report.stat().st_size > 1000
        assert db.get_session(session.id) is not None
        controller.disconnect()
    if sys.stdout is not None:
        print(f"AutoMind AI {VERSION} self-test: PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="AutoMindAI")
    parser.add_argument("--self-test", action="store_true", help="Run packaged runtime smoke tests and exit")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    args = parser.parse_args(argv)

    if args.version:
        print(VERSION)
        return 0
    if args.self_test:
        return self_test()

    configure_logging()
    log = logging.getLogger("automind")
    _enable_windows_dpi_awareness()
    try:
        from app.controller import AutoMindController
        from ui.app import AutoMindApplication
        controller = AutoMindController()
        app = AutoMindApplication(controller)
        log.info("Application startup complete")
        app.mainloop()
        return 0
    except Exception:
        log.exception("Fatal startup error")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
