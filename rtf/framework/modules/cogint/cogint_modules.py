"""RTF OMEGA-BLACK v6.0 — COGINT modules."""
from __future__ import annotations

from collections import Counter
import math
from framework.modules.base import BaseModule, ModuleResult


class PersonalityProfileModule(BaseModule):
    def info(self): return {"name":"personality_profile","category":"cogint","description":"Rule-based OCEAN scoring"}
    def _declare_options(self): self._register_option("target","Text sample")
    async def run(self)->ModuleResult:
        text=(self.get("target") or "").lower()
        words=text.split(); c=Counter(words); total=max(1,len(words))
        scores={
            "openness":min(1.0,(c['imagine']+c['curious']+c['creative'])/total*40),
            "conscientiousness":min(1.0,(c['plan']+c['organized']+c['deadline'])/total*40),
            "extraversion":min(1.0,(c['party']+c['friends']+c['talk'])/total*40),
            "agreeableness":min(1.0,(c['thanks']+c['help']+c['sorry'])/total*40),
            "neuroticism":min(1.0,(c['stress']+c['anxious']+c['worried'])/total*40),
        }
        return ModuleResult(success=True, output={"scores":scores,"confidence":round(min(0.95,math.log(total+1)/6),3)})


class DeceptionIndicatorsModule(BaseModule):
    def info(self): return {"name":"deception_indicators","category":"cogint","description":"Linguistic deception heuristics"}
    def _declare_options(self): self._register_option("target","Text sample")
    async def run(self)->ModuleResult:
        text=(self.get("target") or "").lower().split()
        if not text: return ModuleResult(success=False,error="No text provided")
        first_person=sum(1 for w in text if w in {"i","me","my","mine"})
        neg=sum(1 for w in text if w in {"not","never","no","none"})
        exclusive=sum(1 for w in text if w in {"but","except","without"})
        score=min(1.0, (neg+exclusive+max(0,2-first_person))*0.08)
        return ModuleResult(success=True, output={"deception_likelihood":round(score,3),"signals":{"first_person":first_person,"negative_terms":neg,"exclusive_terms":exclusive}})
