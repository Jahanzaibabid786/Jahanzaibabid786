"""Generate assets/stats.svg from the GitHub GraphQL API (real data only)."""
import json
import os
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USER = os.environ.get("USERNAME") or sys.argv[1]
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = Path(os.environ.get("OUT", "assets/stats.svg"))

QUERY = """
query($login:String!){
  user(login:$login){
    createdAt
    repositories(ownerAffiliations:OWNER, privacy:PUBLIC){ totalCount }
    followers{ totalCount }
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount } }
      }
    }
  }
}"""

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
    headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-stats"},
)
data = json.load(urllib.request.urlopen(req))
if "errors" in data:
    sys.exit(f"GraphQL error: {data['errors']}")
u = data["data"]["user"]
cal = u["contributionsCollection"]["contributionCalendar"]
days = sorted(
    (d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]
)
counts = dict(days)

today = date.today()
cur, d = 0, today if counts.get(today.isoformat(), 0) else today - timedelta(days=1)
while counts.get(d.isoformat(), 0):
    cur += 1
    d -= timedelta(days=1)

best = run = 0
for _, c in days:
    run = run + 1 if c else 0
    best = max(best, run)

since = u["createdAt"][:4]
stats = [
    (str(cal["totalContributions"]), "Contributions", "last 12 months"),
    (str(cur), "Current streak", "day" if cur == 1 else "days"),
    (str(best), "Longest streak", "last 12 months"),
    (str(u["repositories"]["totalCount"]), "Public repos", f"member since {since}"),
]

W, H, pad = 760, 150, 24
cw = (W - pad * 2) / len(stats)
cells = []
for i, (num, label, sub) in enumerate(stats):
    cx = pad + cw * i + cw / 2
    if i:
        cells.append(f'<line x1="{pad + cw * i:.0f}" y1="36" x2="{pad + cw * i:.0f}" y2="114" stroke="#1E293B"/>')
    cells.append(
        f'<text x="{cx:.0f}" y="70" class="n">{num}</text>'
        f'<text x="{cx:.0f}" y="94" class="l">{label}</text>'
        f'<text x="{cx:.0f}" y="112" class="s">{sub}</text>'
    )

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub statistics for {USER}">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2563EB"/><stop offset="1" stop-color="#22D3EE"/></linearGradient></defs>
  <style>
    text{{font-family:'Segoe UI',-apple-system,Helvetica,Arial,sans-serif;text-anchor:middle}}
    .n{{font-size:34px;font-weight:700;fill:#F8FAFC}}
    .l{{font-size:14px;font-weight:600;fill:#22D3EE}}
    .s{{font-size:12px;fill:#94A3B8}}
  </style>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="#080F1C" stroke="#1E293B"/>
  <rect x="{pad}" y="0" width="64" height="3" rx="1.5" fill="url(#g)"/>
  {''.join(cells)}
  <text x="{W / 2:.0f}" y="138" class="s" style="font-size:11px">Verified GitHub data · updated {today.isoformat()}</text>
</svg>
"""
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
print("wrote", OUT, {s[1]: s[0] for s in stats})
