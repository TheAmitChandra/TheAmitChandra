"""Refresh the profile chart from public Chess.com rapid game history."""

import json
import math
from datetime import datetime, timezone
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USERNAME = "thegeekyamit"
BASE = f"https://api.chess.com/pub/player/{USERNAME}"
README = Path(__file__).resolve().parents[1] / "README.md"
START, END = "<!-- CHESS:START -->", "<!-- CHESS:END -->"


def fetch(url):
    request = Request(url, headers={
        "User-Agent": "TheAmitChandra-profile/1.0 (https://github.com/TheAmitChandra)"
    })
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def rapid_games(archives, limit=100):
    games = {}
    for archive in sorted(archives, reverse=True):
        if not archive.startswith(BASE + "/games/"):
            raise ValueError("Unexpected archive URL")
        for game in fetch(archive)["games"]:
            if not game.get("rated") or game.get("time_class") != "rapid" or game.get("rules") != "chess":
                continue
            for side in ("white", "black"):
                player = game[side]
                if player["username"].lower() == USERNAME:
                    games[game["url"]] = (game["end_time"], player["rating"])
                    break
        if len(games) >= limit:
            break
    return sorted(games.values())[-limit:]


def chart(ratings, height=12):
    """One column per game, with box-drawing lines connecting rating levels."""
    if not ratings:
        raise ValueError("Cannot chart an empty rating history")
    low = math.floor(min(ratings) / 10) * 10
    high = math.ceil(max(ratings) / 10) * 10
    if high == low:
        high += 10
        low -= 10
    rows = [round((high - rating) / (high - low) * height) for rating in ratings]
    grid = [[" " for _ in ratings] for _ in range(height + 1)]
    grid[rows[0]][0] = "─"
    for x in range(1, len(rows)):
        previous, current = rows[x - 1], rows[x]
        if previous == current:
            grid[current][x] = "─"
        else:
            grid[previous][x] = "╮" if current > previous else "╯"
            grid[current][x] = "╰" if current > previous else "╭"
            for y in range(min(previous, current) + 1, max(previous, current)):
                grid[y][x] = "│"
    return "\n".join(
        f"{high - (high - low) * y / height:4.0f} ┤ {''.join(row)}".rstrip()
        for y, row in enumerate(grid)
    )


def render(stats, games):
    if not games:
        raise ValueError("No rated rapid games found; keeping the existing chart")
    ratings = [rating for _, rating in games]
    first, last = [datetime.fromtimestamp(games[i][0], timezone.utc).strftime("%d %b %Y") for i in (0, -1)]
    rapid = stats["chess_rapid"]
    return (
        f"<samp><strong>Rapid {rapid['last']['rating']}</strong> · Personal best "
        f"<strong>{rapid['best']['rating']}</strong></samp>\n\n"
        f"```text\nRAPID / LAST {len(games)} GAMES\n\n{chart(ratings)}\n\n"
        f"       {first} → {last} · oldest to newest\n```"
    )


def update(readme, block):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one pair of chess markers")
    before, rest = readme.split(START)
    _, after = rest.split(END)
    return before + START + "\n" + block + "\n" + END + after


def main():
    original = README.read_text(encoding="utf-8-sig")
    update(original, "")  # Validate markers before fetching anything.
    stats = fetch(BASE + "/stats")
    games = rapid_games(fetch(BASE + "/games/archives")["archives"])
    result = update(original, render(stats, games))
    # Write only after all requests succeed. No timestamp-only commits.
    if result != original:
        README.write_text(result, encoding="utf-8")
    print(f"Chess history refreshed: {len(games)} games, rapid {stats['chess_rapid']['last']['rating']}")


if __name__ == "__main__":
    main()
