"""
Agents 包
=========

用于组织各种智能 Agent：
- 周报生成 Agent (WeeklyReportAgent)
- 风险分析 Agent (RiskAnalysisAgent)
- 成本分析 Agent (待实现)
等。

每个 Agent 主要负责编排 tools，并根据业务场景组装提示词、输入输出结构。

💡 使用方式：
    from agents import WeeklyReportAgent, RiskAnalysisAgent
    from agents import get_weekly_report_agent, get_risk_agent

    # 使用工厂函数创建实例
    agent = get_weekly_report_agent(db)
    result = await agent.generate_report("P001")
"""

# ===== 导入周报Agent =====
from agents.weekly_report_agent import (
    WeeklyReportAgent,
    ReportFormat,
    WeeklyReport,
    ProgressSection,
    CostSection,
    SafetySection,
    get_weekly_report_agent,
)

# ===== 导入风险Agent =====
from agents.risk_agent import (
    RiskAnalysisAgent,
    RiskCategory,
    RiskLevel,
    RiskStatus,
    RiskItem,
    RiskAlert,
    RiskTrend,
    RiskAnalysisResult,
    get_risk_agent,
)

# ===== 导出列表 =====
__all__ = [
    # 周报Agent
    "WeeklyReportAgent",
    "ReportFormat",
    "WeeklyReport",
    "ProgressSection",
    "CostSection",
    "SafetySection",
    "get_weekly_report_agent",

    # 风险Agent
    "RiskAnalysisAgent",
    "RiskCategory",
    "RiskLevel",
    "RiskStatus",
    "RiskItem",
    "RiskAlert",
    "RiskTrend",
    "RiskAnalysisResult",
    "get_risk_agent",
]


# =========================================
# 💡 使用示例
# =========================================
"""
# 示例1: 生成周报
from agents import get_weekly_report_agent, ReportFormat

async def generate_report(db, project_id):
    agent = get_weekly_report_agent(db)
    result = await agent.generate_report(
        project_id=project_id,
        report_format=ReportFormat.MARKDOWN,
        include_ai_suggestions=True
    )
    return result


# 示例2: 风险分析
from agents import get_risk_agent

async def analyze_risks(db, project_id):
    agent = get_risk_agent(db)
    result = await agent.analyze_risks(
        project_id=project_id,
        include_ai_insights=True,
        historical_days=30
    )
    return result


# 示例3: 快速风险扫描
from agents import get_risk_agent

async def quick_scan(db, project_id):
    agent = get_risk_agent(db)
    result = await agent.quick_scan(project_id)
    return result
"""