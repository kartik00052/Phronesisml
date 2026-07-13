"""Template-based Markdown report builder for Phronesis pipelines.

Assembles a Markdown report from WorkflowState data across all pipeline
stages.  Pure string formatting with graceful degradation for
missing/None fields.

The report is assembled from individual section builders, each of which
handles one pipeline stage.  If a section has no data (e.g. because the
stage was skipped or failed), a stub message is inserted indicating that
the section is unavailable.

Section builders:
- ``_build_summary_section``: run metadata (target, task type, ambiguity).
- ``_build_validation_section``: validation report from the Validation agent.
- ``_build_eda_section``: data profile from the EDA agent.
- ``_build_target_detection_section``: target detection results.
- ``_build_feature_engineering_section``: feature names and transformations.
- ``_build_model_selection_section``: candidate models, best model.
- ``_build_evaluation_section``: metrics, ambiguity caveat.
- ``_build_explainability_section``: feature importance, sampling info.
- ``_build_notes_section``: cross-cutting notes (ambiguity caveats, etc.).

Each builder takes the ``WorkflowState`` and returns a ``str`` for the
section.  The main ``build_report`` function reads the template and
substitutes the sections.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "full_report.md"


@lru_cache(maxsize=1)
def _read_template() -> str:
    """Read and cache the report template from disk."""
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


def build_report(state: Any, narrative: str | None = None) -> str:
    """Build a complete Markdown report from WorkflowState.

    Args:
        state: The WorkflowState (or compatible dataclass) containing
            outputs from all pipeline stages.
        narrative: Optional narrative summary string.  If ``None``,
            a stub message is inserted.  This is additive — the structured
            data sections remain the source of truth.

    Returns:
        A Markdown-formatted report string.

    """
    run_id = getattr(state, "run_id", "unknown")
    status = getattr(state, "status", "unknown")

    try:
        template = _read_template()
    except OSError as exc:
        logger.warning("Report template missing or unreadable: %s", exc)
        return (
            f"# Phronesis Report — {run_id}\n\n"
            f"**Status:** {status}\n\n"
            "_Report template could not be loaded. "
            "Check that Phronesis is installed correctly._\n"
        )

    return template.format(
        run_id=run_id,
        status=status,
        summary_section=_build_summary_section(state),
        narrative_section=_build_narrative_section(narrative),
        validation_section=_build_validation_section(state),
        eda_section=_build_eda_section(state),
        target_detection_section=_build_target_detection_section(state),
        feature_engineering_section=_build_feature_engineering_section(state),
        model_selection_section=_build_model_selection_section(state),
        evaluation_section=_build_evaluation_section(state),
        explainability_section=_build_explainability_section(state),
        notes_section=_build_notes_section(state),
    )


def build_html_report(state: Any, narrative: str | None = None) -> str:
    """Build a complete HTML report from WorkflowState.

    Uses the same section builders as the Markdown report but wraps
    the output in proper HTML structure.

    Args:
        state: The WorkflowState (or compatible dataclass) containing
            outputs from all pipeline stages.
        narrative: Optional narrative summary string.

    Returns:
        An HTML-formatted report string.
    """
    import html as html_mod

    run_id = html_mod.escape(str(getattr(state, "run_id", "unknown")))
    status = html_mod.escape(str(getattr(state, "status", "unknown")))

    def _md_to_html(text: str) -> str:
        """Minimal Markdown → HTML for report sections."""
        import re

        # Horizontal rules
        text = re.sub(r"^---+$", "<hr>", text, flags=re.MULTILINE)
        # Bold: **text**
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # Inline code: `text`
        text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
        # Italic: _text_
        text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", text)
        # Headings: ### text
        text = re.sub(r"^### (.+)$", r"<h4>\1</h4>", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
        text = re.sub(r"^# (.+)$", r"<h2>\1</2>", text, flags=re.MULTILINE)
        # Blockquote: > text
        text = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE)
        # Numbered list: 1. text
        text = re.sub(r"^\d+\. (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
        # Unordered list: - text
        text = re.sub(r"^- (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
        # Wrap consecutive <li> in <ul>
        text = re.sub(r"((?:<li>.*?</li>\n?)+)", r"<ul>\1</ul>", text)
        # Paragraphs: wrap remaining loose lines
        lines = text.split("\n")
        result: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("<"):
                result.append(f"<p>{html_mod.escape(stripped)}</p>")
            else:
                result.append(line)
        return "\n".join(result)

    sections = [
        ("Summary", _build_summary_section(state)),
        ("Narrative Summary", _build_narrative_section(narrative)),
        ("Data Validation", _build_validation_section(state)),
        ("Exploratory Data Analysis", _build_eda_section(state)),
        ("Target Detection", _build_target_detection_section(state)),
        ("Feature Engineering", _build_feature_engineering_section(state)),
        ("Model Selection", _build_model_selection_section(state)),
        ("Model Evaluation", _build_evaluation_section(state)),
        ("Model Explainability", _build_explainability_section(state)),
        ("Notes", _build_notes_section(state)),
    ]

    body_sections = "\n".join(
        f"<section><h2>{html_mod.escape(title)}</h2>{_md_to_html(content)}</section>"
        for title, content in sections
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phronesis Report — {run_id}</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 900px;
         margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; line-height: 1.6; }}
  h1 {{ border-bottom: 2px solid #e0e0e0; padding-bottom: 0.5rem; }}
  h2 {{ color: #2c3e50; margin-top: 2rem; }}
  h3, h4 {{ color: #34495e; }}
  section {{ margin-bottom: 1.5rem; padding: 1rem; border: 1px solid #eee;
             border-radius: 6px; background: #fafafa; }}
  pre {{ background: #f4f4f4; padding: 0.75rem; border-radius: 4px;
         overflow-x: auto; }}
  code {{ background: #f4f4f4; padding: 0.15em 0.35em; border-radius: 3px;
          font-size: 0.9em; }}
  blockquote {{ border-left: 3px solid #3498db; margin: 0.5rem 0;
                padding: 0.5rem 1rem; background: #eef6fb; }}
  ul {{ margin: 0.25rem 0 0.5rem 1.5rem; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 1.5rem 0; }}
  .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1rem; }}
</style>
</head>
<body>
<h1>Phronesis Pipeline Report</h1>
<p class="meta"><strong>Pipeline Run:</strong> {run_id} &mdash;
<strong>Status:</strong> {status}</p>
<hr>
{body_sections}
</body>
</html>"""


