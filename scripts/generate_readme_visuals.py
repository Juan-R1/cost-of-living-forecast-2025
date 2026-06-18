"""Generate README visuals from the cleaned Texas rent forecast output."""

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_ROOT / "Data" / "Cleaned" / "forecast_output.csv"
IMAGES_DIR = PROJECT_ROOT / "images"

COLORS = {
    "Austin, TX": "#2c7fb8",
    "Dallas, TX": "#41ab5d",
    "El Paso, TX": "#fdae61",
    "San Antonio, TX": "#756bb1",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def load_forecast() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE, parse_dates=["ds"])
    return df.sort_values(["City", "ds"])


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def scale(value: float, old_min: float, old_max: float, new_min: float, new_max: float) -> float:
    if old_max == old_min:
        return new_min
    return new_min + (value - old_min) * (new_max - new_min) / (old_max - old_min)


def draw_title(draw: ImageDraw.ImageDraw, title: str, width: int) -> None:
    title_font = font(34, bold=True)
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (bbox[2] - bbox[0])) / 2, 28), title, fill="#222222", font=title_font)


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    fill: tuple[int, int, int],
    width: int = 4,
    dash_length: int = 14,
    gap_length: int = 9,
) -> None:
    x1, y1 = start
    x2, y2 = end
    distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    if distance == 0:
        return
    step = dash_length + gap_length
    steps = int(distance // step) + 1
    for index in range(steps):
        start_dist = index * step
        end_dist = min(start_dist + dash_length, distance)
        if start_dist >= distance:
            break
        sx = x1 + (x2 - x1) * start_dist / distance
        sy = y1 + (y2 - y1) * start_dist / distance
        ex = x1 + (x2 - x1) * end_dist / distance
        ey = y1 + (y2 - y1) * end_dist / distance
        draw.line((sx, sy, ex, ey), fill=fill, width=width)


def save_forecast_trend(df: pd.DataFrame) -> None:
    width, height = 1400, 820
    margin_left, margin_right, margin_top, margin_bottom = 120, 280, 120, 115
    chart_left, chart_top = margin_left, margin_top
    chart_right, chart_bottom = width - margin_right, height - margin_bottom

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw_title(draw, "Texas Rent Forecast by City", width)

    min_date = df["ds"].min()
    max_date = df["ds"].max()
    min_value = df["y"].min() * 0.94
    max_value = df["y"].max() * 1.04

    axis_font = font(18)
    label_font = font(20)
    draw.line((chart_left, chart_bottom, chart_right, chart_bottom), fill="#333333", width=2)
    draw.line((chart_left, chart_top, chart_left, chart_bottom), fill="#333333", width=2)

    for step in range(5):
        y_value = min_value + (max_value - min_value) * step / 4
        y = scale(y_value, min_value, max_value, chart_bottom, chart_top)
        draw.line((chart_left, y, chart_right, y), fill="#dddddd", width=1)
        draw.text((35, y - 10), f"{y_value:,.0f}", fill="#444444", font=axis_font)

    for year in [2015, 2017, 2019, 2021, 2023, 2025]:
        date = pd.Timestamp(f"{year}-01-31")
        x = scale(date.value, min_date.value, max_date.value, chart_left, chart_right)
        draw.line((x, chart_bottom, x, chart_bottom + 8), fill="#333333", width=2)
        draw.text((x - 20, chart_bottom + 15), str(year), fill="#444444", font=axis_font)

    for city, city_df in df.groupby("City"):
        color = hex_to_rgb(COLORS[city])
        actual = city_df[city_df["type"] == "actual"]
        forecast = city_df[city_df["type"] == "forecast"]
        actual_points = [
            (
                scale(row.ds.value, min_date.value, max_date.value, chart_left, chart_right),
                scale(row.y, min_value, max_value, chart_bottom, chart_top),
            )
            for row in actual.itertuples()
        ]
        forecast_points = [
            (
                scale(row.ds.value, min_date.value, max_date.value, chart_left, chart_right),
                scale(row.y, min_value, max_value, chart_bottom, chart_top),
            )
            for row in forecast.itertuples()
        ]
        if len(actual_points) > 1:
            draw.line(actual_points, fill=color, width=4)
        if forecast_points:
            joined = [actual_points[-1], *forecast_points]
            for start, end in zip(joined, joined[1:]):
                draw_dashed_line(draw, start, end, fill=color, width=4)

    draw.text((chart_left + 330, height - 55), "Date", fill="#222222", font=label_font)
    draw.text((20, chart_top + 210), "Rent value", fill="#222222", font=label_font)

    legend_x, legend_y = chart_right + 40, chart_top
    draw.text((legend_x, legend_y - 42), "City", fill="#222222", font=font(22, bold=True))
    for index, city in enumerate(COLORS):
        y = legend_y + index * 42
        draw.line((legend_x, y + 12, legend_x + 38, y + 12), fill=hex_to_rgb(COLORS[city]), width=5)
        draw.text((legend_x + 50, y), city, fill="#222222", font=axis_font)
    draw.text((legend_x, legend_y + 190), "Dashed portion: forecast", fill="#555555", font=axis_font)

    image.save(IMAGES_DIR / "cost_of_living_forecast.png")


def save_bar_chart(rows: list[tuple[str, float]], title: str, ylabel: str, output: str, percent: bool = False) -> None:
    width, height = 1100, 720
    chart_left, chart_top, chart_right, chart_bottom = 115, 120, 1030, 570
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw_title(draw, title, width)

    max_value = max(value for _, value in rows) * 1.12
    bar_width = 150
    gap = (chart_right - chart_left - bar_width * len(rows)) / max(1, len(rows) - 1)

    draw.line((chart_left, chart_bottom, chart_right, chart_bottom), fill="#333333", width=2)
    draw.line((chart_left, chart_top, chart_left, chart_bottom), fill="#333333", width=2)
    draw.text((chart_left, chart_top - 34), ylabel, fill="#222222", font=font(18, bold=True))

    for i in range(5):
        value = max_value * i / 4
        y = scale(value, 0, max_value, chart_bottom, chart_top)
        draw.line((chart_left, y, chart_right, y), fill="#dddddd", width=1)
        label = f"{value:.0f}%" if percent else f"{value:,.0f}"
        draw.text((30, y - 10), label, fill="#444444", font=font(16))

    for index, (city, value) in enumerate(rows):
        x0 = chart_left + index * (bar_width + gap)
        x1 = x0 + bar_width
        y0 = scale(value, 0, max_value, chart_bottom, chart_top)
        draw.rectangle((x0, y0, x1, chart_bottom), fill=hex_to_rgb(COLORS[city]))
        value_label = f"{value:.1f}%" if percent else f"{value:,.0f}"
        bbox = draw.textbbox((0, 0), value_label, font=font(18, bold=True))
        draw.text(((x0 + x1 - (bbox[2] - bbox[0])) / 2, y0 - 30), value_label, fill="#222222", font=font(18, bold=True))
        city_label = city.replace(", TX", "")
        bbox = draw.textbbox((0, 0), city_label, font=font(18))
        draw.text(((x0 + x1 - (bbox[2] - bbox[0])) / 2, chart_bottom + 20), city_label, fill="#222222", font=font(18))

    image.save(IMAGES_DIR / output)


def save_city_comparison(df: pd.DataFrame) -> None:
    latest_forecast = (
        df[df["type"] == "forecast"]
        .sort_values("ds")
        .groupby("City")
        .tail(1)
        .sort_values("y", ascending=False)
    )
    rows = [(row.City, row.y) for row in latest_forecast.itertuples()]
    save_bar_chart(rows, "Forecasted Rent Level by City", "Forecast value", "city_rent_comparison.png")


def save_growth_chart(df: pd.DataFrame) -> None:
    actual = df[df["type"] == "actual"].copy()
    rows = []
    for city, city_df in actual.groupby("City"):
        city_df = city_df.sort_values("ds")
        start = city_df.iloc[0]["y"]
        end = city_df.iloc[-1]["y"]
        rows.append((city, (end - start) / start * 100))
    rows.sort(key=lambda item: item[1], reverse=True)
    save_bar_chart(rows, "Actual Rent Growth in Included Texas Cities", "Growth", "rent_growth_comparison.png", percent=True)


def main() -> None:
    IMAGES_DIR.mkdir(exist_ok=True)
    df = load_forecast()
    save_forecast_trend(df)
    save_city_comparison(df)
    save_growth_chart(df)
    print(f"Saved visuals to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
