"""Builds the README figures of harness-ai, light and dark, in the design language of the skills map.

Run from the repository root: python3 docs/assets/readme/build.py docs/assets/readme. Standard library only.
The terminal of the hero quotes `harness.py status . --map` on this repository, lines cut with "…": rerun it
and update the lines if the output changes. The SVGs are shown through <img>, so
they load no font and run no script: system fonts, CSS animation only, reduced motion respected.
"""
from __future__ import annotations

import os
import sys
from html import escape

SANS = "'IBM Plex Sans', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
HEAD = "'IBM Plex Sans Condensed', 'IBM Plex Sans', -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

THEMES = {
    "light": dict(
        bg="#f3f6f8", surface="#ffffff", sunken="#e8edf1", ink="#15202b", muted="#536271", rule="#cfd8df",
        accent="#0f5777", accent_soft="#dcebf2", mid="#4f93b1", glow="#bfe0ee",
        l1="#e3eef3", l1_ink="#15202b", l2="#bcd9e6", l2_ink="#15202b", l3="#4f93b1", l3_ink="#ffffff",
        l4="#0f5777", l4_ink="#ffffff",
        sdlc="#7a5200", sdlc_soft="#f6ecd2", sdlc_edge="#e2c98a", never="#8a3b2e",
        bronze=("#e2a676", "#9a5b2a", "#6b3c17"), silver=("#e9eef2", "#9aa7b2", "#5f6c77"),
        gold=("#f7dc7a", "#c59a17", "#86650a"), platinum=("#d6eef6", "#6fa9be", "#2f6477"),
        term_bg="#0e151b", term_ink="#e3eaf0", term_muted="#8fa1ae", term_ok="#7bd1a2", term_acc="#74b9d8",
        guard="#15202b", guard_ink="#ffffff", guard_acc="#f0c66a",
    ),
    "dark": dict(
        bg="#0e151b", surface="#151f28", sunken="#1b2731", ink="#e3eaf0", muted="#9dadb9", rule="#2b3946",
        accent="#74b9d8", accent_soft="#173447", mid="#3c86a8", glow="#123247",
        l1="#1b2a35", l1_ink="#e3eaf0", l2="#1d3c50", l2_ink="#e3eaf0", l3="#2f6f8f", l3_ink="#ffffff",
        l4="#74b9d8", l4_ink="#08161e",
        sdlc="#e1b55c", sdlc_soft="#33280f", sdlc_edge="#6b5420", never="#f08f7c",
        bronze=("#f0b07e", "#c47a40", "#7d4a20"), silver=("#f2f6f9", "#b5c1cb", "#6f7c87"),
        gold=("#ffe58f", "#e0bc4c", "#9b7a13"), platinum=("#e3f5fb", "#8cc5da", "#3d7a90"),
        term_bg="#070c10", term_ink="#e3eaf0", term_muted="#8fa1ae", term_ok="#7bd1a2", term_acc="#74b9d8",
        guard="#e3eaf0", guard_ink="#0e151b", guard_acc="#9b6a00",
    ),
}

MOTION = """
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
  .rise { animation: rise .7s cubic-bezier(.16,1,.3,1) backwards; }
  @keyframes rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
"""