# ── Section builders ─────────────────────────────────────────────────


def _build_narrative_section(narrative: str | None) -> str:
    """Build the narrative section from a summary string.

    If no narrative is provided, a stub message is inserted indicating
    that the narrative was not generated.
    """
    if narrative is None:
        return "_Narrative summary not generated._"
    if not narrative.strip():
        return "_Narrative summary was empty._"
    return narrative


def _build_summary_section(state: Any) -> str:
    """Build the summary/metadata section."""
    lines = []
    target = getattr(state, "target_column", None)
    task_type = getattr(state, "task_type", None)
    confidence = getattr(state, "target_detection_confidence", None)
    ambiguity = getattr(state, "ambiguity_reason", None)

    if target is not None:
        lines.append(f"- **Target Column:** {target}")
    if task_type is not None:
        lines.append(f"- **Task Type:** {task_type}")
    if confidence is not None:
        lines.append(f"- **Detection Confidence:** {confidence:.2f}")
    if ambiguity is not None:
        lines.append(f"- **Ambiguity:** {ambiguity}")

    feature_names = getattr(state, "feature_names", None)
    if feature_names:
        lines.append(f"- **Features ({len(feature_names)}):** {', '.join(feature_names[:10])}")
        if len(feature_names) > 10:
            lines.append(f"  ... and {len(feature_names) - 10} more")

    best = getattr(state, "best_pipeline", None)
    if best is not None:
        model_type = getattr(best, "model_type", None)
        if model_type is None and isinstance(best, dict):
            model_type = best.get("model_type")
        if model_type is not None:
            lines.append(f"- **Best Model:** {model_type}")

    return "\n".join(lines) if lines else "_No summary data available._"


def _build_validation_section(state: Any) -> str:
    """Build the validation section from validation_report."""
    report = getattr(state, "validation_report", None)
    if report is None:
        return "_Validation data not available._"

    lines = []
    if isinstance(report, dict):
        checks = report.get("checks", [])
        if checks:
            lines.append(f"**{len(checks)} validation checks performed:**\n")
            for check in checks:
                if isinstance(check, dict):
                    name = check.get("name", "unknown")
                    passed = check.get("passed", False)
                    status_icon = "PASS" if passed else "FAIL"
                    lines.append(f"- [{status_icon}] {name}")
        else:
            lines.append("_No validation checks recorded._")
    else:
        lines.append(f"Validation report type: {type(report).__name__}")

    return "\n".join(lines) if lines else "_Validation data not available._"


def _build_eda_section(state: Any) -> str:
    """Build the EDA section from data_profile."""
    profile = getattr(state, "data_profile", None)
    if profile is None:
        return "_EDA data not available._"

    lines = []
    if isinstance(profile, dict):
        n_rows = profile.get("n_rows")
        n_cols = profile.get("n_cols")
        if n_rows is not None:
            lines.append(f"- **Rows:** {n_rows}")
        if n_cols is not None:
            lines.append(f"- **Columns:** {n_cols}")

        null_pct = profile.get("null_percentage")
        if null_pct is not None:
            lines.append(f"- **Null Percentage:** {null_pct:.1f}%")

        dtypes = profile.get("dtypes", {})
        if dtypes:
            lines.append(f"- **Column Types:** {len(dtypes)} columns")
    else:
        lines.append(f"Profile type: {type(profile).__name__}")

    return "\n".join(lines) if lines else "_EDA data not available._"


