#!/usr/bin/env python3
"""Generate terminal-themed SVG cards for the profile README (no external services)."""
import base64
import datetime as dt
import json
import os
import textwrap
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "FiTcHeRs71")
TOKEN = os.environ["GITHUB_TOKEN"]
WAKA_KEY = os.environ.get("WAKATIME_API_KEY", "")
OUT = os.path.join(os.path.dirname(__file__), "..", "cards")

PINS = {
    "WebServ": "Non-blocking HTTP/1.1 server with CGI and nginx-like config.",
    "42-Mini-Shell": "Bash-like shell: lexer, recursive descent parser to AST, pipes, redirections.",
    "42-Cub3D": "Wolfenstein 3D-style raycasting engine built with the miniLibX.",
    "42bet": "Real-money-free football predictions for 42 Lausanne students.",
    "42-Inception": "NGINX + WordPress + MariaDB infrastructure, one Docker container per service.",
}

BG, BORDER, GREEN, TEXT, MUTED = "#0d1117", "#1f6f3a", "#00ff41", "#c9d1d9", "#7d8590"
FONT = "'Fira Code','JetBrains Mono',Consolas,monospace"


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]


def frame(w, h, title, inner):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>
  text {{ font-family: {FONT}; }}
  .fade {{ animation: in .6s ease-out both; }}
  @keyframes in {{ from {{ opacity: 0; }} }}
</style>
<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="8" fill="{BG}" stroke="{BORDER}"/>
<circle cx="18" cy="16" r="5" fill="#ff5f56"/><circle cx="34" cy="16" r="5" fill="#ffbd2e"/><circle cx="50" cy="16" r="5" fill="#27c93f"/>
<text x="68" y="20" font-size="12" fill="{MUTED}">{escape(title)}</text>
{inner}
</svg>
"""


def write(name, svg):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(svg)
    print("wrote", name)


def pin_card(repo, desc):
    lines = textwrap.wrap(desc, 48)[:2]
    body = [f'<text x="18" y="52" font-size="16" font-weight="700" fill="{GREEN}">./{escape(repo["name"])}</text>']
    for i, line in enumerate(lines):
        body.append(f'<text x="18" y="{76 + i * 17}" font-size="12" fill="{TEXT}">{escape(line)}</text>')
    lang = repo["primaryLanguage"] or {"name": "Shell", "color": "#89e051"}
    body.append(f'<circle cx="24" cy="126" r="5" fill="{lang["color"] or MUTED}"/>')
    body.append(f'<text x="36" y="130" font-size="12" fill="{MUTED}">{escape(lang["name"])}</text>')
    body.append(f'<text x="160" y="130" font-size="12" fill="{MUTED}">★ {repo["stargazerCount"]}   ⑂ {repo["forkCount"]}</text>')
    return frame(400, 150, f"~/projects/{repo['name']}", '<g class="fade">' + "".join(body) + "</g>")


def rows_card(title, rows, w=400):
    h = 44 + 24 * len(rows) + 10
    body = []
    for i, (label, value) in enumerate(rows):
        y = 56 + i * 24
        delay = f'style="animation-delay:{i * 0.12:.2f}s"'
        body.append(
            f'<g class="fade" {delay}><text x="18" y="{y}" font-size="13" fill="{GREEN}">$</text>'
            f'<text x="34" y="{y}" font-size="13" fill="{TEXT}">{escape(label)}</text>'
            f'<text x="{w - 18}" y="{y}" font-size="13" fill="{GREEN}" text-anchor="end" font-weight="700">{escape(str(value))}</text></g>'
        )
    return frame(w, h, title, "".join(body))


def bars_card(title, items, w=400):
    """items: list of (name, percent, color, right_label)."""
    h = 44 + 30 * len(items) + 6
    body = []
    for i, (name, pct, color, right) in enumerate(items):
        y = 54 + i * 30
        bw = max(2, (w - 36) * pct / 100)
        delay = f"animation-delay:{i * 0.12:.2f}s"
        body.append(
            f'<g class="fade" style="{delay}">'
            f'<text x="18" y="{y}" font-size="12" fill="{TEXT}">{escape(name)}</text>'
            f'<text x="{w - 18}" y="{y}" font-size="12" fill="{MUTED}" text-anchor="end">{escape(right)}</text>'
            f'<rect x="18" y="{y + 6}" width="{w - 36}" height="6" rx="3" fill="#161b22"/>'
            f'<rect x="18" y="{y + 6}" width="{bw:.1f}" height="6" rx="3" fill="{color}"/></g>'
        )
    return frame(w, h, title, "".join(body))


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    tail = counts[:-1] if counts and counts[-1] == 0 else counts  # today may still be empty
    for c in reversed(tail):
        if not c:
            break
        current += 1
    return current, longest


def activity_card(days, w=820, h=190):
    last = days[-60:]
    peak = max((d["contributionCount"] for d in last), default=0) or 1
    left, right, top, bottom = 40, w - 20, 44, h - 30
    step = (right - left) / max(1, len(last) - 1)
    pts = [(left + i * step, bottom - (bottom - top) * d["contributionCount"] / peak) for i, d in enumerate(last)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{left},{bottom} {line} {right},{bottom}"
    length = int(sum(((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5 for i in range(len(pts) - 1))) + 1
    inner = f"""
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity=".35"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient></defs>
<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#21262d"/>
<text x="{left - 8}" y="{top + 4}" font-size="10" fill="{MUTED}" text-anchor="end">{peak}</text>
<text x="{left - 8}" y="{bottom + 4}" font-size="10" fill="{MUTED}" text-anchor="end">0</text>
<text x="{left}" y="{h - 10}" font-size="10" fill="{MUTED}">{last[0]["date"]}</text>
<text x="{right}" y="{h - 10}" font-size="10" fill="{MUTED}" text-anchor="end">{last[-1]["date"]}</text>
<polygon class="fade" points="{area}" fill="url(#g)" style="animation-delay:1.2s"/>
<polyline points="{line}" fill="none" stroke="{GREEN}" stroke-width="2" stroke-linejoin="round"
  stroke-dasharray="{length}">
  <animate attributeName="stroke-dashoffset" from="{length}" to="0" dur="2s" fill="freeze"/>
