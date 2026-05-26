"""阶段 4: 调研 — delegate_task 委托 subagent 搜索解决方案."""

import json
from novel_tools.pipeline.db import list_open_gaps, update_gap_status, save_research


def research_gap_prompt(gap: dict) -> str:
    return f"""研究以下 novel_tools 工具的差距：

模块: {gap['module']}
差距类型: {gap['gap_type']}
描述: {gap['description']}
出现次数: {gap['occurrence_count']}

任务：
1. 在 GitHub 上搜索相关的开源中文 NLP/文本分析项目
2. 在 arXiv 上搜索相关论文
3. 分析每个方案的优缺点和可行性
4. 返回调研报告 JSON：

{{
  "sources": [{{"type": "github", "url": "...", "summary": "..."}}],
  "approaches": [{{"name": "...", "feasibility": "high/medium/low", "effort": "small/medium/large", "description": "..."}}],
  "recommendation": "推荐方案及理由"
}}

项目路径: /home/miku/.hermes/skills/novel_any/novel_tools/
当前实现代码在 novel_tools/{gap['module']}/ 下"""


def research_gaps() -> list[dict]:
    gaps = list_open_gaps()
    results = []
    for gap in gaps:
        prompt = research_gap_prompt(gap)
        update_gap_status(gap["id"], "researching")
        results.append({"gap_id": gap["id"], "module": gap["module"], "prompt": prompt, "status": "ready_for_delegation"})
    return results


if __name__ == "__main__":
    pending = research_gaps()
    print(f"待调研 gaps: {len(pending)}")
    for g in pending:
        print(f"  gap #{g['gap_id']}: {g['module']}")
