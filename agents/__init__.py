"""
========================================
Agents 智能体包
========================================

📚 模块说明：
用于组织各种智能 Agent，每个Agent负责编排tools
并根据业务场景组装提示词、输入输出结构。

🎯 包含Agent：
- WeeklyReportAgent  - 周报生成Agent
- RiskAnalysisAgent  - 风险分析Agent
- CostAnalysisAgent  - 成本分析Agent (新增)
- ProgressAnalysisAgent - 进度分析Agent (新增)
- SafetyAnalysisAgent - 安全分析Agent (新增)

💡 使用方式：
    from agents import get_weekly_report_agent, get_risk_agent
    from agents import get_cost_agent, get_progress_agent, get_safety_agent

    # 使用工厂函数创建实例
    agent = get_cost_agent(db)
    result = await agent.analyze_costs("P001")

========================================
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

# ===== 导入成本Agent (新增) =====
from agents.cost_agent import (
    CostAnalysisAgent,
    CostRiskLevel,
    CostCategory,
    CostOverview,
    CategoryCost,
    CostOverrun,
    CostTrend,
    CostPrediction,
    CostRisk,
    CostAnalysisResult,
    get_cost_agent,
)

# ===== 导入进度Agent (新增) =====
from agents.progress_agent import (
    ProgressAnalysisAgent,
    ProgressRiskLevel,
    TaskStatus,
    ProgressOverview,
    SPIAnalysis,
    DelayedTask,
    CriticalPathTask,
    ProgressTrend,
    CompletionPrediction,
    Bottleneck,
    ProgressAnalysisResult,
    get_progress_agent,
)

# ===== 导入安全Agent (新增) =====
from agents.safety_agent import (
    SafetyAnalysisAgent,
    SafetyRiskLevel,
    DefectLevel,
    DefectStatus,
    SafetyOverview,
    DefectByType,
    FrequentIssue,
    OpenDefect,
    SafetyTrend,
    RectificationPlan,
    SafetyAlert,
    SafetyAnalysisResult,
    get_safety_agent,
)


# ===== 导出列表 =====
__all__ = [
    # ===== 周报Agent =====
    "WeeklyReportAgent",
    "ReportFormat",
    "WeeklyReport",
    "ProgressSection",
    "CostSection",
    "SafetySection",
    "get_weekly_report_agent",

    # ===== 风险Agent =====
    "RiskAnalysisAgent",
    "RiskCategory",
    "RiskLevel",
    "RiskStatus",
    "RiskItem",
    "RiskAlert",
    "RiskTrend",
    "RiskAnalysisResult",
    "get_risk_agent",

    # ===== 成本Agent =====
    "CostAnalysisAgent",
    "CostRiskLevel",
    "CostCategory",
    "CostOverview",
    "CategoryCost",
    "CostOverrun",
    "CostTrend",
    "CostPrediction",
    "CostRisk",
    "CostAnalysisResult",
    "get_cost_agent",

    # ===== 进度Agent =====
    "ProgressAnalysisAgent",
    "ProgressRiskLevel",
    "TaskStatus",
    "ProgressOverview",
    "SPIAnalysis",
    "DelayedTask",
    "CriticalPathTask",
    "ProgressTrend",
    "CompletionPrediction",
    "Bottleneck",
    "ProgressAnalysisResult",
    "get_progress_agent",

    # ===== 安全Agent =====
    "SafetyAnalysisAgent",
    "SafetyRiskLevel",
    "DefectLevel",
    "DefectStatus",
    "SafetyOverview",
    "DefectByType",
    "FrequentIssue",
    "OpenDefect",
    "SafetyTrend",
    "RectificationPlan",
    "SafetyAlert",
    "SafetyAnalysisResult",
    "get_safety_agent",
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


# 示例3: 成本分析 (新增)
from agents import get_cost_agent

async def analyze_costs(db, project_id):
    agent = get_cost_agent(db)
    result = await agent.analyze_costs(
        project_id=project_id,
        analysis_months=3,
        include_ai_insights=True
    )
    return result


# 示例4: 进度分析 (新增)
from agents import get_progress_agent

async def analyze_progress(db, project_id):
    agent = get_progress_agent(db)
    result = await agent.analyze_progress(
        project_id=project_id,
        analysis_days=30,
        include_ai_insights=True
    )
    return result


# 示例5: 安全分析 (新增)
from agents import get_safety_agent

async def analyze_safety(db, project_id):
    agent = get_safety_agent(db)
    result = await agent.analyze_safety(
        project_id=project_id,
        analysis_days=30,
        include_ai_insights=True
    )
    return result


# 示例6: 快速检查
from agents import get_cost_agent, get_progress_agent, get_safety_agent

async def quick_check(db, project_id):
    cost_agent = get_cost_agent(db)
    progress_agent = get_progress_agent(db)
    safety_agent = get_safety_agent(db)
    
    return {
        "cost": await cost_agent.quick_cost_check(project_id),
        "progress": await progress_agent.quick_progress_check(project_id),
        "safety": await safety_agent.quick_safety_check(project_id)
    }
"""