def _build_target_detection_section(state: Any) -> str:
    """Build the target detection section."""
    target = getattr(state, "target_column", None)
    task_type = getattr(state, "task_type", None)
    confidence = getattr(state, "target_detection_confidence", None)
    ambiguity = getattr(state, "ambiguity_reason", None)

    if target is None and task_type is None:
        return "_Target detection data not available._"

    lines = []
    if target is not None:
        lines.append(f"- **Detected Target:** {target}")
    if task_type is not None:
        lines.append(f"- **Task Type:** {task_type}")
    if confidence is not None:
        lines.append(f"- **Confidence:** {confidence:.2f}")
    if ambiguity is not None:
        lines.append(f"- **Ambiguity Reason:** {ambiguity}")

    return "\n".join(lines) if lines else "_Target detection data not available._"


def _build_feature_engineering_section(state: Any) -> str:
    """Build the feature engineering section."""
    feature_names = getattr(state, "feature_names", None)
    if feature_names is None:
        return "_Feature engineering data not available._"

    lines = [f"- **{len(feature_names)} engineered features:**"]
    for name in feature_names:
        lines.append(f"  - {name}")

    return "\n".join(lines)


def _build_model_selection_section(state: Any) -> str:
    """Build the model selection section."""
    candidates = getattr(state, "candidate_models", None)
    best = getattr(state, "best_pipeline", None)

    if candidates is None and best is None:
        return "_Model selection data not available._"

    lines = []
    if candidates and isinstance(candidates, list):
        lines.append(f"**{len(candidates)} candidate models evaluated:**\n")
        for i, c in enumerate(candidates[:5], 1):
            if isinstance(c, dict):
                name = c.get("model_type", f"Candidate {i}")
                score = c.get("mean_cv_score")
                if score is not None:
                    lines.append(f"{i}. {name} (CV score: {score:.4f})")
                else:
                    lines.append(f"{i}. {name}")

    if best is not None:
        model_type = (
            getattr(best, "model_type", None)
            if not isinstance(best, dict)
            else best.get("model_type")
        )
        if model_type is not None:
            lines.append(f"\n**Selected Model:** {model_type}")

    return "\n".join(lines) if lines else "_Model selection data not available._"


def _build_evaluation_section(state: Any) -> str:
    """Build the evaluation section."""
    report = getattr(state, "evaluation_report", None)
    if report is None:
        return "_Evaluation data not available._"

    lines = []
    if isinstance(report, dict):
        metrics = report.get("metrics", {})
        if metrics:
            lines.append("**Metrics:**\n")
            for name, value in metrics.items():
                if isinstance(value, float):
                    lines.append(f"- {name}: {value:.4f}")
                else:
                    lines.append(f"- {name}: {value}")

        caveat = report.get("ambiguity_caveat")
        if caveat:
            lines.append(f"\n> **Note:** {caveat}")
    else:
        lines.append(f"Evaluation report type: {type(report).__name__}")

    return "\n".join(lines) if lines else "_Evaluation data not available._"


def _build_explainability_section(state: Any) -> str:
    """Build the explainability section."""
    report = getattr(state, "explanation_report", None)
    if report is None:
        return "_Explainability data not available._"

    lines = []
    if isinstance(report, dict):
        importance = report.get("feature_importance", {})
        if importance:
            sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            lines.append("**Feature Importance (top 10 by mean |SHAP value|):**\n")
            for name, score in sorted_features[:10]:
                top_score = sorted_features[0][1]
                bar = "#" * int(score / top_score * 20) if top_score > 0 else ""
                lines.append(f"- {name}: {score:.4f}  `{bar}`")

        explainer = report.get("explainer_type")
        if explainer:
            lines.append(f"\n**Explainer:** {explainer}")

        sampled = report.get("sampled", False)
        n_used = report.get("n_samples_used", None)
        max_s = report.get("max_samples", None)
        if sampled and n_used is not None:
            lines.append(
                f"\n> **Note:** Explanations based on a sample of {n_used} rows "
                f"(max_samples={max_s}). Full dataset may differ.",
            )
    else:
        lines.append(f"Explanation report type: {type(report).__name__}")

    return "\n".join(lines) if lines else "_Explainability data not available._"


def _build_notes_section(state: Any) -> str:
    """Build the notes/cross-cutting concerns section."""
    notes = []
    ambiguity = getattr(state, "ambiguity_reason", None)
    task_type = getattr(state, "task_type", None)

    if task_type == "ambiguous" and ambiguity:
        notes.append(f"- **Ambiguity detected:** {ambiguity}")
        notes.append(
            "- The task type could not be definitively determined. "
            "Results should be interpreted with caution.",
        )

    eval_report = getattr(state, "evaluation_report", None)
    if isinstance(eval_report, dict):
        caveat = eval_report.get("ambiguity_caveat")
        if caveat:
            notes.append(f"- **Evaluation caveat:** {caveat}")

    explanation = getattr(state, "explanation_report", None)
    if isinstance(explanation, dict) and explanation.get("sampled"):
        notes.append(
            "- **Explainability sampling:** Feature importance is based on a "
            "sampled subset of the data, not the full dataset.",
        )

    if not notes:
        notes.append("_No special notes._")

    return "\n".join(notes)
