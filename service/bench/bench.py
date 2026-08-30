#!/usr/bin/env python3
"""Measure what the caching and indexing decisions in this service actually buy.

Three experiments, run against a live instance:

  latency  - server-side mean time per endpoint, cache on vs off
  queries  - SELECTs issued per request, per chain depth (needs cache off)
  index    - EXPLAIN ANALYZE for the chain query under three index choices

On why latency is read from the server rather than timed at the client: a
request to /actuator/health, which does almost no work, costs ~25 ms measured
from a Python client over Windows loopback. That floor is larger than every
difference worth reporting, so client-side percentiles here would be measuring
the loopback, not the service. Micrometer's http.server.requests counts time
inside the server, so the numbers below reflect the handler.

    python bench/bench.py --experiment latency --n 300
    python bench/bench.py --experiment queries
    python bench/bench.py --experiment index
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Courses chosen to span the shape of the graph: a deep upper-division chain,
# a mid-depth one, and a lower-division course with a shallow tree.
CHAIN_CODES = ["CSE 101", "CSE 141", "MATH 20C"]
DEPTHS = [1, 3, 6, 12]

# Micrometer reports one timer per URI template, not per concrete path.
TRACKED_URIS = [
    "/api/courses/{code}/chain",
    "/api/courses/{code}",
    "/api/courses",
    "/api/graph",
    "/actuator/health",
]


def get(url: str, timeout: float = 60.0) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def timer(base: str, uri: str) -> tuple[float, float]:
    """(count, total_seconds) for one URI template."""
    q = urllib.parse.urlencode({"tag": f"uri:{uri}"})
    status, body = get(f"{base}/actuator/metrics/http.server.requests?{q}")
    if status != 200:
        return 0.0, 0.0
    m = {x["statistic"]: x["value"] for x in json.loads(body).get("measurements", [])}
    return m.get("COUNT", 0.0), m.get("TOTAL_TIME", 0.0)


def snapshot(base: str) -> dict[str, tuple[float, float]]:
    return {u: timer(base, u) for u in TRACKED_URIS}


def mysql(container: str, sql: str, table: bool = False) -> str:
    flags = ["-t"] if table else ["-N", "-B"]
    out = subprocess.run(
        ["docker", "exec", container, "mysql", "-uroot", "-proot", *flags, "-e", sql],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return out.stdout.strip()


def selects(container: str) -> int:
    return int(mysql(container, "SHOW GLOBAL STATUS LIKE 'Com_select'").split("\t")[1])


def wait_ready(base: str, seconds: int = 180) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        status, _ = get(f"{base}/actuator/health", timeout=3)
        if status == 200:
            return
        time.sleep(1)
    raise SystemExit(f"service at {base} never became healthy")


def paths_for_load() -> list[str]:
    out = [f"/api/courses/{c.replace(' ', '%20')}/chain?depth=6" for c in CHAIN_CODES]
    out += ["/api/courses/CSE%20101", "/api/courses?q=data&limit=25", "/api/graph"]
    return out


def exp_latency(base: str, n: int, warmup: int) -> list[dict]:
    paths = paths_for_load()
    for _ in range(warmup):
        for p in paths:
            get(f"{base}{p}")
    before = snapshot(base)
    for _ in range(n):
        for p in paths:
            get(f"{base}{p}")
    after = snapshot(base)

    rows = []
    for uri in TRACKED_URIS:
        c0, t0 = before[uri]
        c1, t1 = after[uri]
        dc, dt = c1 - c0, t1 - t0
        if dc <= 0:
            continue
        rows.append({"uri": uri, "requests": int(dc), "mean_ms": 1000.0 * dt / dc})
    return rows


def exp_queries(base: str, container: str) -> list[dict]:
    rows = []
    for code in CHAIN_CODES:
        for depth in DEPTHS:
            path = f"/api/courses/{code.replace(' ', '%20')}/chain?depth={depth}"
            get(f"{base}{path}")
            before = selects(container)
            status, body = get(f"{base}{path}")
            after = selects(container)
            doc = json.loads(body)
            rows.append(
                {
                    "code": code,
                    "depth": depth,
                    "status": status,
                    "selects": after - before,
                    "nodes": len(doc.get("nodes", [])),
                    "edges": len(doc.get("edges", [])),
                    "truncated": doc.get("truncated"),
                }
            )
    return rows


INDEX_QUERY = (
    "SELECT * FROM prereq.prereqs {hint} WHERE course_code IN "
    "('CSE 101','CSE 100','CSE 12','CSE 21') AND prereq_type='AND'"
)

INDEX_VARIANTS = [
    ("optimizer choice", ""),
    ("force composite", "FORCE INDEX (ix_prereqs_course_type_group)"),
    ("no index", "IGNORE INDEX (ix_prereqs_course_code, ix_prereqs_course_type_group)"),
]


def exp_index(container: str, reps: int = 7) -> list[dict]:
    rows = []
    for label, hint in INDEX_VARIANTS:
        sql = INDEX_QUERY.format(hint=hint)
        times, chosen, scan = [], None, None
        for _ in range(reps):
            out = mysql(container, f"EXPLAIN ANALYZE {sql}")
            for part in out.replace("\\n", "\n").splitlines():
                if "actual time=" in part:
                    tail = part.split("actual time=")[1].split(")")[0]
                    times.append(float(tail.split("..")[1].split(" ")[0]))
                    break
            if chosen is None:
                plan = mysql(container, f"EXPLAIN {sql}")
                cols = plan.split("\t")
                chosen = cols[6] if len(cols) > 6 else "?"
                scan = cols[4] if len(cols) > 4 else "?"
        rows.append(
            {
                "variant": label,
                "key_used": chosen,
                "access_type": scan,
                "best_ms": min(times) if times else None,
                "median_ms": sorted(times)[len(times) // 2] if times else None,
            }
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8080")
    ap.add_argument("--mysql-container", default="pd-mysql")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--warmup", type=int, default=50)
    ap.add_argument("--experiment", choices=["latency", "queries", "index"], required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if args.experiment != "index":
        wait_ready(args.base_url)

    if args.experiment == "latency":
        rows = exp_latency(args.base_url, args.n, args.warmup)
    elif args.experiment == "queries":
        rows = exp_queries(args.base_url, args.mysql_container)
    else:
        rows = exp_index(args.mysql_container)

    text = json.dumps({"experiment": args.experiment, "label": args.label, "rows": rows}, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


if __name__ == "__main__":
    sys.exit(main())
