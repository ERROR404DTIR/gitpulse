#!/usr/bin/env python3
"""gitpulse - feel the heartbeat of any git repository.

Single file, zero dependencies (just Python 3.8+ and git).
Shows a contribution heatmap, streaks, busiest days/hours, top authors and
hot files in your terminal, or exports a self-contained HTML report.
"""
import argparse
import html
import math
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta

__version__ = "1.0.0"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SHADES = [238, 22, 28, 34, 46]  # 256-color greens, dark -> bright
PLAIN = "·░▒▓█"
SPARK = "▁▂▃▄▅▆▇█"


# ---------------------------------------------------------------- git layer
def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        sys.exit("gitpulse: git is not installed or not in PATH")
    if r.returncode != 0:
        sys.exit("gitpulse: " + (r.stderr.strip() or "not a git repository"))
    return r.stdout


def load(repo, since=None, author=None):
    args = ["log", "--no-merges", "--pretty=format:@@%H|%an|%at", "--numstat"]
    if since:
        args.append("--since=" + since)
    if author:
        args.append("--author=" + author)
    commits, cur = [], None
    for line in git(repo, *args).splitlines():
        if line.startswith("@@"):
            _, rest = line[2:].split("|", 1)
            name, ts = rest.rsplit("|", 1)
            cur = {"author": name, "when": datetime.fromtimestamp(int(ts)),
                   "add": 0, "del": 0, "files": []}
            commits.append(cur)
        elif line.strip() and cur is not None:
            parts = line.split("\t", 2)
            if len(parts) == 3:
                a, d, path = parts
                cur["add"] += int(a) if a.isdigit() else 0
                cur["del"] += int(d) if d.isdigit() else 0
                cur["files"].append(path)
    return commits


# ----------------------------------------------------------------- analysis
def streaks(days):
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best, prev = max(best, run), d
    cur, d = 0, date.today()
    if d not in days:
        d -= timedelta(days=1)
    while d in days:
        cur += 1
        d -= timedelta(days=1)
    return best, cur


def analyze(commits):
    days = Counter(c["when"].date() for c in commits)
    authors = {}
    for c in commits:
        a = authors.setdefault(c["author"], [0, 0, 0])
        a[0] += 1
        a[1] += c["add"]
        a[2] += c["del"]
    best, cur = streaks(days)
    return {
        "total": len(commits),
        "days": days,
        "weekday": Counter(c["when"].weekday() for c in commits),
        "hour": Counter(c["when"].hour for c in commits),
        "authors": sorted(authors.items(), key=lambda kv: -kv[1][0]),
        "files": Counter(f for c in commits for f in c["files"]),
        "add": sum(c["add"] for c in commits),
        "del": sum(c["del"] for c in commits),
        "first": min(days) if days else None,
        "last": max(days) if days else None,
        "best": best,
        "cur": cur,
    }


def level(count, peak):
    return 0 if not count else max(1, min(4, math.ceil(count * 4 / peak)))


def grid(days, weeks):
    today = date.today()
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    cols = []
    for w in range(weeks):
        col = []
        for d in range(7):
            day = start + timedelta(days=w * 7 + d)
            col.append((day, days.get(day, 0) if day <= today else None))
        cols.append(col)
    return cols


# ----------------------------------------------------------- terminal output
def paint(text, code, color):
    return f"\033[{code}m{text}\033[0m" if color else text


def bar(value, peak, width=26):
    if not value:
        return ""
    return "█" * max(1, round(value / peak * width))


def heatmap_text(days, color, weeks):
    cols = grid(days, weeks)
    peak = max(days.values(), default=1)
    labels, last, prev = [" "] * (weeks * 2 + 2), -9, None
    for i, col in enumerate(cols):
        month = col[0][0].month
        if month != prev and i - last >= 2 and i <= weeks - 2:
            labels[i * 2:i * 2 + 3] = list(col[0][0].strftime("%b"))
            last = i
        prev = month
    out = ["    " + "".join(labels).rstrip()]
    for d in range(7):
        row = DAYS[d] + " " if d in (0, 2, 4) else "    "
        for col in cols:
            val = col[d][1]
            if val is None:
                row += "  "
            elif color:
                row += f"\033[38;5;{SHADES[level(val, peak)]}m■\033[0m "
            else:
                row += PLAIN[level(val, peak)] + " "
        out.append(row.rstrip())
    legend = "    less " + "".join(
        (f"\033[38;5;{c}m■\033[0m " if color else p + " ")
        for c, p in zip(SHADES, PLAIN)) + "more"
    return "\n".join(out + [legend])


