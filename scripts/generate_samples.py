from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.controller import AutoMindController
from core.config import ConfigManager
from database.repository import DatabaseRepository
from simulator.scenarios import SCENARIOS


def main() -> int:
    root = ROOT
    samples = root / "samples"
    sessions_dir = samples / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="automind-samples-") as td:
        work = Path(td)
        config = ConfigManager(work / "settings.json")
        config.set("general", "first_run_complete", True)
        db = DatabaseRepository(work / "automind.db")
        controller = AutoMindController(config=config, db=db)

        for key in SCENARIOS:
            session = controller.start_simulation(key)
            path = sessions_dir / f"{key}.json"
            path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")

            if key == "misfire":
                controller.save_notes("Demo note: rough idle reported during the simulated inspection.")
                controller.generate_report(samples / "AutoMindAI-Sample-Report.pdf")

            controller.disconnect()

    print(f"Generated {len(SCENARIOS)} sample sessions and sample PDF in {samples}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
