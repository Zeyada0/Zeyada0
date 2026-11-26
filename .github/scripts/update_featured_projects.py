#!/usr/bin/env python3
"""Rebuild the Featured Projects table in README.md.

Rule: a public, non-fork, non-archived repo owned by OWNER appears in the
table iff it has the 'featured-project' topic. Known projects keep their
curated title / summary / tools from PROJECTS (and PROJECTS order). Any new
repo with the topic gets a generated row appended after the known ones.

Rows live between <!-- FEATURED-PROJECTS:START --> and
<!-- FEATURED-PROJECTS:END --> in README.md. If the markers or the API are
unavailable, the README is left untouched.
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

OWNER = "Zeyada0"
TOPIC = "featured-project"
README = "README.md"
START = "<!-- FEATURED-PROJECTS:START -->"
END = "<!-- FEATURED-PROJECTS:END -->"

# repo name -> (display title, what it shows, tools). Order = table order.
PROJECTS = {
    "sallah-call-center-dashboard": (
        "Salla Call Center Dashboard",
        "Call-center performance, agent analysis and volume forecasting",
        "Power BI, DAX",
    ),
    "hyper-market-sales-dashboard": (
        "Hyper Market Sales Dashboard",
        "Sales, profit, returns, customers and stores across 5 report pages",
        "Power BI, Power Query",
    ),
    "service-insight-suite": (
        "Service Insight Suite",
        "Revenue, hours, clients, departments and efficiency",
        "Power BI, DAX",
    ),
    "baladna-supply-chain-dashboard": (
        "Baladna Supply Chain Dashboard",
        "Weekly production vs distribution across regions and categories",
        "Power BI, Power Query",
    ),
    "adidas-sales-dashboard": (
        "Adidas Sales Dashboard",
        "Sales overview and product analysis",
        "Power BI, DAX",
    ),
}


def fetch_repos():
    fixture = os.environ.get("FEATURED_PROJECTS_FIXTURE")
    if fixture:
        with open(fixture, encoding="utf-8") as f:
            return json.load(f)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "featured-projects-workflow",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    url = (
        "https://api.github.com/users/" + OWNER
        + "/repos?per_page=100&type=public&sort=created&direction=asc"
    )
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as exc:  # noqa: BLE001 - leave README untouched on API trouble
            print("GitHub API attempt %d failed: %s" % (attempt + 1, exc), file=sys.stderr)
            time.sleep(5)
    return None


TOOL_NAMES = {
    "power-bi": "Power BI",
    "dax": "DAX",
    "sql": "SQL",
    "excel": "Excel",
    "tableau": "Tableau",
    "power-query": "Power Query",
    "python": "Python",
}


def esc(text):
    return html.escape(text, quote=False)


def row_for(repo):
    name = repo["name"]
    url = repo["html_url"]
    if name in PROJECTS:
        title, desc, tools = PROJECTS[name]
    else:
        title = re.sub(r"[-_]+", " ", name).strip().title()
        desc = repo.get("description") or "Data analysis project"
        extra = [t for t in (repo.get("topics") or []) if t != TOPIC]
        tools = ", ".join(TOOL_NAMES.get(t, t.replace("-", " ").title()) for t in extra) or (repo.get("language") or "-")
    return (
        '  <tr><td><a href="' + url + '"><strong>' + esc(title) + "</strong></a></td><td>"
        + esc(desc) + "</td><td>" + esc(tools) + "</td></tr>"
    )


def main():
    repos = fetch_repos()
    if repos is None:
        print("Could not fetch repository list; leaving README unchanged.")
        return 0
    featured = [
        r for r in repos
        if not r.get("fork") and not r.get("archived") and TOPIC in (r.get("topics") or [])
    ]
    known = [r for name in PROJECTS for r in featured if r["name"] == name]
    new = sorted(
        (r for r in featured if r["name"] not in PROJECTS),
        key=lambda r: r.get("created_at") or "",
    )
    rows = [row_for(r) for r in known + new]
    block = START + "\n" + "\n".join(rows) + "\n  " + END

    with open(README, encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        print("Markers not found in README.md; leaving it unchanged.", file=sys.stderr)
        return 1
    updated = pattern.sub(lambda _m: block, text, count=1)
    if updated != text:
        with open(README, "w", encoding="utf-8", newline="\n") as f:
            f.write(updated)
        print("README.md updated: %d featured project row(s)." % len(rows))
    else:
        print("README.md already up to date: %d featured project row(s)." % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
