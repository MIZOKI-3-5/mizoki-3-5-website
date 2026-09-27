#!/usr/bin/env python3
"""A/B/C test arithmetic — power sizing and the sample-ratio-mismatch check.

Companion tooling for the SITE A/B/C TEST — DESIGN FIX (r1.0) and its
pre-registration (docs/marketing/abtest-preregistration-signal-landing.md).
Stdlib-only on purpose, like the other gate scripts here: deploy runners and
operator laptops need no installs.

Subcommands
-----------
power     Two-proportion sample size (α, power, baseline → lifted rate):
              python3 scripts/abtest_stats.py power --baseline 0.02 --lift-to 0.03
srm       Chi-square goodness-of-fit of arm counts against equal split.
          Counts come inline, or from an exported assignment log:
              python3 scripts/abtest_stats.py srm --counts 1200,1150,1210
              gcloud logging read 'jsonPayload.event="mizoki_abtest" AND \
                jsonPayload.kind="assignment"' --format=json | \
                python3 scripts/abtest_stats.py srm --gcloud-json -
          When SRM fires: STOP, discard the test, fix assignment. Never
          reweight and continue — a reweighted broken assignment produces a
          confident wrong answer, which is worse than no answer (spec §5).
selftest  Seeded checks in both directions (a gate that cannot fire is not a
          gate); run before trusting any verdict from this file.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from statistics import NormalDist

DEFAULT_ARMS = ("a", "b", "c")
SRM_ALPHA = 0.001  # conventional SRM alarm threshold


# --- Chi-square survival function (regularized upper incomplete gamma) ------

def _gamma_series_p(a: float, x: float) -> float:
    """P(a,x) by series expansion (x < a+1)."""
    term = 1.0 / a
    total = term
    n = a
    for _ in range(500):
        n += 1.0
        term *= x / n
        total += term
        if abs(term) < abs(total) * 1e-15:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_contfrac_q(a: float, x: float) -> float:
    """Q(a,x) by continued fraction (x >= a+1); Numerical Recipes gcf."""
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def chi2_sf(x: float, df: int) -> float:
    """P(X² > x) for df degrees of freedom (any df ≥ 1)."""
    if x <= 0:
        return 1.0
    a = df / 2.0
    half = x / 2.0
    if half < a + 1.0:
        return max(0.0, min(1.0, 1.0 - _gamma_series_p(a, half)))
    return max(0.0, min(1.0, _gamma_contfrac_q(a, half)))


def srm_test(counts: dict[str, int]) -> dict:
    arms = sorted(counts)
    values = [counts[a] for a in arms]
    total = sum(values)
    df = len(values) - 1
    if total == 0 or df < 1:
        return {"n": total, "df": df, "chi2": None, "p": None}
    expected = total / len(values)
    chi2 = sum((v - expected) ** 2 / expected for v in values)
    return {"n": total, "df": df, "chi2": chi2, "p": chi2_sf(chi2, df)}


# --- Two-proportion power sizing --------------------------------------------

def n_per_arm(p1: float, p2: float, alpha: float = 0.05,
              power: float = 0.80) -> int:
    """Sample size per arm, two-sided two-proportion z-test."""
    if not (0.0 < p1 < 1.0 and 0.0 < p2 < 1.0) or p1 == p2:
        raise ValueError("rates must be in (0,1) and differ")
    z_a = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    z_b = NormalDist().inv_cdf(power)
    p_bar = (p1 + p2) / 2.0
    num = (z_a * math.sqrt(2.0 * p_bar * (1.0 - p_bar))
           + z_b * math.sqrt(p1 * (1.0 - p1) + p2 * (1.0 - p2))) ** 2
    return math.ceil(num / (p1 - p2) ** 2)


# --- Log ingestion -----------------------------------------------------------

def counts_from_events(lines, arms=DEFAULT_ARMS) -> dict[str, int]:
    """Count non-bot assignment events per arm from JSONL event lines."""
    counts = {a: 0 for a in arms}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        if rec.get("event") != "mizoki_abtest" or rec.get("kind") != "assignment":
            continue
        if rec.get("bot"):
            continue
        variant = rec.get("variant")
        if variant in counts:
            counts[variant] += 1
    return counts


def counts_from_gcloud_json(text: str, arms=DEFAULT_ARMS) -> dict[str, int]:
    """Same, from `gcloud logging read --format=json` (list of entries)."""
    counts = {a: 0 for a in arms}
    entries = json.loads(text)
    for entry in entries if isinstance(entries, list) else []:
        payload = entry.get("jsonPayload") if isinstance(entry, dict) else None
        if not isinstance(payload, dict):
            continue
        if payload.get("event") != "mizoki_abtest":
            continue
        if payload.get("kind") != "assignment" or payload.get("bot"):
            continue
        variant = payload.get("variant")
        if variant in counts:
            counts[variant] += 1
    return counts


# --- CLI ---------------------------------------------------------------------

def cmd_power(args: argparse.Namespace) -> int:
    n = n_per_arm(args.baseline, args.lift_to, args.alpha, args.power)
    print(f"two-proportion test, two-sided alpha={args.alpha}, power={args.power}")
    print(f"baseline {args.baseline:.4f} -> detectable {args.lift_to:.4f}")
    print(f"N per arm : {n:,}")
    print(f"N total   : {n * args.arms:,}  ({args.arms} arms)")
    print("Substitute REAL measured baselines before deciding — an "
          "underpowered test is worse than no test (spec §2/§7).")
    return 0


def cmd_srm(args: argparse.Namespace) -> int:
    if args.counts:
        raw = [int(v) for v in args.counts.split(",")]
        counts = {arm: raw[i] for i, arm in enumerate(DEFAULT_ARMS[: len(raw)])}
    elif args.gcloud_json:
        text = (sys.stdin.read() if args.gcloud_json == "-"
                else open(args.gcloud_json, encoding="utf-8").read())
        counts = counts_from_gcloud_json(text)
    elif args.log:
        with open(args.log, encoding="utf-8") as fh:
            counts = counts_from_events(fh)
    else:
        print("srm: provide --counts, --log FILE, or --gcloud-json FILE|-",
              file=sys.stderr)
        return 2
    result = srm_test(counts)
    print(f"arm counts : {counts}")
    if result["p"] is None:
        print("no assignments counted — nothing to test")
        return 2
    print(f"chi2 = {result['chi2']:.4f}  df = {result['df']}  "
          f"p = {result['p']:.6g}  (alarm threshold p < {args.alpha})")
    if result["p"] < args.alpha:
        print("SRM DETECTED — STOP. Discard the test and fix assignment "
              "(caching, bot filtering, or the assignment path is broken). "
              "Do NOT reweight and continue: every downstream result from "
              "this assignment is invalid.")
        return 1
    print("no sample-ratio mismatch detected at this threshold")
    return 0


def cmd_selftest(_args: argparse.Namespace) -> int:
    """Both-directions seeded checks; refuses a vacuous pass."""
    checks: list[tuple[str, bool]] = []

    # Known chi-square critical values (df, x, expected sf).
    for df, x, expect in ((1, 3.841, 0.05), (2, 5.991, 0.05),
                          (3, 7.815, 0.05), (2, 13.816, 0.001),
                          (4, 9.488, 0.05)):
        got = chi2_sf(x, df)
        checks.append((f"chi2_sf({x}, df={df}) ~= {expect}",
                       abs(got - expect) < 0.0005))
    checks.append(("chi2_sf(0, 2) == 1", chi2_sf(0.0, 2) == 1.0))

    # Power sizing against the spec's illustrative table (its ~3,800 row).
    checks.append(("power 2%->3% in [3700, 3950]",
                   3700 <= n_per_arm(0.02, 0.03) <= 3950))
    checks.append(("power 8%->11% in [1400, 1600]",
                   1400 <= n_per_arm(0.08, 0.11) <= 1600))

    # SRM must FIRE on a seeded broken split and must NOT fire on a fair one.
    broken = srm_test({"a": 1500, "b": 1000, "c": 1000})
    fair = srm_test({"a": 1010, "b": 990, "c": 1000})
    checks.append(("seeded SRM violation fires", broken["p"] < SRM_ALPHA))
    checks.append(("fair split does not fire", fair["p"] > 0.05))

    # Log ingestion: assignments counted, bots and other kinds excluded.
    lines = [
        json.dumps({"event": "mizoki_abtest", "kind": "assignment",
                    "variant": "a", "bot": False}),
        json.dumps({"event": "mizoki_abtest", "kind": "assignment",
                    "variant": "b", "bot": True}),
        json.dumps({"event": "mizoki_abtest", "kind": "exposure",
                    "variant": "c", "bot": False}),
        "not json",
    ]
    counted = counts_from_events(lines)
    checks.append(("log ingestion counts non-bot assignments only",
                   counted == {"a": 1, "b": 0, "c": 0}))

    if not checks:
        print("SELFTEST FAILED — no checks ran (vacuous pass refused)",
              file=sys.stderr)
        return 1
    failures = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'ok' if ok else 'FAIL'}  {name}")
    if failures:
        print(f"SELFTEST FAILED — {len(failures)}/{len(checks)}",
              file=sys.stderr)
        return 1
    print(f"SELFTEST OK — {len(checks)} checks")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_power = sub.add_parser("power", help="two-proportion sample size")
    p_power.add_argument("--baseline", type=float, required=True)
    p_power.add_argument("--lift-to", type=float, required=True)
    p_power.add_argument("--alpha", type=float, default=0.05)
    p_power.add_argument("--power", type=float, default=0.80)
    p_power.add_argument("--arms", type=int, default=3)
    p_power.set_defaults(func=cmd_power)

    p_srm = sub.add_parser("srm", help="sample-ratio-mismatch check")
    p_srm.add_argument("--counts", help="comma-separated a,b,c counts")
    p_srm.add_argument("--log", help="JSONL event-line file")
    p_srm.add_argument("--gcloud-json",
                       help="gcloud logging read --format=json output (or -)")
    p_srm.add_argument("--alpha", type=float, default=SRM_ALPHA)
    p_srm.set_defaults(func=cmd_srm)

    p_self = sub.add_parser("selftest", help="seeded checks, both directions")
    p_self.set_defaults(func=cmd_selftest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
