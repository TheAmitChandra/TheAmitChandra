"""Generate a daily GitHub activity card using gh and GitHub's GraphQL API.

ACTIVITY_METRIC selects commits or contributions. Contributions include the
private activity the user shares on their profile. Exact private commit counts
require an appropriately authorized GH_TOKEN; restricted counts are never
assumed to be commits. Streaks follow contribution-calendar days in UTC.
"""

from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import subprocess
import time

USERNAME = "TheAmitChandra"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "github-activity.svg"


def graphql(query, **variables):
    payload = json.dumps({"query": query, "variables": variables})
    for attempt in range(3):
        result = subprocess.run(
            ["gh", "api", "graphql", "--input", "-"], input=payload,
            text=True, encoding="utf-8", capture_output=True, timeout=60,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if not data.get("errors") and data.get("data"):
                return data["data"]
        if attempt < 2:
            time.sleep(2 ** attempt)
    raise RuntimeError("GitHub activity query failed; keeping the existing card")


def fetch_history(now, metric="commits"):
    validate_metric(metric)
    user = graphql(
        "query($login:String!){user(login:$login){createdAt "
        "contributionsCollection{contributionYears}}}", login=USERNAME,
    )["user"]
    if not user:
        raise ValueError("GitHub user not found")
    first_year = min([int(user["createdAt"][:4])] + user["contributionsCollection"]["contributionYears"])
    days, total = {}, 0
    query = """query($login:String!,$from:DateTime!,$to:DateTime!) {
      user(login:$login) {
        contributionsCollection(from:$from,to:$to) {
          totalCommitContributions
          contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
        }
      }
    }"""
    for year in range(first_year, now.year + 1):
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = min(datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc), now)
        collection = graphql(query, **{
            "login": USERNAME, "from": start.isoformat(), "to": end.isoformat(),
        })["user"]["contributionsCollection"]
        count = (collection["totalCommitContributions"] if metric == "commits"
                 else collection["contributionCalendar"]["totalContributions"])
        if not isinstance(count, int) or count < 0:
            raise ValueError("Invalid activity count")
        total += count
        for week in collection["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                when = date.fromisoformat(day["date"])
                if start.date() <= when <= end.date():
                    days[when] = day["contributionCount"]
        # Missing calendar data must not silently turn into a broken streak.
        cursor = start.date()
        while cursor <= end.date():
            if cursor not in days:
                raise ValueError(f"Incomplete contribution calendar: {cursor}")
            cursor += timedelta(days=1)
    return total, days, first_year


def streaks(days, today):
    current = best = run = 0
    previous = None
    for day, count in sorted(days.items()):
        if day > today:
            continue
        if count > 0:
            run = run + 1 if previous == day - timedelta(days=1) else 1
            best = max(best, run)
        else:
            run = 0
        previous = day
    cursor = today if days.get(today, 0) > 0 else today - timedelta(days=1)
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return current, best


def validate_metric(metric):
    if metric not in ("commits", "contributions"):
        raise ValueError("ACTIVITY_METRIC must be commits or contributions")


def render(total, current, best, first_year, today, metric="commits"):
    validate_metric(metric)
    title = f"{total:,} total {metric}, {current} day current streak, {best} day best streak"
    description = ("GitHub-counted commits visible to the API token across contribution history."
                   if metric == "commits" else
                   "GitHub contribution-calendar total, including shared private activity, commits, pull requests, reviews, and issues.")
    cells = []
    for x, label, number, caption in (
        (24, f"TOTAL {metric.upper()}", total, f"since {first_year}"),
        (234, "CURRENT STREAK", current, "consecutive days"),
        (444, "BEST STREAK", best, "consecutive days"),
    ):
        cells.append(f'''  <text x="{x}" y="29" fill="#9aa6b2" font-size="11" letter-spacing="1">{label}</text>
  <text x="{x}" y="68" fill="#e6edf3" font-size="30" font-weight="600">{number:,}</text>
  <text x="{x}" y="91" fill="#8daba0" font-size="11">{caption}</text>''')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="660" height="142" viewBox="0 0 660 142" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{description} Streaks count active contribution-calendar days in UTC; today may still be in progress. Updated {today.isoformat()}.</desc>
  <rect x=".5" y=".5" width="659" height="141" rx="8" fill="#161b22" stroke="#38414c"/>
  <path d="M218 20v76M428 20v76M24 108h612" stroke="#303944"/>
  <g font-family="monospace">
{chr(10).join(cells)}
  <circle cx="28" cy="125" r="3" fill="#8daba0"/>
  <text x="40" y="129" fill="#9aa6b2" font-size="10">DAILY SYNC · {today.isoformat()} UTC</text>
  </g>
</svg>
'''


def main():
    now = datetime.now(timezone.utc)
    metric = os.environ.get("ACTIVITY_METRIC", "contributions")
    total, days, first_year = fetch_history(now, metric)
    current, best = streaks(days, now.date())
    svg = render(total, current, best, first_year, now.date(), metric)
    # All API calls and validation finish before replacing the published asset.
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Activity card: {total} {metric}, current streak {current}, best streak {best}")


if __name__ == "__main__":
    main()
