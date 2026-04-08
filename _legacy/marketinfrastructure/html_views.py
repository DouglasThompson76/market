from __future__ import annotations

import html
import json
from typing import Any
from urllib.parse import urlencode

from .models import CandidateRecord


def render_dashboard(
    *,
    candidates: list[CandidateRecord],
    filters: dict[str, list[str]],
    query: dict[str, str],
) -> str:
    table_rows = "\n".join(render_candidate_row(candidate) for candidate in candidates)
    sort_by = query.get("sort", "")
    sort_dir = query.get("direction", "")
    options_html = "\n".join(
        render_filter_group(
            label=label,
            name=name,
            values=values,
            current=query.get(name, ""),
        )
        for label, name, values in (
            ("Category", "category", filters["categories"]),
            ("Action", "action", filters["actions"]),
            ("Risk", "risk_bucket", filters["risk_buckets"]),
            ("Setup Status", "status", filters["statuses"]),
        )
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MarketInfrastructure Premarket Board</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header class="page-shell">
    <div>
      <p class="eyebrow">MarketInfrastructure</p>
      <h1>Premarket Setup Board</h1>
      <p class="lede">This app ranks premarket candidates from <code>MarketSnapshot_output.csv</code>, validates structure against the 90-day <code>snapshot/</code> history, and prepares the watchlist before the bell. Timing and execution are handled by a separate intraday system after the open.</p>
    </div>
    <nav class="top-nav">
      <a class="active" href="/">Premarket Board</a>
      <span class="disabled">Open Timing (External)</span>
      <span class="disabled">Programmed Exit</span>
      <span class="disabled">Trade Autopsy</span>
    </nav>
  </header>

  <main class="page-shell layout">
    <aside class="sidebar card">
      <h2>Filters</h2>
      <form method="get">
        <label>
          Search
          <input type="text" name="search" value="{html.escape(query.get("search", ""))}" placeholder="Ticker or company">
        </label>
        <input type="hidden" name="sort" value="{html.escape(sort_by)}">
        <input type="hidden" name="direction" value="{html.escape(sort_dir)}">
        {options_html}
        <label>
          Limit
          <input type="number" min="1" max="500" name="limit" value="{html.escape(query.get("limit", "100"))}">
        </label>
        <button type="submit">Apply filters</button>
      </form>
      <section class="card inset">
        <h3>Phase 1 workflow</h3>
        <p>Use this board before 9:30 AM to rank structural setups by resistance, squeeze, blue-sky context, and embedded news sentiment.</p>
        <p class="muted">At the open, hand the best candidates to the separate intraday system for minute-by-minute timing and execution.</p>
      </section>
    </aside>

    <section class="content">
      <section class="card summary-strip">
        <div>
          <span class="summary-label">Candidates</span>
          <strong>{len(candidates)}</strong>
        </div>
        <div>
          <span class="summary-label">Mission</span>
          <strong>Find the strongest premarket setups. Do not treat this screen as a live trigger confirmation tool.</strong>
        </div>
      </section>

      <section class="card">
        <table>
          <thead>
            <tr>
              {render_sortable_header("Symbol", "symbol", query)}
              {render_sortable_header("Price", "price", query)}
              {render_sortable_header("Priority", "priority", query)}
              {render_sortable_header("Setup", "setup", query)}
              {render_sortable_header("GNN", "gnn", query)}
              {render_sortable_header("Pattern", "pattern", query)}
              {render_sortable_header("News", "news", query)}
              {render_sortable_header("Pink Line", "pink_line", query)}
              {render_sortable_header("Squeeze", "squeeze", query)}
              {render_sortable_header("Blue Sky", "blue_sky", query)}
              {render_sortable_header("Risk", "risk", query)}
            </tr>
          </thead>
          <tbody>
            {table_rows}
          </tbody>
        </table>
      </section>
    </section>
  </main>
</body>
</html>
"""


def render_candidate_row(candidate: CandidateRecord) -> str:
    detail_href = (
        f"/symbol/{html.escape(candidate.symbol)}?"
        + urlencode({"trade_date": candidate.trade_date.isoformat()})
    )
    narrative = candidate.narrative_context
    news_value = narrative_summary(candidate)
    return f"""<tr>
  <td>
    <a href="{detail_href}">{html.escape(candidate.symbol)}</a>
    <div class="muted">{html.escape(candidate.company_name or "")}</div>
  </td>
  <td>{format_number(candidate.current_price_context.get("price"))}</td>
  <td>{html.escape(candidate.setup_priority)}</td>
  <td><span class="badge {badge_class(candidate.setup_status)}">{html.escape(candidate.setup_status)}</span></td>
  <td>{format_number(candidate.gnn_prob)}</td>
  <td>
    {html.escape(candidate.pattern_context.get("family", "n/a"))}
    <div class="muted">score {format_number(candidate.pattern_context.get("score"))}</div>
  </td>
  <td>
    {html.escape(news_value)}
    <div class="muted">{html.escape(narrative.get("status", ""))}</div>
  </td>
  <td>{format_number(candidate.pink_line_context.get("distance_pct"))}</td>
  <td>{format_number(candidate.squeeze_context.get("compression_score"))}</td>
  <td>{format_number(candidate.blue_sky_context.get("distance_to_52w_high_pct"))}</td>
  <td>{html.escape(candidate.risk_bucket or "")}</td>
</tr>"""


def render_sortable_header(label: str, sort_key: str, query: dict[str, str]) -> str:
    current_sort = query.get("sort", "")
    current_direction = query.get("direction", "")
    next_direction = default_sort_direction(sort_key)
    indicator = ""
    header_class = "sortable-header"
    if current_sort == sort_key:
        header_class += " active"
        if current_direction == "desc":
            next_direction = "asc"
            indicator = " ↓"
        else:
            next_direction = "desc"
            indicator = " ↑"
    query_params = {
        "search": query.get("search", ""),
        "category": query.get("category", ""),
        "action": query.get("action", ""),
        "risk_bucket": query.get("risk_bucket", ""),
        "status": query.get("status", ""),
        "limit": query.get("limit", "100"),
        "sort": sort_key,
        "direction": next_direction,
    }
    href = "?" + urlencode(query_params)
    return (
        f'<th><a class="{header_class}" href="{html.escape(href)}">'
        f"{html.escape(label)}<span class=\"sort-indicator\">{html.escape(indicator)}</span></a></th>"
    )


def default_sort_direction(sort_key: str) -> str:
    if sort_key in {"symbol", "priority", "setup", "risk"}:
        return "asc"
    return "desc"


def render_detail(candidate: CandidateRecord) -> str:
    checks = "\n".join(
        render_check_stack_item(name, payload)
        for name, payload in iter_ordered_checks(candidate.favor_checks_local)
    )
    posture = review_posture(candidate)
    posture_badge = badge_class(posture["badge"])
    status_badge = badge_class(candidate.setup_status)
    snapshot_json = html.escape(json.dumps(candidate.raw_snapshot, indent=2))
    historical_json = html.escape(json.dumps(candidate.historical_metrics, indent=2))
    checklist_items = "\n".join(
        f"<li>{html.escape(item)}</li>" for item in candidate.manual_open_checklist
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(candidate.symbol)} | Premarket Setup Review</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <main class="page-shell detail-layout">
    <a class="back-link" href="/">&#8592; Back to dashboard</a>
    <section class="card detail-hero">
      <div class="detail-hero-main">
        <p class="eyebrow">Premarket Setup Review</p>
        <div class="hero-title-row">
          <h1>{html.escape(candidate.symbol)}</h1>
          <span class="badge {status_badge}">{html.escape(candidate.setup_status)}</span>
        </div>
        <p class="hero-company">{html.escape(candidate.company_name or "Unnamed listing")}</p>
        <div class="hero-chip-row">
          <span class="badge badge-inline">{html.escape(candidate.setup_priority)}</span>
          <span class="badge badge-inline">{html.escape(candidate.selected_category or "Unclassified")}</span>
          <span class="badge badge-inline">{html.escape(candidate.trading_action or "WATCH_ONLY")}</span>
          <span class="badge badge-inline">{html.escape(candidate.risk_bucket or "UNKNOWN")}</span>
        </div>
        <p class="detail-status-note">{html.escape(candidate.alert_message)}</p>
      </div>
      <div class="detail-hero-stats">
        {render_summary_stat("Trade Date", candidate.trade_date.isoformat())}
        {render_summary_stat("Setup Score", f"{candidate.setup_score:.2f}")}
        {render_summary_stat("Structural Score", f"{candidate.structural_score:.2f}")}
        {render_summary_stat("News Score", format_number(candidate.newscore))}
      </div>
    </section>

    <section class="detail-review-strip card">
      <div class="review-posture-block">
        <span class="summary-label">Review posture</span>
        <span class="badge {posture_badge}">{html.escape(posture["label"])}</span>
      </div>
      <div>
        <span class="summary-label">Operator note</span>
        <strong>{html.escape(posture["message"])}</strong>
      </div>
      <div>
        <span class="summary-label">Phase 2 handoff</span>
        <strong>{html.escape(candidate.handoff_message)}</strong>
      </div>
    </section>

    <section class="detail-grid detail-primary-grid">
      <section class="card detail-card">
        <h2>Trade Context</h2>
        <div class="metric-cluster">
          {render_metric_item("Category", candidate.selected_category, tone="neutral")}
          {render_metric_item("Trading action", candidate.trading_action, tone=status_tone(candidate.trading_action))}
          {render_metric_item("Management action", candidate.management_action, tone="neutral")}
          {render_metric_item("Risk bucket", candidate.risk_bucket, tone=risk_tone(candidate.risk_bucket))}
          {render_metric_item("Top influencer", candidate.top_influencer, source=candidate.top_influence_type, tone="neutral")}
        </div>
      </section>

      <section class="card detail-card">
        <h2>Premarket Structure</h2>
        <div class="metric-cluster">
          {render_metric_item("Pink Line", candidate.pink_line_context.get("level"), source=candidate.pink_line_context.get("source"), note=format_percent_note(candidate.pink_line_context.get("distance_pct"), prefix="Distance to level"), tone=context_tone(candidate.pink_line_context.get("status")))}
          {render_metric_item("HTF Squeeze", candidate.squeeze_context.get("compression_score"), note=squeeze_note(candidate.squeeze_context), tone=context_tone(candidate.squeeze_context.get("status")))}
          {render_metric_item("Blue Sky", candidate.blue_sky_context.get("distance_to_52w_high_pct"), note=blue_sky_note(candidate.blue_sky_context), tone=context_tone(candidate.blue_sky_context.get("status")))}
          {render_metric_item("Relative volume", candidate.relative_volume_context.get("ratio"), note=relative_volume_note(candidate.relative_volume_context), tone=relative_volume_tone(candidate.relative_volume_context.get("ratio")))}
          {render_metric_item("Daily RSI", candidate.daily_rsi_context.get("value"), source=candidate.daily_rsi_context.get("source"), tone=rsi_tone(candidate.daily_rsi_context.get("value")))}
        </div>
      </section>

      <section class="card detail-card decision-card">
        <h2>Narrative & Handoff</h2>
        <div class="metric-cluster">
          {render_metric_item("News sentiment", candidate.newssentiment or "Not populated", note=candidate.narrative_context.get("reason"), tone=context_tone(candidate.narrative_context.get("status")))}
          {render_metric_item("News score", candidate.newscore, note=narrative_note(candidate.narrative_context), tone=context_tone(candidate.narrative_context.get("status")))}
          {render_metric_item("Setup status", candidate.setup_status, tone=context_tone(candidate.setup_status))}
          {render_metric_item("Requires intraday confirmation", yes_no(candidate.requires_intraday_confirmation), note=candidate.handoff_message, tone="watch")}
        </div>
      </section>

      <section class="card detail-card">
        <h2>Pattern Intelligence</h2>
        <div class="metric-cluster">
          {render_metric_item("Pattern family", candidate.pattern_context.get("family"), note=candidate.pattern_context.get("summary"), tone=pattern_tone(candidate.pattern_context.get("confidence")))}
          {render_metric_item("Pattern score", candidate.pattern_context.get("score"), note=pattern_signature_note(candidate.pattern_context), tone=pattern_tone(candidate.pattern_context.get("confidence")))}
          {render_metric_item("Confidence", candidate.pattern_context.get("confidence"), note=pattern_peer_note(candidate.pattern_context), tone=pattern_tone(candidate.pattern_context.get("confidence")))}
        </div>
      </section>
    </section>

    <section class="card detail-card">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Review Sequence</p>
          <h2>Premarket Checks</h2>
        </div>
        <p class="muted section-note">These checks rank the setup before the open. They do not confirm live execution timing.</p>
      </div>
      <div class="check-stack">
        {checks}
      </div>
    </section>

    <section class="detail-grid detail-primary-grid">
      <section class="card detail-card">
        <div class="section-heading">
          <div>
            <p class="eyebrow">At The Open</p>
            <h2>Manual Follow-Through Checklist</h2>
          </div>
        </div>
        <ul class="golden-hour-list">
          {checklist_items}
        </ul>
      </section>

      <section class="card detail-card">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Phase 2</p>
            <h2>External Intraday Handoff</h2>
          </div>
        </div>
        <p class="muted">{html.escape(candidate.handoff_message)}</p>
        <p class="muted">This screen ends at watchlist preparation. A separate intraday system owns minute-by-minute breakout timing, volume validation, and execution.</p>
      </section>
    </section>

    <section class="diagnostics-stack">
      <details class="card diagnostic-card">
        <summary>Diagnostics: historical metrics</summary>
        <pre>{historical_json}</pre>
      </details>

      <details class="card diagnostic-card">
        <summary>Diagnostics: raw market snapshot</summary>
        <pre>{snapshot_json}</pre>
      </details>
    </section>
  </main>
</body>
</html>
"""


def render_filter_group(*, label: str, name: str, values: list[str], current: str) -> str:
    options = ['<option value="">All</option>']
    for value in values:
        selected = " selected" if value == current else ""
        options.append(
            f'<option value="{html.escape(value)}"{selected}>{html.escape(value)}</option>'
        )
    return f"""
    <label>
      {html.escape(label)}
      <select name="{html.escape(name)}">
        {''.join(options)}
      </select>
    </label>
    """


def render_check_stack_item(name: str, payload: dict[str, Any]) -> str:
    return f"""<article class="check-item">
      <div class="check-item-main">
        <div class="check-item-header">
          <h3>{html.escape(payload.get("label", name))}</h3>
          <span class="badge {badge_class(payload.get("status", ""))}">{html.escape(payload.get("status", ""))}</span>
        </div>
        <p class="check-item-reason">{html.escape(payload.get("reason", ""))}</p>
      </div>
      <div class="check-item-value">
        <span class="summary-label">Value</span>
        <strong>{format_number(payload.get("value"))}</strong>
      </div>
    </article>"""


def iter_ordered_checks(checks: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    order = (
        "gnn_support",
        "pink_line_context",
        "squeeze_context",
        "blue_sky_context",
        "narrative_context",
        "pattern_context",
        "relative_volume_context",
        "risk_context",
    )
    known = [(name, checks[name]) for name in order if name in checks]
    extras = [(name, payload) for name, payload in checks.items() if name not in order]
    return known + extras


def render_summary_stat(label: str, value: str) -> str:
    return f"""<div class="summary-stat">
      <span class="summary-label">{html.escape(label)}</span>
      <strong>{html.escape(value)}</strong>
    </div>"""


def render_metric_item(
    label: str,
    value: Any,
    *,
    source: str | None = None,
    note: str | None = None,
    tone: str = "neutral",
) -> str:
    note_html = ""
    source_html = ""
    if source:
        source_html = f'<div class="metric-source">{html.escape(source)}</div>'
    if note:
        note_html = f'<div class="metric-note">{html.escape(note)}</div>'
    return f"""<div class="metric-item tone-{html.escape(tone)}">
      <dt>{html.escape(label)}</dt>
      <dd>
        <div class="metric-value">{format_number(value)}</div>
        {source_html}
        {note_html}
      </dd>
    </div>"""


def review_posture(candidate: CandidateRecord) -> dict[str, str]:
    status = candidate.setup_status.upper()
    if status == "HIGH_PRIORITY_SETUP":
        return {
            "label": "Ready for open review",
            "badge": "PASS",
            "message": "This setup deserves attention before the bell and should be handed to the intraday system at the open.",
        }
    if status == "WATCHLIST":
        return {
            "label": "Watch closely",
            "badge": "WATCH",
            "message": "The structure is interesting, but it is not the strongest setup on the board yet.",
        }
    if status == "NEEDS_REVIEW":
        return {
            "label": "Needs review",
            "badge": "WATCH",
            "message": "The setup may work, but missing or mixed narrative inputs still require human review.",
        }
    return {
        "label": "Not ready",
        "badge": "FAIL",
        "message": "The structure is weak enough that this name should not be a core premarket focus.",
    }


def narrative_summary(candidate: CandidateRecord) -> str:
    if candidate.newssentiment and candidate.newscore is not None:
        return f"{candidate.newssentiment} {candidate.newscore:.2f}"
    if candidate.newssentiment:
        return candidate.newssentiment
    if candidate.newscore is not None:
        return f"score {candidate.newscore:.2f}"
    return "incomplete"


def format_percent_note(value: Any, *, prefix: str) -> str | None:
    if isinstance(value, float):
        return f"{prefix}: {value:.2f}%"
    return None


def relative_volume_note(context: dict[str, Any]) -> str | None:
    current_volume = context.get("current_volume")
    avg_volume = context.get("avg_volume_5d")
    if isinstance(current_volume, float) and isinstance(avg_volume, float):
        return f"Current {current_volume:.0f} vs 5D avg {avg_volume:.0f}"
    return None


def squeeze_note(context: dict[str, Any]) -> str:
    parts: list[str] = []
    if isinstance(context.get("range_ratio"), float):
        parts.append(f"Range ratio {context['range_ratio']:.2f}")
    if isinstance(context.get("volatility_ratio"), float):
        parts.append(f"Vol ratio {context['volatility_ratio']:.2f}")
    if not parts:
        return "Compression inputs are incomplete."
    return " | ".join(parts)


def blue_sky_note(context: dict[str, Any]) -> str:
    if context.get("is_52w_high"):
        return "Already at a 52-week high."
    if context.get("is_near_52w_high"):
        return "Trading near a 52-week high."
    return context.get("reason", "")


def narrative_note(context: dict[str, Any]) -> str:
    if context.get("completeness") == "INCOMPLETE":
        return "Embedded news columns are not populated yet."
    influencer = context.get("top_influencer")
    influence_type = context.get("influence_type")
    if influencer and influence_type:
        return f"Context support: {influencer} via {influence_type}"
    return context.get("reason", "")


def pattern_signature_note(context: dict[str, Any]) -> str:
    signature = context.get("feature_signature") or {}
    parts: list[str] = []
    if isinstance(signature.get("touch_count_90d"), int):
        parts.append(f"{signature['touch_count_90d']} touches")
    if isinstance(signature.get("compression_ratio"), float):
        parts.append(f"compression {signature['compression_ratio']:.2f}")
    if isinstance(signature.get("range_position_90d_pct"), float):
        parts.append(f"range {signature['range_position_90d_pct']:.0f}%")
    return " | ".join(parts) if parts else context.get("summary", "")


def pattern_peer_note(context: dict[str, Any]) -> str:
    peers = context.get("similar_setups_today") or []
    if peers:
        return "Similar today: " + ", ".join(peers)
    population = context.get("family_population")
    if isinstance(population, int):
        return f"{population} setup(s) in this pattern family today."
    return "No same-family peers surfaced on today’s board."


def status_tone(action: str | None) -> str:
    normalized = (action or "").upper()
    if normalized in {"BUY", "ADD", "HOLD"}:
        return "pass"
    if normalized == "WATCH_ONLY":
        return "watch"
    return "fail"


def risk_tone(risk_bucket: str | None) -> str:
    normalized = (risk_bucket or "").upper()
    if normalized in {"LOW", "MEDIUM"}:
        return "pass"
    if normalized == "HIGH":
        return "watch"
    return "fail"


def relative_volume_tone(value: Any) -> str:
    if isinstance(value, float):
        if value >= 1.0:
            return "pass"
        if value >= 0.75:
            return "watch"
    return "fail"


def rsi_tone(value: Any) -> str:
    if isinstance(value, float):
        if value >= 60:
            return "pass"
        if value >= 50:
            return "watch"
    return "fail"


def context_tone(status: str | None) -> str:
    normalized = (status or "").upper()
    if "HIGH_PRIORITY_SETUP" in normalized or normalized == "PASS":
        return "pass"
    if "WATCHLIST" in normalized or "NEEDS_REVIEW" in normalized or normalized == "WATCH":
        return "watch"
    return "fail"


def pattern_tone(confidence: str | None) -> str:
    normalized = (confidence or "").upper()
    if normalized == "HIGH":
        return "pass"
    if normalized == "MEDIUM":
        return "watch"
    return "fail"


def badge_class(status: str) -> str:
    normalized = status.upper()
    if "HIGH_PRIORITY_SETUP" in normalized or "READY" in normalized or normalized == "PASS":
        return "badge-pass"
    if (
        "WATCHLIST" in normalized
        or "NEEDS_REVIEW" in normalized
        or normalized == "WATCH"
    ):
        return "badge-pending"
    return "badge-fail"


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value is None:
        return "n/a"
    return html.escape(str(value))
