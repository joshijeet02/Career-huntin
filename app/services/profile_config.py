import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "candidate_intelligence_v1.json"


@lru_cache(maxsize=1)
def load_profile_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def get_source_weights() -> dict[str, float]:
    cfg = load_profile_config()
    priorities = (
        cfg.get("execution_preferences", {}).get("job_source_priority", [])
        if isinstance(cfg, dict)
        else []
    )
    mapped = {
        "company_site": "Company career pages (direct)",
        "wellfound": "Wellfound",
        "yc_jobs": "Y Combinator Work at a Startup",
        "builtin": "Built In",
        "venture_capital_careers": "Venture Capital Careers",
        "devex": "Devex",
        "impactpool": "Impactpool",
        "world_bank": "World Bank careers",
        "imf": "IMF recruitment",
        "un": "UN Careers Portal",
        "adb": "ADB Consultant Management System",
        "linkedin": "LinkedIn",
        "job_board": "Built In",
    }
    # Higher priority sources receive a larger additive bonus.
    bonuses: dict[str, float] = {}
    total = max(len(priorities), 1)
    for key, label in mapped.items():
        if label in priorities:
            rank = priorities.index(label)
            bonuses[key] = round(((total - rank) / total) * 20.0, 2)
        else:
            bonuses[key] = 3.0
    return bonuses


def get_execution_preferences() -> dict[str, Any]:
    cfg = load_profile_config()
    return cfg.get("execution_preferences", {}) if isinstance(cfg, dict) else {}

