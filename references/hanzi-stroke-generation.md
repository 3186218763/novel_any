# 汉字笔画映射生成

`hanzi_strokes.json` 从 Unicode Unihan 数据库生成，用于 flesch_zh 中文可读性计算。

## 生成流程

```bash
# 1. 下载 Unihan.zip
curl -sL "https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip" -o Unihan.zip

# 2. 提取 kTotalStrokes 字段（在 Unihan_IRGSources.txt 中）
python3 -c "
import zipfile, json
zf = zipfile.ZipFile('Unihan.zip')
content = zf.read('Unihan_IRGSources.txt').decode('utf-8')

stroke_map = {}
for line in content.splitlines():
    if 'kTotalStrokes' not in line: continue
    parts = line.split('\t')
    if len(parts) >= 3 and parts[1] == 'kTotalStrokes':
        char = chr(int(parts[0][2:], 16))
        val = parts[2].split()[0].strip()
        if val.isdigit():
            stroke_map[char] = int(val)

# 3. 过滤到常用 CJK 范围
common = {c: s for c, s in stroke_map.items() if '\u4e00' <= c <= '\u9fff'}
# 包含 Extension A
for cp in range(0x3400, 0x4DC0):
    c = chr(cp)
    if c in stroke_map: common[c] = stroke_map[c]

# 4. 保存
with open('hanzi_strokes.json', 'w') as f:
    json.dump(common, f, ensure_ascii=False, separators=(',', ':'))
```

## 文件位置

`novel_tools/data/hanzi_strokes.json`

wordcount.py 的 `_load_stroke_map()` 读取路径:
```python
Path(__file__).parent.parent / "data" / "hanzi_strokes.json"
# = novel_tools/data/hanzi_strokes.json
```

## 数据规模

- CJK Unified Ideographs (U+4E00-U+9FFF): 20,992 字
- 含 Extension A (U+3400-U+4DBF): 27,584 字
- 文件大小: ~242 KB

## 使用

```python
stroke_cache = _load_stroke_map()
stroke_sum = sum(stroke_cache.get(ch, 10) for ch in chinese_chars)
# 未知字默认 10 画
```