</polyline>"""
    return frame(w, h, "git log --since=60.days | plot", inner)


def main():
    os.makedirs(OUT, exist_ok=True)
    data = gql(
        """query($login: String!) {
          user(login: $login) {
            followers { totalCount }
            pullRequests { totalCount }
            issues { totalCount }
            contributionsCollection {
              totalCommitContributions
              restrictedContributionsCount
              contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
            }
            repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
              nodes {
                name stargazerCount forkCount
                primaryLanguage { name color }
                languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
              }
            }
          }
        }""",
        {"login": USER},
    )["user"]

    repos = {r["name"]: r for r in data["repositories"]["nodes"]}
    for name, desc in PINS.items():
        if name in repos:
            write(f"pin-{name}.svg", pin_card(repos[name], desc))

    cc = data["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(days)
    stars = sum(r["stargazerCount"] for r in repos.values())
    write("stats.svg", rows_card("git log --stat", [
        ("contributions (last year)", cc["contributionCalendar"]["totalContributions"]),
        ("commits", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("public repos", len(repos)),
        ("pull requests", data["pullRequests"]["totalCount"]),
        ("stars earned", stars),
    ]))
    write("streak.svg", rows_card("streak --watch", [
        ("current streak", f"{current} day{'' if current == 1 else 's'}"),
        ("longest streak (1y)", f"{longest} day{'' if longest == 1 else 's'}"),
        ("active days (1y)", sum(1 for d in days if d["contributionCount"])),
        ("best day", max(d["contributionCount"] for d in days)),
        ("today", days[-1]["contributionCount"]),
    ]))
    write("activity.svg", activity_card(days))

    langs = {}
    for r in repos.values():
        for e in r["languages"]["edges"]:
            n = e["node"]
            size, color = langs.get(n["name"], (0, n["color"]))
            langs[n["name"]] = (size + e["size"], color or MUTED)
    total = sum(s for s, _ in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
    write("languages.svg", bars_card("cloc ~/repos --top 6",
        [(n, s * 100 / total, c, f"{s * 100 / total:.1f}%") for n, (s, c) in top]))

    if WAKA_KEY:
        auth = base64.b64encode(WAKA_KEY.encode()).decode()
        req = urllib.request.Request(
            "https://wakatime.com/api/v1/users/current/stats/last_7_days",
            headers={"Authorization": f"Basic {auth}"},
        )
        with urllib.request.urlopen(req) as r:
            waka = json.load(r)["data"]
        items = [l for l in waka.get("languages", []) if l["name"] != "Other"][:6]
        write("wakatime.svg", bars_card(
            f"wakatime --last-7-days  ({waka.get('human_readable_total', '0 mins')})",
            [(l["name"], l["percent"], GREEN, l["text"]) for l in items],
        ))
    print("done", dt.datetime.now(dt.timezone.utc).isoformat())


if __name__ == "__main__":
    main()
