"""Build the animated profile SVG from the public GitHub contribution calendar."""

import argparse
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = "jackfeicoder"
PALETTE = ("#17344d", "#bceeff", "#76c9f1", "#368fd0", "#245caa")
WEEK_PITCH = 15
GRID_X, GRID_Y = 35, 56
CELL = 11
LABEL = "#b9d4e7"
RULE = "#254762"


class ContributionCalendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "ContributionCalendar-day" in attrs.get("class", "").split():
            self.days[date.fromisoformat(attrs["data-date"])] = int(attrs["data-level"])


def load_calendar(source):
    parser = ContributionCalendar()
    if source:
        parser.feed(source.read_text(encoding="utf-8"))
    else:
        request = Request(
            f"https://github.com/users/{USERNAME}/contributions",
            headers={"User-Agent": "jackfeicoder-profile-contribution-art/1.0"},
        )
        with urlopen(request, timeout=20) as response:
            parser.feed(response.read().decode("utf-8"))
    days = sorted(parser.days)
    if (
        not 350 <= len(days) <= 371
        or (days[-1] - days[0]).days + 1 != len(days)
        or any(level not in range(len(PALETTE)) for level in parser.days.values())
    ):
        raise ValueError("GitHub did not return a complete contribution calendar")
    return [(day, parser.days[day]) for day in days]


def make_svg(calendar):
    first = calendar[0][0]
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    width = max(865, GRID_X + ((calendar[-1][0] - sunday).days // 7 + 1) * WEEK_PITCH + 32)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 '
        f'{width} 197" width="{width}" height="197" aria-labelledby="chart-title">',
        '<title id="chart-title">Jack’s public GitHub contribution calendar</title>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="196" rx="15" fill="#0b1c2e" stroke="{RULE}"/>',
        '<text x="20" y="27" font-size="15" font-weight="700" fill="#e1f6ff">GitHub Contributions</text>',
        f'<g fill="{LABEL}" font-size="11">',
    ]
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        parts.append(f'<text x="8" y="{GRID_Y + row * WEEK_PITCH + 9}">{label}</text>')
    last_month = None
    columns = set()
    for day, level in calendar:
        week, weekday = divmod((day - sunday).days, 7)
        x, y = GRID_X + week * WEEK_PITCH, GRID_Y + weekday * WEEK_PITCH
        columns.add(week)
        if day.month != last_month:
            if day != first or first.day <= 15:
                parts.append(f'<text x="{x}" y="47">{day.month}月</text>')
            last_month = day.month
        parts.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{PALETTE[level]}">'
            f'<title>{day.isoformat()} · activity level {level}</title></rect>'
        )
    parts.append('</g>')
    parts.append(f'<text x="19" y="177" fill="{LABEL}" font-size="11">{first.isoformat()} — {calendar[-1][0].isoformat()}</text>')
    legend = width - 145
    parts.append(f'<text x="{legend}" y="177" fill="{LABEL}" font-size="11">Less</text>')
    for index, color in enumerate(PALETTE):
        parts.append(f'<rect x="{legend + 29 + index * 13}" y="167" width="10" height="10" rx="2" fill="{color}"/>')
    parts.append(f'<text x="{legend + 97}" y="177" fill="{LABEL}" font-size="11">More</text>')
    parts.extend(snake(max(columns)))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def snake(last_week):
    left = GRID_X + CELL // 2
    right = left + last_week * WEEK_PITCH
    rows = [GRID_Y + CELL // 2 + row * WEEK_PITCH for row in range(7)]
    points = [(left, rows[0])]
    for row, y in enumerate(rows):
        start, end = (left, right) if row % 2 == 0 else (right, left)
        points.extend(((start, y), (end, y)))
    path = "M " + " L ".join(f"{x} {y}" for x, y in points)
    parts = ['<g aria-hidden="true">']
    for index in range(9, -1, -1):
        radius = 5 if index else 6
        opacity = 1 - index * 0.075
        parts.append(
            f'<circle r="{radius}" fill="#28eddf" stroke="#0e6175" stroke-width="1" opacity="{opacity:.3f}">'
            f'<animateMotion path="{path}" dur="34s" begin="-{(10 - index) * 0.045:.3f}s" repeatCount="indefinite" calcMode="paced"/>'
            '</circle>'
        )
    parts.append('</g>')
    return parts


def main():
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--source", type=Path, help="Use a previously fetched public calendar for local preview")
    arguments.add_argument("--output", type=Path, default=Path("assets"))
    options = arguments.parse_args()
    calendar = load_calendar(options.source)
    options.output.mkdir(parents=True, exist_ok=True)
    svg = make_svg(calendar)
    (options.output / "contributions-snake.svg").write_text(svg, encoding="utf-8", newline="\n")
    print(f"Rendered {len(calendar)} days, from {calendar[0][0]} through {calendar[-1][0]}.")


if __name__ == "__main__":
    main()
