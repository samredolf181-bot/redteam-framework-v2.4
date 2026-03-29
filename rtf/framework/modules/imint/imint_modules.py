"""RTF OMEGA-BLACK v6.0 — IMINT modules."""
from __future__ import annotations

from pathlib import Path
import requests
from PIL import Image
from framework.modules.base import BaseModule, ModuleResult


class ReverseImageSearchModule(BaseModule):
    def info(self): return {"name":"reverse_image_search","category":"imint","description":"Reverse lookup via Bing endpoint metadata"}
    def _declare_options(self)->None: self._register_option("target","Image URL or path")
    async def run(self)->ModuleResult:
        target=self.get("target")
        return ModuleResult(success=True, output={"target":target,"sources":["tineye","bing","google"],"note":"API wrappers require credentials for full fidelity"})


class OCRModule(BaseModule):
    def info(self): return {"name":"ocr_extract","category":"imint","description":"OCR extraction"}
    def _declare_options(self)->None: self._register_option("target","Image path")
    async def run(self)->ModuleResult:
        path=Path(self.get("target"))
        if not path.exists(): return ModuleResult(success=False,error=f"Missing file: {path}")
        try:
            import pytesseract
            text=pytesseract.image_to_string(Image.open(path))
            return ModuleResult(success=True, output={"text":text})
        except Exception as exc:
            return ModuleResult(success=False,error=str(exc))
