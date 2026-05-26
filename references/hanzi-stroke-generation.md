# hanzi_strokes.json 生成指南

> 用于 `stats/wordcount.py` 的 `flesch_zh` 中文可读性计算。
> 缺失此文件时，所有汉字默认按 10 画计算，flesch_zh 指标完全失真。

## 加载路径

`wordcount.py` 中 `_load_stroke_map()` 的读取路径：

```
novel_tools/data/hanzi_strokes.json   ← 正确路径
```

⚠️ 不是 `novel_tools/stats/data/hanzi_strokes.json`。`__file__` 是 `stats/wordcount.py`，
`.parent.parent` 回到 `novel_tools/`。

## 生成方法

### 来源：Unicode Unihan 数据库

官方下载：https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip

### 步骤

```bash
cd /tmp
curl -sL "https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip" -o Unihan.zip
```

```python
import zipfile, json, os

zf = zipfile.ZipFile("/tmp/Unihan.zip")
content = zf.read("Unihan_IRGSources.txt").decode("utf-8")

stroke_map = {}
for line in content.splitlines():
    if line.startswith('#') or 'kTotalStrokes' not in line:
        continue
    parts = line.split('\t')
    if len(parts) >= 3 and parts[1] == 'kTotalStrokes':
        try:
            char = chr(int(parts[0][2:], 16))
            val = parts[2].split()[0].strip()
            if val.isdigit():
                stroke_map[char] = int(val)
        except (ValueError, IndexError):
            pass

# 筛选 CJK Unified Ideographs (U+4E00-U+9FFF) + Extension A (U+3400-U+4DBF)
common = {}
for lo, hi in [(0x4E00, 0xA000), (0x3400, 0x4DC0)]:
    for cp in range(lo, hi):
        ch = chr(cp)
        if ch in stroke_map:
            common[ch] = stroke_map[ch]

os.makedirs("novel_tools/data", exist_ok=True)
with open("novel_tools/data/hanzi_strokes.json", "w", encoding="utf-8") as f:
    json.dump(common, f, ensure_ascii=False, separators=(',', ':'))
```

### 输出规格

- 约 27,500 个汉字
- ~240KB（紧凑 JSON，无缩进）
- key: 单个汉字, value: 笔画数 (int)
- 范围: CJK Unified Ideographs (20,992) + Extension A (6,592)
- 采样验证: `一→1 二→2 我→7 龘→48`

### 关键字段

| Unihan 字段 | 文件 | 含义 |
|------------|------|------|
| `kTotalStrokes` | `Unihan_IRGSources.txt` | 总笔画数（含部首） |