def render_terminal(s, repo, color, top):
    width = shutil.get_terminal_size((100, 24)).columns
    weeks = max(10, min(53, (width - 6) // 2))
    o = []
    o.append(paint(f"\n  ♥ gitpulse · {repo}", "1;32", color))
    span = f"{s['first']} → {s['last']}"
    o.append(f"  {s['total']:,} commits · {len(s['authors'])} authors · {span}")
    o.append(f"  {paint('+' + format(s['add'], ','), '32', color)} / "
             f"{paint('-' + format(s['del'], ','), '31', color)} lines · "
             f"{len(s['days'])} active days")
    o.append(f"  🔥 current streak {s['cur']}d · longest streak {s['best']}d\n")
    o.append(heatmap_text(s["days"], color, weeks))

    o.append(paint("\n  Weekdays", "1", color))
    peak = max(s["weekday"].values(), default=1)
    for d in range(7):
        n = s["weekday"].get(d, 0)
        o.append(f"  {DAYS[d]} {paint(bar(n, peak).ljust(26), '36', color)} {n}")

    o.append(paint("\n  Hours (0-23)", "1", color))
    hp = max(s["hour"].values(), default=1)
    spark = "".join(SPARK[min(7, int(s["hour"].get(h, 0) / hp * 7.99))]
                    if s["hour"].get(h) else " " for h in range(24))
    o.append("  " + paint(spark, "35", color))
    o.append("  0     6     12    18   23")
    busy = max(range(24), key=lambda h: s["hour"].get(h, 0))
    o.append(f"  busiest hour: {busy:02d}:00")

    o.append(paint("\n  Top authors", "1", color))
    ap = s["authors"][0][1][0] if s["authors"] else 1
    for name, (n, a, d) in s["authors"][:top]:
        o.append(f"  {name[:18]:<18} {paint(bar(n, ap, 18).ljust(18), '33', color)}"
                 f" {n:>5}  +{a:,}/-{d:,}")

    o.append(paint("\n  Hot files (most changed)", "1", color))
    fp = s["files"].most_common(1)[0][1] if s["files"] else 1
    for path, n in s["files"].most_common(top):
        o.append(f"  {n:>4} {paint(bar(n, fp, 12).ljust(12), '31', color)} {path[:60]}")
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------- HTML report
def render_html(s, repo):
    cols = grid(s["days"], 53)
    peak = max(s["days"].values(), default=1)
    cells = []
    for x, col in enumerate(cols):
        for y, (day, val) in enumerate(col):
            if val is None:
                continue
            cells.append(f'<rect class="l{level(val, peak)}" x="{x * 14}" y="{y * 14}" '
                         f'width="11" height="11" rx="2"><title>{day}: {val} commits'
                         f'</title></rect>')

    def bars(items, peak_v):
        return "".join(
            f'<div class="row"><span>{html.escape(str(k))}</span>'
            f'<i style="width:{max(2, v / peak_v * 100):.0f}%"></i><b>{v}</b></div>'
            for k, v in items if v)

    wp = max(s["weekday"].values(), default=1)
    hp = max(s["hour"].values(), default=1)
    ap = s["authors"][0][1][0] if s["authors"] else 1
    fp = s["files"].most_common(1)[0][1] if s["files"] else 1
    stat = lambda n, t: f'<div class="stat"><b>{n}</b><span>{t}</span></div>'
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>gitpulse · {html.escape(repo)}</title><style>
body{{background:#0d1117;color:#c9d1d9;font:15px/1.5 system-ui,sans-serif;margin:0;padding:32px;animation:f .6s}}
@keyframes f{{from{{opacity:0;transform:translateY(8px)}}}}
h1{{color:#3fb950;margin:0 0 4px}}h2{{margin:28px 0 8px;font-size:16px;color:#8b949e}}
.stats{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}}
.stat{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px}}
.stat b{{display:block;font-size:22px;color:#58a6ff}}.stat span{{font-size:12px;color:#8b949e}}
svg{{max-width:100%;height:auto}}.l0{{fill:#161b22}}.l1{{fill:#0e4429}}.l2{{fill:#006d32}}.l3{{fill:#26a641}}.l4{{fill:#39d353}}
.row{{display:flex;align-items:center;gap:10px;margin:3px 0}}.row span{{width:150px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}}
.row i{{display:block;height:10px;background:#58a6ff;border-radius:5px}}.row b{{color:#8b949e;font-weight:400}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}}
</style></head><body>
<h1>♥ gitpulse</h1><div>{html.escape(repo)} · {s['first']} → {s['last']}</div>
<div class="stats">{stat(f"{s['total']:,}", "commits")}{stat(len(s['authors']), "authors")}
{stat(f"+{s['add']:,}", "lines added")}{stat(f"-{s['del']:,}", "lines removed")}
{stat(len(s['days']), "active days")}{stat(f"{s['cur']}d", "current streak")}{stat(f"{s['best']}d", "longest streak")}</div>
<h2>Last 12 months</h2><svg viewBox="0 0 {53 * 14} {7 * 14}">{"".join(cells)}</svg>
<div class="grid"><div><h2>Weekdays</h2>{bars([(DAYS[d], s['weekday'].get(d, 0)) for d in range(7)], wp)}</div>
<div><h2>Hours</h2>{bars([(f"{h:02d}:00", s['hour'].get(h, 0)) for h in range(24)], hp)}</div>
<div><h2>Authors</h2>{bars([(n, v[0]) for n, v in s['authors'][:10]], ap)}</div>
<div><h2>Hot files</h2>{bars(s['files'].most_common(10), fp)}</div></div>
</body></html>"""


# ----------------------------------------------------------------------- CLI
def main(argv=None):
    p = argparse.ArgumentParser(prog="gitpulse",
                                description="Feel the heartbeat of any git repo.")
    p.add_argument("path", nargs="?", default=".", help="repo path (default: .)")
    p.add_argument("--since", help='e.g. "6 months ago" or 2026-01-01')
    p.add_argument("--author", help="only count commits by this author")
    p.add_argument("--top", type=int, default=5, help="rows in top lists (default 5)")
    p.add_argument("--html", metavar="FILE", help="also write a self-contained HTML report")
    p.add_argument("--no-color", action="store_true", help="plain output")
    p.add_argument("-V", "--version", action="version", version=__version__)
    a = p.parse_args(argv)

    commits = load(a.path, a.since, a.author)
    if not commits:
        sys.exit("gitpulse: no commits found")
    s = analyze(commits)
    name = git(a.path, "rev-parse", "--show-toplevel").strip().replace("\\", "/").split("/")[-1]
    color = sys.stdout.isatty() and not a.no_color
    print(render_terminal(s, name, color, a.top))
    if a.html:
        with open(a.html, "w", encoding="utf-8") as f:
            f.write(render_html(s, name))
        print(f"  HTML report saved to {a.html}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        sys.exit(1)