def t(x, y, s, size, fill, family=SANS, weight=400, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>{escape(s)}</text>')


def svg(w, h, title, desc, body, style=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d">\n<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n'
            f'<style>{MOTION}{style}</style>\n{body}\n</svg>\n')


def delay(i, step=0.12, start=0.1):
    return f'class="rise" style="animation-delay:{start + i * step:.2f}s"'


# ---------------------------------------------------------------- hero
def hero(c):
    w, h = 1280, 440
    b = [f'<rect width="{w}" height="{h}" rx="18" fill="{c["bg"]}"/>',
         '<defs>',
         f'<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{c["rule"]}" stroke-width="1" opacity=".45"/></pattern>',
         f'<radialGradient id="glow" cx="78%" cy="40%" r="60%"><stop offset="0" stop-color="{c["glow"]}" stop-opacity=".9"/><stop offset="1" stop-color="{c["bg"]}" stop-opacity="0"/></radialGradient>',
         f'<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{c["bg"]}"/><stop offset=".55" stop-color="{c["bg"]}" stop-opacity=".4"/><stop offset="1" stop-color="{c["bg"]}" stop-opacity="0"/></linearGradient>',
         '<clipPath id="card"><rect width="1280" height="440" rx="18"/></clipPath>',
         '</defs>',
         '<g clip-path="url(#card)">',
         f'<rect width="{w}" height="{h}" fill="url(#grid)"/>',
         f'<rect width="{w}" height="{h}" fill="url(#fade)"/>',
         f'<rect width="{w}" height="{h}" fill="url(#glow)"/>',
         '</g>',
         f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="{c["rule"]}"/>']
    x = 64
    b.append(f'<g {delay(0)}>' + t(x, 78, "CLAUDE CODE PLUGIN MARKETPLACE  ·  ZERO-DEPENDENCY PYTHON CLI", 14, c["muted"], MONO,
                                    extra='letter-spacing="1.6"') + '</g>')
    b.append(f'<g {delay(1)}><text x="{x - 4}" y="168" font-family="{MONO}" font-size="92" font-weight="500" '
             f'fill="{c["ink"]}" letter-spacing="-2">harness-ai<tspan class="cursor" fill="{c["accent"]}">_</tspan></text></g>')
    for i, line in enumerate(("Get a repository ready for AI coding agents,",
                              "measure where it stands, and level it up",
                              "one step at a time.")):
        b.append(f'<g {delay(2)}>' + t(x, 222 + i * 30, line, 22, c["ink"]) + '</g>')
    chips = (("The prompt explains.", 196, c["accent_soft"], c["accent"]),
             ("The code checks.", 164, c["mid"], "#ffffff"),
             ("The pipeline executes.", 214, c["accent"] if c is THEMES["light"] else c["l4"], "#ffffff" if c is THEMES["light"] else c["l4_ink"]))
    cx = x
    for i, (label, width, fill, ink) in enumerate(chips):
        b.append(f'<g {delay(3 + i, 0.18)}><rect x="{cx}" y="332" width="{width}" height="40" rx="8" fill="{fill}"/>'
                 + t(cx + width / 2, 358, label, 17, ink, HEAD, 600, "middle") + '</g>')
        cx += width + 10
    stats = "2 plugins  ·  16 skills  ·  5 levels  ·  2 tested CLIs  ·  0 dependencies"
    b.append(f'<g {delay(6)}>' + t(x, 406, stats, 15, c["muted"], MONO) + '</g>')

    # terminal card: real output of `harness.py status . --map` on this repository, lines shortened with …
    tx, ty, tw, th = 700, 92, 520, 288
    lines = [
        ("$ ", c["term_acc"], "python3 cli/harness.py status . --map", c["term_ink"]),
        ("", None, "Where this repository stands, level by level:", c["term_muted"]),
        ("✓ ", c["term_ok"], "1 Framed     the agent knows…", c["term_ink"]),
        ("· ", c["term_muted"], "2 Looped     review remarks become…", c["term_muted"]),
        ("· ", c["term_muted"], "3 Verified   mandatory rules are…", c["term_muted"]),
        ("· ", c["term_muted"], "4 Delegated  whole tasks go to…", c["term_muted"]),
        ("", None, "", c["term_ink"]),
        ("", None, "Target: none chosen yet. You decide how", c["term_ink"]),
        ("", None, "far to go; you can stay at any level.", c["term_ink"]),
    ]
    b.append(f'<g {delay(4, start=0.3)}>')
    b.append(f'<rect x="{tx + 6}" y="{ty + 10}" width="{tw}" height="{th}" rx="14" fill="{c["accent"]}" opacity=".18"/>')
    b.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="14" fill="{c["term_bg"]}"/>')
    for i, dot in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        b.append(f'<circle cx="{tx + 22 + i * 18}" cy="{ty + 20}" r="5.5" fill="{dot}"/>')
    b.append(t(tx + tw / 2, ty + 25, "your-repo — harness status", 12, c["term_muted"], MONO, anchor="middle"))
    b.append(f'<line x1="{tx}" x2="{tx + tw}" y1="{ty + 38}" y2="{ty + 38}" stroke="#ffffff" stroke-opacity=".08"/>')
    for i, (lead, lead_ink, text, ink) in enumerate(lines):
        y = ty + 66 + i * 24
        if lead:
            b.append(t(tx + 22, y, lead, 14, lead_ink, MONO, 600))
        b.append(t(tx + 22 + (len(lead) and 16), y, text, 14, ink, MONO, extra='xml:space="preserve" style="white-space:pre"'))
    here_y = ty + 66 + 2 * 24
    b.append(f'<g class="here"><rect x="{tx + 382}" y="{here_y - 15}" width="122" height="21" rx="10.5" fill="{c["term_ok"]}" opacity=".16"/>'
             + t(tx + 443, here_y, "← you are here", 12, c["term_ok"], MONO, 600, "middle") + '</g>')
    b.append('</g>')
    style = """
  .cursor { animation: blink 1.1s steps(1) infinite; }
  @keyframes blink { 50% { opacity: 0; } }
  .here { animation: pulse 2.4s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: .55; } }
"""
    return svg(w, h, "harness-ai",
               "harness-ai: Claude Code skills and a zero-dependency Python CLI. The prompt explains, the code checks, "
               "the pipeline executes. A terminal shows harness status --map placing this repository at level 1, Framed.",
               "\n".join(b), style)


# ---------------------------------------------------------------- four layers
def layers(c):
    w = 1280
    bands = (
        ("L1 Judgment", "the agent", "Choose between open options, talk with the human", "The agent, its sub-agents", c["l1"], c["l1_ink"]),
        ("L2 Procedure", "the prompt explains", "Tell the order, when to call what, how to read a result", "Skills, AGENTS.md", c["l2"], c["l2_ink"]),
        ("L3 Local logic", "the code checks", "Guarantee: preconditions, computations, idempotence", "Tested CLI, linters, arch. tests", c["l3"], c["l3_ink"]),
        ("L4 Remote execution", "the pipeline executes", "Act with rights on shared resources", "CI, pipelines", c["l4"], c["l4_ink"]),
    )
    gaps = ("follows", "calls, never re-implements", "the same checks run again in")
    bh, gap, top = 92, 38, 24
    h = top * 2 + len(bands) * bh + (len(bands) - 1) * gap
    b = [f'<rect width="{w}" height="{h}" rx="18" fill="{c["bg"]}"/>',
         f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="{c["rule"]}"/>']
    for i, (name, sub, role, carried, fill, ink) in enumerate(bands):
        y = top + i * (bh + gap)
        inset = 40 + (3 - i) * 0
        b.append(f'<g {delay(i, 0.15)}>')
        b.append(f'<rect x="{inset}" y="{y}" width="{w - 2 * inset}" height="{bh}" rx="12" fill="{fill}"/>')
        b.append(t(inset + 32, y + 44, name, 26, ink, HEAD, 600))
        b.append(t(inset + 32, y + 70, sub, 15, ink, MONO, extra='opacity=".8" letter-spacing=".4"'))
        b.append(t(inset + 340, y + 54, role, 20, ink))
        b.append(f'<rect x="{w - inset - 316}" y="{y + 30}" width="292" height="32" rx="7" fill="{ink}" opacity=".09"/>')
        b.append(t(w - inset - 170, y + 52, carried, 15, ink, MONO, 500, "middle"))
        b.append('</g>')
        if i < len(gaps):
            gy = y + bh + gap / 2
            b.append(f'<g {delay(i + 0.5, 0.15)}><path d="M120 {gy - 12}v20m-6-7l6 7 6-7" fill="none" stroke="{c["muted"]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
                     + t(140, gy + 6, gaps[i], 16, c["muted"], MONO) + '</g>')
    return svg(w, h, "Four layers",
               "L1 Judgment, the agent: choose between open options and talk with the human. L2 Procedure, the prompt "
               "explains: skills and AGENTS.md. L3 Local logic, the code checks: tested CLI, linters, architecture tests. "
               "L4 Remote execution, the pipeline executes: CI and pipelines.", "\n".join(b))


# ---------------------------------------------------------------- five levels
def medal(c, cx, cy, kind, r=24, idx=0):
    if kind is None:
        return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c["muted"]}" stroke-width="2" stroke-dasharray="4 5"/>')
    hi, mid, lo = c[kind]
    gid = f"m{kind}"
    return (f'<defs><radialGradient id="{gid}" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="{hi}"/>'
            f'<stop offset=".55" stop-color="{mid}"/><stop offset="1" stop-color="{lo}"/></radialGradient>'
            f'<clipPath id="c{gid}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath></defs>'
            f'<path d="M{cx - 16} {cy - r - 18}l7 18h18l7-18z" fill="{mid}" opacity=".55"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{gid})"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r - 6}" fill="none" stroke="{hi}" stroke-opacity=".7" stroke-width="1.5"/>'
            f'<g clip-path="url(#c{gid})"><rect class="shine" style="animation-delay:{1.2 + idx * 0.35:.2f}s" x="{cx - r - 30}" y="{cy - r - 10}" width="14" height="{2 * r + 20}" fill="#ffffff" opacity=".55" transform="rotate(20 {cx} {cy})"/></g>')


def levels(c):
    w, h = 1280, 520
    steps = (
        (0, "None", None, "no medal", ("The agent starts from", "zero at every session.")),
        (1, "Framed", "bronze", "bronze", ("A short AGENTS.md, a mode,", "a Forbidden section.")),
        (2, "Looped", "silver", "silver", ("rule: in reviews, a harvest", "that finds a real signal.")),
        (3, "Verified", "gold", "gold", ("Rules held by tools, a CI,", "an audit with no P1 left.")),
        (4, "Delegated", "platinum", "platinum", ("Task contracts, agent PRs", "that come back clean.")),
    )
    b = [f'<rect width="{w}" height="{h}" rx="18" fill="{c["bg"]}"/>',
         f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="{c["rule"]}"/>']
    base, cw, gap, x0 = 488, 224, 18, 40
    tops = [290, 240, 190, 140, 90]
    b.append(t(x0, 52, "EVERY LEVEL IS MEASURED, NEVER DECLARED  ·  EVERY LEVEL IS A PLACE YOU CAN STAY", 15,
               c["muted"], MONO, extra='letter-spacing="1.2"'))
    for i, (n, name, kind, label, earn) in enumerate(steps):
        x, top = x0 + i * (cw + gap), tops[i]
        col = c[kind][1] if kind else c["muted"]
        gid = f"col{i}"
        b.append(f'<g {delay(i, 0.14)}>')
        b.append(f'<defs><linearGradient id="{gid}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{col}" stop-opacity=".22"/>'
                 f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient></defs>')
        b.append(f'<rect x="{x}" y="{top}" width="{cw}" height="{base - top}" rx="12" fill="{c["surface"]}" stroke="{c["rule"]}"/>')
        b.append(f'<rect x="{x}" y="{top}" width="{cw}" height="{base - top}" rx="12" fill="url(#{gid})"/>')
        b.append(f'<rect x="{x}" y="{top}" width="{cw}" height="5" rx="2.5" fill="{col}"/>')
        b.append(t(x + 20, top + 36, f"level {n}", 15, c["muted"], MONO))
        b.append(medal(c, x + cw - 42, top + 50, kind, 20, i))
        b.append(t(x + 20, top + 88, name, 27, c["ink"], HEAD, 600))
        b.append(t(x + 20, top + 114, label, 15, col, MONO, 600, extra='letter-spacing=".6"'))
        for j, line in enumerate(earn):
            b.append(t(x + 20, top + 148 + j * 23, line, 16, c["ink"]))
        b.append('</g>')
    # rising arrow over the tops
    pts = " ".join(f"{x0 + i * (cw + gap) + cw / 2},{tops[i] - 22}" for i in range(5))
    b.append(f'<polyline class="trail" points="{pts}" fill="none" stroke="{c["accent"]}" stroke-width="2" stroke-dasharray="2 7" stroke-linecap="round" opacity=".7"/>')
    style = """
  .shine { animation: shine 4.2s ease-in-out infinite; transform-box: fill-box; }
  @keyframes shine { 0%, 70% { transform: translateX(0) rotate(20deg); } 100% { transform: translateX(90px) rotate(20deg); } }
  .trail { animation: march 1.6s linear infinite; }
  @keyframes march { to { stroke-dashoffset: -18; } }
"""
    return svg(w, h, "Five levels",
               "Five levels measured by harness status: 0 None, no medal; 1 Framed, bronze; 2 Looped, silver; "
               "3 Verified, gold; 4 Delegated, platinum. Every level is a place you can stay.", "\n".join(b), style)


# ---------------------------------------------------------------- ticket to production
def sdlc(c):
    w, h = 1280, 640
    b = [f'<rect width="{w}" height="{h}" rx="18" fill="{c["bg"]}"/>',
         f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="{c["rule"]}"/>',
         '<defs>',
         f'<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{c["muted"]}"/></marker>',
         '</defs>']
    cw, ch, gx = 216, 158, 28
    xs = [40 + i * (cw + gx) for i in range(5)]
    y1, y2 = 40, 290

    def card(x, y, name, level, does, never, i):
        out = [f'<g {delay(i, 0.1)}>',
               f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="12" fill="{c["sdlc_soft"]}" stroke="{c["sdlc_edge"]}"/>',
               t(x + 18, y + 34, name, 20, c["sdlc"], MONO, 600)]
        if level:
            out.append(f'<rect x="{x + cw - 86}" y="{y + 17}" width="70" height="24" rx="12" fill="{c["sdlc"]}" opacity=".14"/>')
            out.append(t(x + cw - 51, y + 34, level, 13, c["sdlc"], MONO, 600, "middle"))
        for j, line in enumerate(does):
            out.append(t(x + 18, y + 64 + j * 21, line, 16, c["ink"]))
        out.append(f'<line x1="{x + 18}" x2="{x + cw - 18}" y1="{y + 106}" y2="{y + 106}" stroke="{c["sdlc_edge"]}" stroke-dasharray="3 4"/>')
        for j, line in enumerate(never):
            out.append(t(x + 18, y + 128 + j * 19, line, 14.5, c["never"], SANS, 500, extra='font-style="italic"'))
        out.append('</g>')
        return out

    row1 = (
        ("ticket", "level 1+", ("Is the ticket ready?", "What does it lack?"), ("✕ never edits the ticket", "  without agreement")),
        ("dev", "level 1+", ("Plan, code, checks, a PR", "on the path its size needs"), ("✕ never approves", "  or merges")),
        ("qa", "level 3+", ("Tests derived from the", "acceptance criteria"), ("✕ never disables or", "  weakens a test")),
        ("secu", "level 1+", ("Secrets, scanners, the", "sensitive places to reread"), ("✕ never declares", "  a change safe")),
        ("review", "level 1+", ("Few comments, each on", "a line of the diff"), ("✕ never approves", "  or merges")),
    )
    for i, (name, level, does, never) in enumerate(row1):
        b += card(xs[i], y1, name, level, does, never, i)
        if i < 4:
            b.append(f'<line x1="{xs[i] + cw + 3}" x2="{xs[i + 1] - 4}" y1="{y1 + ch / 2}" y2="{y1 + ch / 2}" stroke="{c["muted"]}" stroke-width="2" marker-end="url(#ah)"/>')
    # review -> CI
    b.append(f'<line x1="{xs[4] + cw / 2}" x2="{xs[4] + cw / 2}" y1="{y1 + ch + 3}" y2="{y2 - 4}" stroke="{c["muted"]}" stroke-width="2" marker-end="url(#ah)"/>')

    def gate(x, y, title, lines, i, human=False):
        out = [f'<g {delay(5 + i, 0.1)}>']
        if human:
            out.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="{ch / 2 if False else 28}" fill="{c["surface"]}" stroke="{c["rule"]}" stroke-width="1.5"/>')
            hx, hy = x + 30, y + 30
            out.append(f'<circle cx="{hx}" cy="{hy}" r="7" fill="{c["accent"]}"/><path d="M{hx - 12} {hy + 22}a12 11 0 0 1 24 0z" fill="{c["accent"]}"/>')
            out.append(t(x + 52, y + 40, title, 19, c["ink"], HEAD, 600))
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="12" fill="{c["sunken"]}" stroke="{c["muted"]}" stroke-width="1.5" stroke-dasharray="6 5"/>')
            out.append(t(x + 18, y + 36, title, 19, c["ink"], MONO, 600))
        for j, line in enumerate(lines):
            out.append(t(x + 18, y + 74 + j * 21, line, 16, c["ink"]))
        out.append('</g>')
        return out

    b += gate(xs[4], y2, "CI · ci pr", ("Security and test gates,", "settings read on the", "target branch. A failed", "gate blocks the merge."), 0)
    b += gate(xs[3], y2, "merge", ("Done by a human.", "No phase approves", "or merges."), 1, True)
    b += card(xs[2], y2, "ship", "level 3+", ("Prerequisites, version,", "notes, the team's steps"), ("✕ never tags, publishes", "  or deploys"), 7)
    b += gate(xs[1], y2, "production", ("Delivered by a human", "or by a pipeline."), 3, True)
    b += card(xs[0], y2, "run", "level 2+", ("Investigates an incident,", "writes the ticket"), ("✕ never restarts, rolls", "  back or changes a thing"), 9)
    for i in (4, 3, 2):
        b.append(f'<line x1="{xs[i] - 3}" x2="{xs[i - 1] + cw + 4}" y1="{y2 + ch / 2}" y2="{y2 + ch / 2}" stroke="{c["muted"]}" stroke-width="2" marker-end="url(#ah)"/>')
    # production -> run (incident), run -> ticket (new ticket)
    b.append(f'<line x1="{xs[1] - 3}" x2="{xs[0] + cw + 4}" y1="{y2 + ch / 2}" y2="{y2 + ch / 2}" stroke="{c["muted"]}" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#ah)"/>')
    px = xs[0] + cw + gx / 2
    b.append(f'<rect x="{px - 36}" y="{y2 + ch / 2 + 12}" width="72" height="22" rx="11" fill="{c["bg"]}" stroke="{c["muted"]}"/>')
    b.append(t(px, y2 + ch / 2 + 27, "incident", 12, c["muted"], MONO, anchor="middle"))
    b.append(f'<line x1="{xs[0] + cw / 2}" x2="{xs[0] + cw / 2}" y1="{y2 - 3}" y2="{y1 + ch + 4}" stroke="{c["muted"]}" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#ah)"/>')
    b.append(t(xs[0] + cw / 2 + 10, (y1 + ch + y2) / 2 + 4, "new ticket", 12, c["muted"], MONO))

    # guardrail band
    gy = 488
    b.append(f'<g {delay(11, 0.1)}>')
    for x in (xs[1], xs[2], xs[0]):
        top = y1 + ch if x == xs[1] else y2 + ch
        b.append(f'<line x1="{x + cw / 2}" x2="{x + cw / 2}" y1="{top + 2}" y2="{gy}" stroke="{c["guard_acc"]}" stroke-width="2" stroke-dasharray="2 5" opacity=".9"/>' if x != xs[1] else '')
    b.append(f'<rect x="40" y="{gy}" width="{w - 80}" height="112" rx="14" fill="{c["guard"]}"/>')
    sx, sy = 78, gy + 56
    b.append(f'<path class="shield" d="M{sx} {sy - 30}l26 10v18c0 18-11 30-26 36c-15-6-26-18-26-36v-18z" fill="{c["guard_acc"]}"/>'
             f'<path d="M{sx - 10} {sy + 2}l7 7l14-15" fill="none" stroke="{c["guard"]}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')
    b.append(t(124, gy + 44, "An agent does not deliver.", 24, c["guard_ink"], HEAD, 600))
    b.append(t(124, gy + 74, "A hook reads every shell command of the agent before it runs, and refuses tag, release,", 17, c["guard_ink"],
               extra='opacity=".88"'))
    b.append(t(124, gy + 96, "workflow run, publish and deploy. Against accidents and smuggled instructions; not a sandbox.", 17,
               c["guard_ink"], extra='opacity=".88"'))
    b.append('</g>')
    style = """
  .shield { animation: glint 3.2s ease-in-out infinite; }
  @keyframes glint { 50% { opacity: .7; } }
"""
    return svg(w, h, "From ticket to production",
               "The ai-sdlc phases: ticket, dev, qa, secu and review, then the CI gates, a human merge, ship, and production "
               "delivered by a human or a pipeline; run turns an incident into a new ticket. Each phase states what it never "
               "does, and a guardrail hook refuses tag, release, workflow run, publish and deploy.", "\n".join(b), style)


FIGURES = {"hero": hero, "layers": layers, "levels": levels, "sdlc": sdlc}


def main(out: str) -> None:
    os.makedirs(out, exist_ok=True)
    for name, build in FIGURES.items():
        for theme, colours in THEMES.items():
            with open(os.path.join(out, f"{name}-{theme}.svg"), "w", encoding="utf-8") as fh:
                fh.write(build(colours))


if __name__ == "__main__":
    main(sys.argv[1])
