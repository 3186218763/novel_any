"""pipeline.validator — 验证分析工具输出与真实读者反馈的一致性."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from novel_tools.pipeline.db import (
    get_chapters,
    get_analyses_for_chapter,
    add_review,
    get_reviews,
    save_comparison,
    add_gap,
)

# ── Dimension mapping ──────────────────────────────────────────────────────

# Map Chinese keywords/patterns to analysis dimensions.
# Each entry: (keyword, dimension, default_sentiment)
# default_sentiment: "negative" or "positive"
_KEYWORD_RULES: list[tuple[str, str, str]] = [
    # ── pacing ──
    ("节奏", "pacing", "negative"),
    ("拖", "pacing", "negative"),
    ("水文", "pacing", "negative"),
    ("水字数", "pacing", "negative"),
    ("太慢", "pacing", "negative"),
    ("进展慢", "pacing", "negative"),
    ("节奏好", "pacing", "positive"),
    ("节奏快", "pacing", "positive"),
    ("爽快", "pacing", "positive"),
    # ── character_consistency ──
    ("角色崩", "character_consistency", "negative"),
    ("人设崩", "character_consistency", "negative"),
    ("人设", "character_consistency", "negative"),
    ("人物崩", "character_consistency", "negative"),
    ("性格变了", "character_consistency", "negative"),
    ("不出力", "character_consistency", "negative"),
    ("挂机", "character_consistency", "negative"),
    # ── ai_score ──
    ("AI", "ai_score", "negative"),
    ("套路", "ai_score", "negative"),
    ("模板", "ai_score", "negative"),
    ("刻板", "ai_score", "negative"),
    ("老套", "ai_score", "negative"),
    ("千篇一律", "ai_score", "negative"),
    # ── readability ──
    ("读不下去", "readability", "negative"),
    ("太绕", "readability", "negative"),
    ("看不懂", "readability", "negative"),
    ("混乱", "readability", "negative"),
    ("费劲", "readability", "negative"),
    ("难读", "readability", "negative"),
    ("流畅", "readability", "positive"),
    ("好读", "readability", "positive"),
    # ── emotion_arc ──
    ("情绪", "emotion_arc", "negative"),
    ("平淡", "emotion_arc", "negative"),
    ("无聊", "emotion_arc", "negative"),
    ("无趣", "emotion_arc", "negative"),
    ("没意思", "emotion_arc", "negative"),
    ("感人", "emotion_arc", "positive"),
    ("燃", "emotion_arc", "positive"),
    ("爽", "emotion_arc", "positive"),
    # ── redundancy ──
    ("啰嗦", "redundancy", "negative"),
    ("废话", "redundancy", "negative"),
    ("重复", "redundancy", "negative"),
    ("车轱辘", "redundancy", "negative"),
    ("冗长", "redundancy", "negative"),
    ("简洁", "redundancy", "positive"),
    # ── timeline ──
    ("时间混乱", "timeline", "negative"),
    ("时间线", "timeline", "negative"),
    ("bug", "timeline", "negative"),
    ("矛盾", "timeline", "negative"),
    ("前后不对", "timeline", "negative"),
    ("穿帮", "timeline", "negative"),
    # ── outline_deviation ──
    ("跑题", "outline_deviation", "negative"),
    ("大纲", "outline_deviation", "negative"),
    ("偏离主线", "outline_deviation", "negative"),
    ("偏了", "outline_deviation", "negative"),
    ("主线", "outline_deviation", "negative"),
    ("支线太多", "outline_deviation", "negative"),
    ("紧扣主线", "outline_deviation", "positive"),
]

# Public dimension map: keyword → dimension (for external lookup)
DIMENSION_MAP: dict[str, str] = {
    "节奏": "pacing",
    "拖": "pacing",
    "水文": "pacing",
    "角色崩": "character_consistency",
    "人设": "character_consistency",
    "AI": "ai_score",
    "套路": "ai_score",
    "模板": "ai_score",
    "读不下去": "readability",
    "太绕": "readability",
    "情绪": "emotion_arc",
    "平淡": "emotion_arc",
    "啰嗦": "redundancy",
    "废话": "redundancy",
    "时间混乱": "timeline",
    "bug": "timeline",
    "跑题": "outline_deviation",
    "大纲": "outline_deviation",
}

# Map from dimension to the analysis module that measures it
DIMENSION_MODULE: dict[str, str] = {
    "pacing": "pacing",
    "character_consistency": "stats",
    "ai_score": "ai_score",
    "readability": "stats",
    "emotion_arc": "emotion",
    "redundancy": "style_lint",
    "timeline": "stats",
    "outline_deviation": "stats",
}

# Thresholds: when tool metrics cross these, the tool considers the dimension "bad"
# metric_path: dotted path into the metrics dict (e.g. "readability.flesch_zh")
_TOOL_THRESHOLDS: dict[str, dict] = {
    "pacing": {"metric": "action_density", "op": "lt", "value": 15},
    "readability": {"metric": "readability.flesch_zh", "op": "lt", "value": 30},
    "emotion_arc": {"metric": "variance", "op": "lt", "value": 0.1},
    "redundancy": {"metric": "total_issues", "op": "gt", "value": 5},
    "ai_score": {"metric": "risk.score", "op": "gt", "value": 50},
}


# ── Dimension extraction ───────────────────────────────────────────────────

def _extract_dimensions_simple(text: str) -> list[tuple[str, str]]:
    """Extract (dimension, sentiment) pairs from review text via keyword matching.

    Returns a list of (dimension, sentiment) tuples. Sentiment is "negative"
    when the review complains about the dimension, "positive" when it praises.
    """
    results: list[tuple[str, str]] = []
    matched_dimensions: set[str] = set()

    # Longer keywords first to avoid partial matches (e.g., "时间混乱" before "混乱")
    sorted_rules = sorted(_KEYWORD_RULES, key=lambda r: -len(r[0]))

    for keyword, dimension, sentiment in sorted_rules:
        if keyword in text and dimension not in matched_dimensions:
            results.append((dimension, sentiment))
            matched_dimensions.add(dimension)

    return results


def _extract_dimensions_llm(text: str) -> list[tuple[str, str]]:
    """Extract dimensions using LLM (placeholder — falls back to simple)."""
    return _extract_dimensions_simple(text)


# ── Tool metric helpers ────────────────────────────────────────────────────

def _tool_normal_metrics_for_dimension(
    metrics: dict, dimension: str
) -> dict:
    """Extract the relevant sub-metrics for a dimension from tool output.

    Returns a dict with:
        metric_name, metric_value, threshold, op, is_bad, module
    """
    threshold_spec = _TOOL_THRESHOLDS.get(dimension)
    if not threshold_spec:
        # No threshold defined — we can't judge; assume normal
        return {
            "metric_name": "unknown",
            "metric_value": None,
            "threshold": None,
            "op": None,
            "is_bad": False,
            "module": DIMENSION_MODULE.get(dimension, "unknown"),
        }

    metric_path = threshold_spec["metric"]
    op = threshold_spec["op"]
    threshold = threshold_spec["value"]

    # Resolve dotted path: "readability.flesch_zh" -> metrics["readability"]["flesch_zh"]
    metric_value = metrics
    for part in metric_path.split("."):
        if isinstance(metric_value, dict):
            metric_value = metric_value.get(part)
        else:
            metric_value = None
            break
    if metric_value is None:
        # Metric not present in output — cannot judge
        return {
            "metric_name": metric_path,
            "metric_value": None,
            "threshold": threshold,
            "op": op,
            "is_bad": False,
            "module": DIMENSION_MODULE.get(dimension, "unknown"),
        }

    if op == "lt":
        is_bad = metric_value < threshold
    elif op == "gt":
        is_bad = metric_value > threshold
    else:
        is_bad = False

    return {
        "metric_name": metric_path,
        "metric_value": metric_value,
        "threshold": threshold,
        "op": op,
        "is_bad": is_bad,
        "module": DIMENSION_MODULE.get(dimension, "unknown"),
    }


def _tool_is_bad_for_dimension(metrics: dict, dimension: str) -> tuple[bool, dict]:
    """Check if tool metrics indicate a problem for the given dimension.

    Returns (is_bad, detail_dict).
    """
    detail = _tool_normal_metrics_for_dimension(metrics, dimension)
    return detail["is_bad"], detail


# ── Validation ─────────────────────────────────────────────────────────────

def validate_book(
    book_id: int, run_id: str = "", use_llm: bool = False
) -> dict:
    """Validate tool analyses against reader reviews for a book.

    For each review, extracts mentioned dimensions. For each chapter,
    compares tool metrics: if review complains about a dimension but
    tool shows normal → false_negative; if review praises but tool
    shows bad → false_positive; otherwise matched.

    Saves comparisons and gaps to the database.

    Args:
        book_id: The book to validate.
        run_id: Identifier for this validation run (auto-generated if empty).
        use_llm: If True, use LLM-extraction (placeholder; always simple for now).

    Returns:
        Stats dict with counts of matched, false_positive, false_negative,
        total_comparisons, and gaps.
    """
    if not run_id:
        run_id = uuid.uuid4().hex[:12]

    extract = _extract_dimensions_llm if use_llm else _extract_dimensions_simple

    # ── Load data ──────────────────────────────────────────────────────
    reviews = get_reviews(book_id)
    chapters = get_chapters(book_id)

    stats = {
        "run_id": run_id,
        "reviews_processed": len(reviews),
        "chapters_processed": len(chapters),
        "matched": 0,
        "false_positive": 0,
        "false_negative": 0,
        "total_comparisons": 0,
        "gaps_created": 0,
        "no_analysis_chapters": 0,
    }

    if not reviews:
        return stats
    if not chapters:
        return stats

    # ── Extract dimensions from reviews ─────────────────────────────────
    # review_dims: list of (review_row, [(dimension, sentiment), ...])
    review_dims: list[tuple[dict, list[tuple[str, str]]]] = []
    for review in reviews:
        dims = extract(review.get("content", ""))
        if dims:
            review_dims.append((review, dims))

    if not review_dims:
        return stats

    # ── Iterate chapters ─────────────────────────────────────────────────
    for chapter in chapters:
        chapter_id = chapter["id"]
        chapter_no = chapter.get("chapter_no", "?")
        analyses = get_analyses_for_chapter(chapter_id)

        if not analyses:
            stats["no_analysis_chapters"] += 1
            continue

        # Build a dict: module → metrics for this chapter
        module_metrics: dict[str, dict] = {}
        for analysis in analyses:
            module = analysis["module"]
            try:
                metrics = json.loads(analysis["metrics"])
            except (json.JSONDecodeError, TypeError):
                metrics = {}
            module_metrics[module] = metrics

        # ── Compare each review-dimension against this chapter ──────
        for review, dims in review_dims:
            review_id = review["id"]

            for dimension, review_sentiment in dims:
                tool_module = DIMENSION_MODULE.get(dimension, "stats")
                metrics = module_metrics.get(tool_module, {})

                is_bad, detail = _tool_is_bad_for_dimension(metrics, dimension)

                # Determine verdict
                if review_sentiment == "negative" and not is_bad:
                    verdict = "false_negative"
                    matched = False
                    confidence = 0.85
                    gap_detail = (
                        f"Reviewer complains about '{dimension}' "
                        f"(metric: {detail['metric_name']}={detail['metric_value']}, "
                        f"threshold: {detail['op']} {detail['threshold']}), "
                        f"but tool shows normal in chapter {chapter_no}."
                    )
                    stats["false_negative"] += 1
                elif review_sentiment == "positive" and is_bad:
                    verdict = "false_positive"
                    matched = False
                    confidence = 0.7
                    gap_detail = (
                        f"Review praised '{dimension}' but tool flagged it as bad "
                        f"(metric: {detail['metric_name']}={detail['metric_value']}, "
                        f"threshold: {detail['op']} {detail['threshold']}) "
                        f"in chapter {chapter_no}."
                    )
                    stats["false_positive"] += 1
                else:
                    verdict = "matched"
                    matched = True
                    confidence = 0.9
                    gap_detail = ""
                    stats["matched"] += 1

                stats["total_comparisons"] += 1

                # ── Save comparison ─────────────────────────────────
                # Find the analysis row that corresponds to this module
                analysis_row = next(
                    (a for a in analyses if a["module"] == tool_module), None
                )
                analysis_id = analysis_row["id"] if analysis_row else 0

                save_comparison(
                    run_id=run_id,
                    analysis_id=analysis_id,
                    review_id=review_id,
                    dimension=dimension,
                    matched=matched,
                    confidence=confidence,
                    verdict=verdict,
                    gap_detail=gap_detail,
                )

                # ── Register gap if mismatch ─────────────────────────
                if not matched:
                    add_gap(
                        module=tool_module,
                        gap_type=verdict,
                        description=(
                            f"[{dimension}] {detail['metric_name']}="
                            f"{detail['metric_value']} vs threshold "
                            f"{detail['op']} {detail['threshold']} "
                            f"(ch {chapter_no})"
                        ),
                    )
                    stats["gaps_created"] += 1

    return stats


# ── Manual review helper ───────────────────────────────────────────────────

def add_manual_reviews(
    book_id: int, reviews_text: str, source: str = "manual"
) -> list[int]:
    """Add reviews without scraping.

    Parses multi-line text. Each non-empty line becomes one review.

    Args:
        book_id: Book to associate reviews with.
        reviews_text: Raw text, one review per line.
        source: Label for the review source (default: 'manual').

    Returns:
        List of created review IDs.
    """
    ids: list[int] = []
    for line in reviews_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        review_id = add_review(
            book_id=book_id,
            source=source,
            content=line,
            sentiment="",
            keywords="",
        )
        ids.append(review_id)
    return ids
