# Multiple date formats supported for robustness (different CSV / API may use different styles)
"""
Robust data_fetch.py
1) Try Hong Kong Observatory (HKO) Open Data CSVs (CLMTEMP + CLMRN).
2) If parsing yields no rows, fallback to Open-Meteo for the same year-month.

Exports:
- class WeatherDay
- function fetch_hk_data(year:int, month:int) -> list[WeatherDay]
"""

from __future__ import annotations
import csv, io
from datetime import datetime, timedelta
from typing import List, Optional
import requests

# ---- HKO endpoints ----
HKO_TEMP_URL = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&rformat=csv&station=HKO"
HKO_RAIN_URL = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMRN&rformat=csv&station=HKO"
REQUEST_TIMEOUT = 20

# Classification thresholds (mm)
RAINY_THRESHOLD = 0.5      # > 0.5 mm -> rainy
CLOUDY_THRESHOLD = 0.0     # 0 < mm <= 0.5 -> cloudy ; 0 -> sunny


class WeatherDay:
    def __init__(self, date: datetime, temp_mean_c: float, weather_type: str):
        self.date = date
        self.temperature = float(temp_mean_c)
        self.weather_type = weather_type
        self.day = date.day


def _read_csv_from_url(url: str) -> list[dict]:
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    text = r.content.decode("utf-8", errors="ignore")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    
    header_idx = 0
    for i, ln in enumerate(lines[:20]):
        low = ln.lower()
        if "date" in low or "data" in low:
            header_idx = i
            break
    effective = "\n".join(lines[header_idx:])
    return list(csv.DictReader(io.StringIO(effective)))


_DATE_FORMATS = ("%Y-%m-%d","%Y/%m/%d","%d/%m/%Y","%m/%d/%Y","%Y-%m-%dT%H:%M:%S")

def _parse_date_any(row: dict) -> Optional[datetime]:
    for k, v in row.items():
        if not k:
            continue
        kl = k.lower()
        if "date" in kl or "data" in kl or "day" in kl:
            s = str(v).strip()
            try:
                return datetime.fromisoformat(s)
            except Exception:
                for fmt in _DATE_FORMATS:
                    try:
                        return datetime.strptime(s, fmt)
                    except Exception:
                        continue
    return None

def _get_float_any(row: dict, *subs: str) -> Optional[float]:
    for k, v in row.items():
        if not k:
            continue
        kl = k.lower()
        if any(sub in kl for sub in subs):
            try:
                return float(str(v).strip())
            except Exception:
                continue
    return None


# ---------- Open-Meteo fallback ----------
def _fallback_open_meteo(year: int, month: int) -> List[WeatherDay]:
    start = datetime(year, month, 1)
    end = (datetime(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1))
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude=22.3&longitude=114.2"
        f"&start_date={start.date()}&end_date={end.date()}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        "&timezone=Asia%2FHong_Kong"
    )
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    data = r.json()

   
    if "daily" not in data:
        print("[fallback] Open-Meteo did not return daily data:", data)
        return []

    d = data["daily"]

    def code_to_type(code, precip):
        if precip and precip > RAINY_THRESHOLD:
            return "rainy"
        if precip and precip > CLOUDY_THRESHOLD:
            return "cloudy"
        cloudy = {1, 2, 3, 45, 48}
        return "cloudy" if code in cloudy else "sunny"

    out: List[WeatherDay] = []
    for i, ds in enumerate(d["time"]):
        date = datetime.fromisoformat(ds)
        tmax = d["temperature_2m_max"][i]
        tmin = d["temperature_2m_min"][i]
        temp = (tmax + tmin) / 2.0
        wtype = code_to_type(d["weathercode"][i], d["precipitation_sum"][i])
        out.append(WeatherDay(date, temp, wtype))
    print(f"[fallback] Open-Meteo returned {len(out)} days.")
    return out


# ---------- main fetch ----------
def fetch_hk_data(year: int, month: int) -> List[WeatherDay]:
    """Try HKO first; if empty, fallback to Open-Meteo."""
    try:
        temp_rows = _read_csv_from_url(HKO_TEMP_URL)
        rain_rows = _read_csv_from_url(HKO_RAIN_URL)
        print(f"[HKO] temp_rows={len(temp_rows)}, rain_rows={len(rain_rows)}")
    except Exception as e:
        print(f"[HKO] fetch error: {e} -> using fallback")
        return _fallback_open_meteo(year, month)

    # date -> mean temp
    temps = {}
    for r in temp_rows:
        d = _parse_date_any(r)
        if not d or d.year != year or d.month != month:
            continue
        t_mean = _get_float_any(r, "daily mean", "mean(°c)", "mean", "avg")
        if t_mean is None:
            t_max = _get_float_any(r, "daily max", "max")
            t_min = _get_float_any(r, "daily min", "min")
            if t_max is not None and t_min is not None:
                t_mean = (t_max + t_min) / 2.0
        if t_mean is not None:
            temps[d.date()] = float(t_mean)

    # date -> rainfall
    rains = {}
    for r in rain_rows:
        d = _parse_date_any(r)
        if not d or d.year != year or d.month != month:
            continue
        rain = _get_float_any(r, "rainfall", "rain", "(mm)")
        rains[d.date()] = 0.0 if rain is None else float(rain)

    print(f"[HKO] matched days: temps={len(temps)}, rains={len(rains)}")

    out: List[WeatherDay] = []
    for day, t_mean in sorted(temps.items()):
        precip = rains.get(day, 0.0) or 0.0
        if precip > RAINY_THRESHOLD:
            wtype = "rainy"
        elif precip > CLOUDY_THRESHOLD:
            wtype = "cloudy"
        else:
            wtype = "sunny"
        out.append(WeatherDay(datetime(day.year, day.month, day.day), t_mean, wtype))

    if not out:
        print("[HKO] no rows parsed for the requested month -> fallback to Open-Meteo")
        return _fallback_open_meteo(year, month)

    print(f"[HKO] returned {len(out)} days.")
    return out