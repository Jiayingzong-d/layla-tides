import re
import requests
import pandas as pd
import matplotlib.pyplot as plt

URL = "https://www.hko.gov.hk/en/tide/ttext.htm"

def fetch_tide_text(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text

def parse_tide_table(text: str) -> pd.DataFrame:
    cleaned = re.sub(r"[ \t\u3000]+", " ", text)
    rows = re.findall(r"(\d{2}:\d{2})\s+([0-9]+(?:\.[0-9]+)?)", cleaned)
    if not rows:
        raise ValueError("未找到潮汐数据，网页结构可能变了。")
    df = pd.DataFrame(rows, columns=["time", "height_m"])
    df["height_m"] = df["height_m"].astype(float)
    today = pd.Timestamp.now(tz="Asia/Hong_Kong").date()
    df["ts"] = pd.to_datetime(
        df["time"].apply(lambda t: f"{today} {t}")
    ).dt.tz_localize("Asia/Hong_Kong")
    return df.sort_values("ts")

def plot_tide(df: pd.DataFrame):
    plt.figure()
    plt.plot(df["ts"], df["height_m"], marker="o")
    plt.title("Hong Kong Tide (Today)")
    plt.xlabel("Time (HKT)")
    plt.ylabel("Height (m)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig("tide_today.png", dpi=160)
    plt.show()

def main():
    txt = fetch_tide_text(URL)
    df = parse_tide_table(txt)
    print(df.head())
    plot_tide(df)

if __name__ == "__main__":
    main()