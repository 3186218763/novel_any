"""黑名单词库管理 — 332 条 AI 高频禁用词，7 类 3 级."""

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SlopWord:
    """一个黑名单词条."""
    word: str
    category: str       # connector/filler/cliche/emotion/action/narration/dialogue
    severity: str        # ban/warn/limit
    max_per_chapter: int = 0

    @property
    def is_banned(self) -> bool:
        return self.severity == "ban"


@dataclass
class SlopDictionary:
    """黑名单词库."""
    words: list[SlopWord] = field(default_factory=list)
    _word_set: set[str] = field(default_factory=set, repr=False)
    _ban_set: set[str] = field(default_factory=set, repr=False)

    def __post_init__(self) -> None:
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._word_set = {w.word for w in self.words}
        self._ban_set = {w.word for w in self.words if w.is_banned}

    @property
    def total(self) -> int:
        return len(self.words)

    def contains(self, text: str) -> list[SlopWord]:
        return [sw for sw in self.words if sw.word in text]

    def count_hits(self, text: str) -> dict[str, int]:
        hits: dict[str, int] = {}
        for sw in self.words:
            count = text.count(sw.word)
            if count > 0:
                hits[sw.word] = count
        return hits

    def by_category(self, category: str) -> list[SlopWord]:
        return [w for w in self.words if w.category == category]

    def by_severity(self, severity: str) -> list[SlopWord]:
        return [w for w in self.words if w.severity == severity]


# 全局单例
_dictionary: SlopDictionary | None = None


def load_dictionary(path: str | None = None) -> SlopDictionary:
    """加载黑名单词库（单例模式）."""
    global _dictionary
    if _dictionary is not None:
        return _dictionary

    if path is None:
        # 默认路径：本模块同级 data/ 目录
        candidates = [
            Path(__file__).parent.parent / "data" / "anti_slop_zh.json",
            Path("novel_tools/data/anti_slop_zh.json"),
        ]
        for c in candidates:
            if c.exists():
                path = str(c)
                break
        else:
            logger.warning("anti_slop_zh.json not found, using empty dictionary")
            _dictionary = SlopDictionary(words=[])
            return _dictionary

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Dictionary file not found: {path}, using empty dictionary")
        _dictionary = SlopDictionary(words=[])
        return _dictionary
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in dictionary file {path}: {e}, using empty dictionary")
        _dictionary = SlopDictionary(words=[])
        return _dictionary

    words = [
        SlopWord(
            word=w["word"],
            category=w.get("category", "filler"),
            severity=w.get("severity", "warn"),
            max_per_chapter=w.get("max_per_chapter", 0),
        )
        for w in data.get("words", [])
    ]

    _dictionary = SlopDictionary(words=words)
    return _dictionary
