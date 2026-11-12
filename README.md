<div align="center">

<img src="assets/banner.svg" alt="gitpulse banner" width="800">

**Feel the heartbeat of any git repository. One Python file. Zero installs.**

![python](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)
![deps](https://img.shields.io/badge/dependencies-none-39d353)
![size](https://img.shields.io/badge/single%20file-~300%20lines-blue)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

<img src="assets/heatmap.svg" alt="animated heatmap" width="480">

</div>

## What you get

- 🟩 **Contribution heatmap** right in your terminal (adapts to your window width)
- 🔥 **Streaks**: current and longest, plus active days
- 📅 **Busiest weekdays** and a ⏰ **24-hour activity sparkline**
- 👥 **Top authors** with commits and lines added/removed
- 🌶️ **Hot files**: the files that change the most (usually where the bugs live)
- 🌐 **Self-contained HTML report** with `--html report.html` (no server, no CDN)

## Quick start

No `pip install`. Just download the file and run it inside any git repo:

```bash
curl -O https://raw.githubusercontent.com/ERROR404DTIR/gitpulse/main/gitpulse.py
python gitpulse.py
```

Requirements: Python 3.8+ and `git` in your PATH. That's it.

## Usage

```bash
python gitpulse.py                         # current repo
python gitpulse.py ~/projects/my-app       # any repo path
python gitpulse.py --since "6 months ago"  # limit the time range
python gitpulse.py --author "Sara"         # one person's pulse
python gitpulse.py --top 10                # longer top lists
python gitpulse.py --html report.html      # also export an HTML report
python gitpulse.py --no-color              # plain output (pipes, CI logs)
```

## Sample output

```text
  ♥ gitpulse · demo
  260 commits · 3 authors · 2025-12-16 → 2026-11-12
  +880 / -0 lines · 177 active days
  🔥 current streak 4d · longest streak 8d

  Weekdays
  Mon ██████████████████         31
  Tue █████████████████████████  42
  Wed █████████████████          29
  Thu ██████████████████████████ 44

  Hours (0-23)
  ▃▂▂▂▁▂▂▄▃▃▃▃▃▂▃▂▂▂▁▁▃▇██
  0     6     12    18   23
  busiest hour: 22:00

  Top authors
  Sara               ██████████████████   116  +409/-0
  Mina               ███████████           72  +260/-0
  Ali                ███████████           72  +211/-0
```

## How it works

gitpulse runs a single `git log --numstat` call, parses it in memory and renders the stats. It never modifies your repository and never touches the network. Merge commits are skipped so the numbers reflect real work.

## License

MIT
