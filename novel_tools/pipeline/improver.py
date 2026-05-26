"""阶段 5: 改进 — 基于调研结果委托 subagent 实现改动."""

import json
from novel_tools.pipeline.db import update_gap_status, save_fix
from novel_tools import __version__ as TOOL_VERSION


def improve_gap_prompt(gap: dict, research_findings: dict) -> str:
    findings_str = json.dumps(research_findings, ensure_ascii=False, indent=2)
    return f"""改进 novel_tools 工具：

差距:
- 模块: {gap['module']}
- 类型: {gap['gap_type']}
- 描述: {gap['description']}

调研结果:
{findings_str}

任务:
1. 在 /home/miku/.hermes/skills/novel_any/novel_tools/ 下实现改进
2. 如果是新增功能，添加相应的检测逻辑
3. 如果是修复阈值，调整参数
4. 不要修改已有测试（用户不需要测试）
5. 完成后运行验证: python -m novel_tools.pipeline.pipeline run --phase analyze --book-id <id>
6. 确保导入正常: python -c "import novel_tools"

当前版本: {TOOL_VERSION}
改进后 bump 版本到 0.3.x"""


def prepare_improvement(gap_id: int, research_json: dict) -> dict:
    update_gap_status(gap_id, "fixing")
    return {"gap_id": gap_id, "status": "ready_for_delegation"}


if __name__ == "__main__":
    print(f"Improver ready. Tool version: {TOOL_VERSION}")
