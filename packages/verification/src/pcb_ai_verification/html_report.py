"""HTML rendering for semantic review reports."""

from __future__ import annotations

import html
from datetime import datetime, timezone

from pcb_ai_circuit_ir.models import Design, ReviewReport


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _severity_class(severity: str) -> str:
    return f"sev-{severity.lower()}"


def render_html_report(report: ReviewReport, design: Design | None = None) -> str:
    """Render a self-contained HTML semantic review report."""
    title = design.name or report.design_id
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    summary = report.summary or {}
    by_severity = summary.get("by_severity", {})

    finding_rows = []
    for finding in report.findings:
        evidence = "".join(
            f"<li><code>{_esc(ref.id)}</code> "
            f"<span class='kind'>{_esc(ref.kind)}</span>"
            + (f" — {_esc(ref.title)}" if ref.title else "")
            + (f" <em>{_esc(ref.excerpt)}</em>" if ref.excerpt else "")
            + "</li>"
            for ref in finding.evidence_refs
        ) or "<li class='muted'>No evidence refs</li>"
        objects = ", ".join(_esc(o) for o in finding.objects) or "—"
        finding_rows.append(
            f"""
            <article class='finding {_esc(_severity_class(finding.severity.value))}' id='finding-{_esc(finding.id)}'>
              <header>
                <span class='badge'>{_esc(finding.severity.value)}</span>
                <code class='rule'>{_esc(finding.rule_id)}</code>
                <span class='source'>{_esc(finding.source)}</span>
              </header>
              <p class='explanation'>{_esc(finding.explanation)}</p>
              <p class='objects'><strong>Objects:</strong> {objects}</p>
              <p class='confidence'><strong>Confidence:</strong> {_esc(f"{finding.confidence:.2f}")}</p>
              <details open>
                <summary>Evidence</summary>
                <ul class='evidence'>{evidence}</ul>
              </details>
            </article>
            """
        )

    fragment_rows = []
    for frag in report.net_fragments:
        endpoints = ", ".join(_esc(e) for e in frag.endpoints) or "—"
        related = ", ".join(
            f"<a href='#finding-{_esc(fid)}'>{_esc(fid[:8])}</a>" for fid in frag.related_finding_ids
        ) or "—"
        fragment_rows.append(
            f"""
            <tr>
              <td><code>{_esc(frag.net_name)}</code></td>
              <td><span class='phase'>{_esc(frag.phase)}</span></td>
              <td>{endpoints}</td>
              <td>{_esc(frag.net_class or "—")}</td>
              <td>{related}</td>
            </tr>
            """
        )

    severity_chips = "".join(
        f"<span class='chip {_esc(_severity_class(k))}'>{_esc(k)}: {_esc(v)}</span>"
        for k, v in by_severity.items()
    ) or "<span class='chip'>No findings</span>"

    design_bits = ""
    if design is not None:
        design_bits = f"""
        <dl class='meta'>
          <dt>Components</dt><dd>{_esc(len(design.components))}</dd>
          <dt>Nets</dt><dd>{_esc(len(design.nets))}</dd>
          <dt>Source</dt><dd>{_esc(design.source_tool.value)} {_esc(design.source_version or "")}</dd>
        </dl>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Review — {_esc(title)}</title>
  <style>
    :root {{
      --bg: #f6f4ef;
      --ink: #1c1b19;
      --muted: #5c574f;
      --card: #fffdf8;
      --line: #d9d2c5;
      --error: #8b1e1e;
      --warning: #8a5a00;
      --info: #1f4b6e;
      --critical: #5a0f0f;
      --accent: #2f5d50;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #ebe4d6 0%, transparent 45%),
        linear-gradient(180deg, #f8f5ee, var(--bg));
      line-height: 1.45;
    }}
    main {{ max-width: 960px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
    h1, h2 {{ font-family: Georgia, "Times New Roman", serif; font-weight: 600; }}
    h1 {{ margin: 0 0 0.25rem; font-size: 2rem; color: var(--accent); }}
    .sub {{ color: var(--muted); margin-bottom: 1.5rem; }}
    section {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 1rem 1.25rem;
      margin-bottom: 1.25rem;
    }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.75rem 0; }}
    .chip, .badge {{
      display: inline-block;
      border-radius: 999px;
      padding: 0.15rem 0.65rem;
      font-size: 0.85rem;
      border: 1px solid var(--line);
      background: #f0ece3;
    }}
    .sev-error, .sev-critical {{ color: var(--error); border-color: #e2b4b4; background: #f8ecec; }}
    .sev-warning {{ color: var(--warning); border-color: #e6d2a6; background: #f8f1e2; }}
    .sev-info {{ color: var(--info); border-color: #b9d0e0; background: #eaf3f8; }}
    .finding {{ border-top: 1px solid var(--line); padding: 1rem 0; }}
    .finding:first-of-type {{ border-top: 0; }}
    .finding header {{ display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }}
    .rule {{ font-size: 0.95rem; }}
    .source {{ color: var(--muted); font-size: 0.85rem; }}
    .muted {{ color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
    th, td {{ text-align: left; padding: 0.55rem 0.4rem; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .phase {{
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--accent);
    }}
    .meta {{ display: grid; grid-template-columns: auto 1fr; gap: 0.25rem 1rem; }}
    .meta dt {{ color: var(--muted); }}
    code {{ font-family: Consolas, "Courier New", monospace; }}
    a {{ color: var(--accent); }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{_esc(title)}</h1>
      <p class="sub">Semantic review · design <code>{_esc(report.design_id)}</code>
        rev {_esc(report.design_revision)} · generated { _esc(generated) }</p>
    </header>

    <section>
      <h2>Summary</h2>
      <p>{_esc(summary.get("finding_count", len(report.findings)))} finding(s)</p>
      <div class="chips">{severity_chips}</div>
      {design_bits}
    </section>

    <section>
      <h2>Findings</h2>
      {"".join(finding_rows) if finding_rows else "<p class='muted'>No findings.</p>"}
    </section>

    <section>
      <h2>Net fragments</h2>
      <p class="muted">Neighborhoods for nets referenced by findings (before/after when operations are applied).</p>
      <table>
        <thead>
          <tr><th>Net</th><th>Phase</th><th>Endpoints</th><th>Class</th><th>Findings</th></tr>
        </thead>
        <tbody>
          {"".join(fragment_rows) if fragment_rows else "<tr><td colspan='5' class='muted'>No related net fragments.</td></tr>"}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""
