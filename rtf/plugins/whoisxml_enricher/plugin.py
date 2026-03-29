from __future__ import annotations
from typing import Dict, Any

def run(target: str, **kwargs: Any) -> Dict[str, Any]:
    return {"target": target, "provider": __name__.split('.')[-2], "status": "ok", "kwargs": kwargs}
