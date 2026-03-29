"""RTF OMEGA-BLACK v6.0 — SIGINT-OSINT modules."""
from __future__ import annotations

import requests
from framework.modules.base import BaseModule, ModuleResult


class ADSBFlightTrackingModule(BaseModule):
    def info(self): return {"name":"adsb_flight_tracking","category":"sigint_osint","description":"OpenSky flight lookup"}
    def _declare_options(self): self._register_option("target","Callsign or ICAO24")
    async def run(self)->ModuleResult:
        target=self.get("target")
        try:
            data=requests.get("https://opensky-network.org/api/states/all",timeout=20).json()
            states=[s for s in (data.get("states") or []) if target.lower() in str(s).lower()][:10]
            return ModuleResult(success=True, output={"matches":states})
        except Exception as exc:
            return ModuleResult(success=False,error=str(exc))


class WeatherPatternModule(BaseModule):
    def info(self): return {"name":"weather_pattern","category":"sigint_osint","description":"Historical weather correlation"}
    def _declare_options(self):
        self._register_option("target","lat,lon")
        self._register_option("date","YYYY-MM-DD")
    async def run(self)->ModuleResult:
        lat,lon=[x.strip() for x in self.get("target").split(",",1)]
        date=self.get("date")
        try:
            r=requests.get("https://archive-api.open-meteo.com/v1/archive",params={"latitude":lat,"longitude":lon,"start_date":date,"end_date":date,"hourly":"temperature_2m,precipitation"},timeout=20)
            return ModuleResult(success=True, output=r.json())
        except Exception as exc:
            return ModuleResult(success=False,error=str(exc))
