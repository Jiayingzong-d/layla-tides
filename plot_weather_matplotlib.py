# -*- coding: utf-8 -*-
"""
Static visualization using pandas + matplotlib
Data: Hong Kong August 2024 (reuses data_fetch.fetch_hk_data)
Outputs:
- A figure with (1) date vs mean temperature (colored by weather type)
  and (2) bar chart for counts by weather type
- Saves to plots/aug_2024_weather.png
"""

import os
from datetime import datetime
from collections import Counter

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from data_fetch import fetch_hk_data  # re-use your existing data loader


WEATHER_COLORS = {
    "sunny":  "#f5b000",  # warm yellow
    "cloudy": "#9aa3b2",  # gray
    "rainy":  "#4a9eff",  # blue
}

def to_dataframe(year: int, month: int) -> pd.DataFrame:
    """Fetch data and convert to a tidy pandas DataFrame."""
    records = fetch_hk_data(year, month)
    if not records:
        raise RuntimeError(f"No data for {year}-{month:02d}.")
    df = pd.DataFrame([{
        "date": r.date,
        "day": r.date.day,
        "mean_temp": float(r.temperature),
        "weather": r.weather_type
    } for r in records])
    df.sort_values("date", inplace=True)
    return df


def plot_august_2024(df: pd.DataFrame, save_path: str | None = None):
    """Make a 2-row figure:
       1) Date vs mean temperature (scatter colored by weather) + line
       2) Bar chart for weather-type counts
    """
    # --- figure layout
    plt.close("all")
    fig = plt.figure(figsize=(12, 7), constrained_layout=True)
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1])

    ax1 = fig.add_subplot(gs[0, 0])  # date-temp
    ax2 = fig.add_subplot(gs[1, 0])  # counts

    # --- Top: date vs temp
    # line for trend
    ax1.plot(df["date"], df["mean_temp"], lw=1.8, color="#444444", alpha=0.8, label="Mean temperature")

    # scatter, colored by weather type
    for wtype, sub in df.groupby("weather"):
        ax1.scatter(sub["date"], sub["mean_temp"],
                    s=40, label=wtype.capitalize(),
                    color=WEATHER_COLORS.get(wtype, "#666666"), zorder=3, alpha=0.9)

    # x/y formatting
    ax1.set_title("Hong Kong — August 2024: Daily Mean Temperature", fontsize=14, pad=10)
    ax1.set_ylabel("Temperature (°C)", fontsize=11)

    # X ticks: every 2 days, nice format
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax1.grid(True, axis="y", alpha=0.25)
    ax1.legend(frameon=False, ncol=3, loc="upper left", fontsize=10)

    # --- Bottom: weather-type counts
    counts = Counter(df["weather"])
    order = ["sunny", "cloudy", "rainy"]
    labels = [w.capitalize() for w in order]
    values = [counts.get(w, 0) for w in order]
    colors = [WEATHER_COLORS[w] for w in order]

    ax2.bar(labels, values, color=colors)
    ax2.set_ylabel("Days", fontsize=11)
    ax2.set_title("Weather-type distribution (days)", fontsize=12, pad=6)
    ax2.grid(True, axis="y", alpha=0.25)

    # tighten layout and save
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=150)
        print(f"Saved figure to: {save_path}")

    plt.show()


def main():
    df = to_dataframe(2024, 8)
    print(df.head())
    plot_august_2024(df, save_path="plots/aug_2024_weather.png")


if __name__ == "__main__":
    main()