"""章节节奏分析 — 对话/描写/叙述比例、段落密度、场景切换."""

import re
from pathlib import Path


def analyze_pacing(filepath: str) -> dict:
    """分析单个章节的节奏.

    Returns:
        dict with: dialogue_ratio, description_ratio, narration_ratio,
                   avg_paragraph_len, paragraph_density, scene_changes
    """
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (UnicodeDecodeError, PermissionError, IOError) as e:
        return {"error": str(e)}

    # 总中文字数
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text)) or 1  # 避免除零

    # 对话字数（「」和 "" 内的中文字符）
    dialogue_text = ''.join(re.findall(r'「([^」]*)」', text))
    dialogue_text += ''.join(re.findall(r'“([^”]*)”', text))
    dialogue_chars = len(re.findall(r'[\u4e00-\u9fff]', dialogue_text))

    # 描写字数（基于形容词/修饰词密度）
    # 统计描写相关的关键词：颜色、形状、声音、气味、触感等
    desc_patterns = [
        r'(?:红|橙|黄|绿|青|蓝|紫|黑|白|灰|金|银)',
        r'(?:大|小|高|矮|长|短|粗|细|宽|窄)',
        r'(?:形容|仿佛|如同|好像|宛如|宛若|似的|一般)',
        r'(?:声音|气味|味道|触感|温度|光线|阴影)',
    ]
    desc_hints = sum(len(re.findall(p, text)) for p in desc_patterns)

    # 叙述字数 = 总字数 - 对话字数（简化模型）
    narration_chars = chinese_chars - dialogue_chars

    # 段落统计
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip() and len(p.strip()) > 5]
    para_lens = [len(re.findall(r'[\u4e00-\u9fff]', p)) for p in paragraphs]

    # 场景切换（分割线 --- 或 ***）
    scene_changes = len(re.findall(r'^[-*]{3,}\s*$', text, re.MULTILINE))

    # === Show vs Tell 比率 ===
    show_vs_tell = round(dialogue_chars / chinese_chars, 3) if chinese_chars > 0 else 0

    # === 动作密度（常见动作动词频次/千字） ===
    ACTION_VERBS = [
        "走", "跑", "跳", "飞", "冲", "退", "进", "出", "站", "坐",
        "躺", "跪", "爬", "翻", "转", "挥", "打", "踢", "推", "拉",
        "抓", "握", "抱", "扔", "砸", "砍", "刺", "射", "拔", "抽",
        "拍", "敲", "点", "按", "捏", "撕", "扯", "咬", "吞", "咽",
    ]
    action_hits = sum(text.count(v) for v in ACTION_VERBS)
    action_density = round(action_hits / (chinese_chars / 1000), 1)

    return {
        "file_path": str(path),
        "chinese_chars": chinese_chars,
        "dialogue_ratio": round(dialogue_chars / chinese_chars, 3),
        "description_hints": desc_hints,  # 描写特征词命中数
        "narration_ratio": round(narration_chars / chinese_chars, 3),
        "paragraph_count": len(paragraphs),
        "avg_paragraph_len": round(sum(para_lens) / len(para_lens), 1) if para_lens else 0,
        "paragraph_density": round(len(paragraphs) / (chinese_chars / 1000), 1),  # 每千字段落数
        "scene_changes": scene_changes,
        "show_vs_tell_ratio": show_vs_tell,
        "action_density": action_density,
    }
