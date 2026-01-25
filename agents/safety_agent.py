"""
安全分析Agent
==============

📚 模块说明：
- 安全检查数据分析
- 隐患识别与预警
- 整改跟踪与闭环
- 安全趋势分析

🎯 核心功能：
1. 安全概览：检查合格率、隐患统计
2. 隐患分析：按类型、等级分类
3. 频发问题：识别高频问题
4. 未闭环项：跟踪待整改问题
5. 趋势分析：安全状况变化
6. 整改计划：生成整改方案
7. 预警机制：安全风险预警

💡 使用方式：
    from agents.safety_agent import SafetyAnalysisAgent, get_safety_agent

    agent = get_safety_agent(db)
    result = await agent.analyze_safety("P001")
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from sqlalchemy.orm import Session
from loguru import logger

# 导入工具模块
from tools.safety_tools import SafetyTools, get_safety_tools
from tools.progress_tools import ProgressTools, get_progress_tools
from tools.rag_tool import run_rag

# 导入数据模型
from models.project import AgentWorkflowLog


class SafetyRiskLevel(str, Enum):
    """安全风险等级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefectLevel(str, Enum):
    """隐患等级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefectStatus(str, Enum):
    """隐患状态"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    VERIFIED = "verified"


@dataclass
class SafetyOverview:
    """安全概览"""
    project_id: str = ""
    project_name: str = ""
    analysis_period: str = ""
    total_checks: int = 0
    passed_checks: int = 0
    pass_rate: float = 100.0
    total_defects: int = 0
    high_level_defects: int = 0
    open_defects: int = 0
    closed_defects: int = 0
    closure_rate: float = 100.0
    risk_level: str = "low"


@dataclass
class DefectByType:
    """按类型统计隐患"""
    defect_type: str = ""
    type_name: str = ""
    count: int = 0
    high_level_count: int = 0
    open_count: int = 0
    percentage: float = 0.0


@dataclass
class FrequentIssue:
    """频发问题"""
    issue_type: str = ""
    occurrence_count: int = 0
    recent_occurrences: int = 0
    trend: str = "stable"
    affected_areas: List[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class OpenDefect:
    """未闭环隐患"""
    defect_id: str = ""
    defect_type: str = ""
    level: str = ""
    description: str = ""
    location: str = ""
    found_date: str = ""
    deadline: str = ""
    days_open: int = 0
    urgency: str = "normal"
    responsible: str = ""
    status: str = "open"


@dataclass
class SafetyTrend:
    """安全趋势"""
    period: str = ""
    checks: int = 0
    pass_rate: float = 100.0
    defects_found: int = 0
    defects_closed: int = 0
    high_level_defects: int = 0


@dataclass
class RectificationPlan:
    """整改计划"""
    phase: str = ""
    priority: str = ""
    items: List[Dict] = field(default_factory=list)
    deadline: str = ""
    responsible: str = ""


@dataclass
class SafetyAlert:
    """安全预警"""
    alert_id: str = ""
    alert_type: str = ""
    level: str = ""
    title: str = ""
    description: str = ""
    triggered_at: str = ""
    action_required: str = ""


@dataclass
class SafetyAnalysisResult:
    """安全分析结果"""
    project_id: str = ""
    project_name: str = ""
    analysis_date: str = ""
    analysis_period: str = ""
    overview: SafetyOverview = field(default_factory=SafetyOverview)
    defects_by_type: List[DefectByType] = field(default_factory=list)
    frequent_issues: List[FrequentIssue] = field(default_factory=list)
    frequent_issue_count: int = 0
    open_defects: List[OpenDefect] = field(default_factory=list)
    urgent_defects: int = 0
    overdue_defects: int = 0
    trends: List[SafetyTrend] = field(default_factory=list)
    trend_direction: str = "stable"
    rectification_plans: List[RectificationPlan] = field(default_factory=list)
    alerts: List[SafetyAlert] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    ai_insights: List[str] = field(default_factory=list)
    success: bool = True
    execution_time: float = 0.0
    error: str = ""


class SafetyAnalysisAgent:
    """安全分析Agent"""

    THRESHOLDS = {
        "pass_rate_critical": 80,
        "pass_rate_high": 90,
        "pass_rate_medium": 95,
        "high_defects_critical": 5,
        "high_defects_high": 3,
        "open_defects_critical": 15,
        "open_defects_high": 10,
        "closure_rate_warning": 80
    }

    def __init__(self, db: Session):
        """初始化Agent"""
        self.db = db
        self.safety_tools = get_safety_tools(db)
        self.progress_tools = get_progress_tools(db)
        logger.info("SafetyAnalysisAgent 初始化完成")

    async def analyze_safety(
            self,
            project_id: str,
            analysis_days: int = 30,
            include_ai_insights: bool = True
    ) -> Dict[str, Any]:
        """执行全面安全分析"""
        start_time = datetime.now()
        workflow_log = None

        try:
            workflow_log = self._start_workflow(project_id, "safety_analysis")
            logger.info(f"开始项目 {project_id} 安全分析")

            result = SafetyAnalysisResult(
                project_id=project_id,
                analysis_date=date.today().isoformat(),
                analysis_period=f"最近{analysis_days}天"
            )

            # Step 1: 获取项目信息
            project_overview = self.progress_tools.get_project_overview(project_id)
            result.project_name = project_overview.get("project_name", "未知项目")

            # Step 2: 安全概览
            overview_data = self.safety_tools.get_safety_overview(project_id, days=analysis_days)
            result.overview = self._build_overview(project_id, overview_data, analysis_days)

            # Step 3: 隐患分类统计
            type_data = self.safety_tools.get_defects_by_type(project_id)
            result.defects_by_type = self._build_defects_by_type(type_data)

            # Step 4: 频发问题
            frequent_data = self.safety_tools.get_frequent_issues(project_id, days=analysis_days)
            result.frequent_issues = self._build_frequent_issues(frequent_data)
            result.frequent_issue_count = len(result.frequent_issues)

            # Step 5: 未闭环隐患
            open_data = self.safety_tools.get_open_defects(project_id)
            result.open_defects = self._build_open_defects(open_data)
            result.urgent_defects = len([d for d in result.open_defects if d.urgency == "紧急"])
            result.overdue_defects = len([d for d in result.open_defects if d.days_open > 7])

            # Step 6: 安全趋势
            trend_data = self.safety_tools.analyze_safety_trend(project_id, days=analysis_days)
            result.trends = self._build_trends(trend_data)
            result.trend_direction = self._determine_trend_direction(result.trends)

            # Step 7: 整改计划
            plan_data = self.safety_tools.get_rectification_plan(project_id)
            result.rectification_plans = self._build_rectification_plans(plan_data)

            # Step 8: 安全预警
            result.alerts = self._generate_alerts(result)

            # Step 9: 生成建议
            result.suggestions = self.safety_tools.get_safety_suggestions(project_id)

            # Step 10: AI洞察
            if include_ai_insights:
                result.ai_insights = await self._generate_ai_insights(result)

            result.success = True
            result.execution_time = (datetime.now() - start_time).total_seconds()

            self._complete_workflow(workflow_log, result, start_time)
            logger.info(f"安全分析完成，耗时: {result.execution_time:.2f}秒")

            return asdict(result)

        except Exception as e:
            error_msg = f"安全分析失败: {str(e)}"
            logger.error(error_msg)
            self._fail_workflow(workflow_log, error_msg)
            return {
                "success": False,
                "project_id": project_id,
                "error": error_msg,
                "execution_time": (datetime.now() - start_time).total_seconds()
            }

    async def quick_safety_check(self, project_id: str, days: int = 7) -> Dict[str, Any]:
        """快速安全检查"""
        try:
            overview = self.safety_tools.get_safety_overview(project_id, days=days)
            pass_rate = overview.get("pass_rate", 100)
            high_defects = overview.get("high_level_defects", 0)
            open_defects = overview.get("open_defects", 0)

            if pass_rate < self.THRESHOLDS["pass_rate_critical"] or high_defects >= self.THRESHOLDS[
                "high_defects_critical"]:
                risk_level = "critical"
            elif pass_rate < self.THRESHOLDS["pass_rate_high"] or high_defects >= self.THRESHOLDS["high_defects_high"]:
                risk_level = "high"
            elif pass_rate < self.THRESHOLDS["pass_rate_medium"]:
                risk_level = "medium"
            else:
                risk_level = "low"

            alerts = []
            if pass_rate < self.THRESHOLDS["pass_rate_high"]:
                alerts.append(f"合格率偏低: {pass_rate:.1f}%")
            if high_defects >= self.THRESHOLDS["high_defects_high"]:
                alerts.append(f"重大隐患: {high_defects}项")

            return {
                "success": True,
                "project_id": project_id,
                "check_time": datetime.now().isoformat(),
                "pass_rate": pass_rate,
                "high_level_defects": high_defects,
                "open_defects": open_defects,
                "risk_level": risk_level,
                "alerts": alerts
            }

        except Exception as e:
            return {"success": False, "project_id": project_id, "error": str(e)}

    def _build_overview(self, project_id: str, data: Dict, days: int) -> SafetyOverview:
        """构建安全概览"""
        pass_rate = data.get("pass_rate", 100)
        high_defects = data.get("high_level_defects", 0)

        if pass_rate < self.THRESHOLDS["pass_rate_critical"] or high_defects >= self.THRESHOLDS[
            "high_defects_critical"]:
            risk_level = "critical"
        elif pass_rate < self.THRESHOLDS["pass_rate_high"] or high_defects >= self.THRESHOLDS["high_defects_high"]:
            risk_level = "high"
        elif pass_rate < self.THRESHOLDS["pass_rate_medium"]:
            risk_level = "medium"
        else:
            risk_level = "low"

        return SafetyOverview(
            project_id=project_id,
            project_name=data.get("project_name", ""),
            analysis_period=f"最近{days}天",
            total_checks=data.get("total_checks", 0),
            passed_checks=data.get("passed_checks", 0),
            pass_rate=pass_rate,
            total_defects=data.get("total_defects", 0),
            high_level_defects=high_defects,
            open_defects=data.get("open_defects", 0),
            closed_defects=data.get("closed_defects", 0),
            closure_rate=data.get("closure_rate", 100),
            risk_level=risk_level
        )

    def _build_defects_by_type(self, data: Dict) -> List[DefectByType]:
        """构建按类型统计"""
        types = data.get("types", {})
        return [DefectByType(
            defect_type=t_key,
            type_name=t_data.get("name", t_key),
            count=t_data.get("count", 0),
            high_level_count=t_data.get("high_level_count", 0),
            open_count=t_data.get("open_count", 0),
            percentage=t_data.get("percentage", 0)
        ) for t_key, t_data in types.items()]

    def _build_frequent_issues(self, data: List[Dict]) -> List[FrequentIssue]:
        """构建频发问题列表"""
        return [FrequentIssue(
            issue_type=issue.get("defect_type", ""),
            occurrence_count=issue.get("occurrence_count", 0),
            recent_occurrences=issue.get("recent_count", 0),
            trend=issue.get("trend", "stable"),
            affected_areas=issue.get("affected_areas", []),
            recommendation=issue.get("recommendation", "")
        ) for issue in data]

    def _build_open_defects(self, data: List[Dict]) -> List[OpenDefect]:
        """构建未闭环隐患列表"""
        return [OpenDefect(
            defect_id=defect.get("defect_id", ""),
            defect_type=defect.get("defect_type", ""),
            level=defect.get("level", "medium"),
            description=defect.get("description", ""),
            location=defect.get("location", ""),
            found_date=defect.get("found_date", ""),
            deadline=defect.get("deadline", ""),
            days_open=defect.get("days_open", 0),
            urgency=defect.get("urgency", "normal"),
            responsible=defect.get("responsible", ""),
            status=defect.get("status", "open")
        ) for defect in data]

    def _build_trends(self, data: Dict) -> List[SafetyTrend]:
        """构建趋势数据"""
        weekly_data = data.get("weekly_data", [])
        return [SafetyTrend(
            period=week.get("period", ""),
            checks=week.get("checks", 0),
            pass_rate=week.get("pass_rate", 100),
            defects_found=week.get("defects_found", 0),
            defects_closed=week.get("defects_closed", 0),
            high_level_defects=week.get("high_level_defects", 0)
        ) for week in weekly_data]

    def _determine_trend_direction(self, trends: List[SafetyTrend]) -> str:
        """判断趋势方向"""
        if len(trends) < 2:
            return "stable"
        recent_rates = [t.pass_rate for t in trends[-4:]]
        if len(recent_rates) >= 2:
            if recent_rates[-1] > recent_rates[0] + 2:
                return "improving"
            elif recent_rates[-1] < recent_rates[0] - 2:
                return "deteriorating"
        return "stable"

    def _build_rectification_plans(self, data: Dict) -> List[RectificationPlan]:
        """构建整改计划"""
        if not data.get("has_plan", False):
            return []
        phases = data.get("phases", [])
        return [RectificationPlan(
            phase=phase.get("phase", ""),
            priority=phase.get("priority", ""),
            items=phase.get("items", []),
            deadline=phase.get("deadline", ""),
            responsible=phase.get("responsible", "")
        ) for phase in phases]

    def _generate_alerts(self, result: SafetyAnalysisResult) -> List[SafetyAlert]:
        """生成安全预警"""
        alerts = []
        alert_id = 0

        if result.overview.pass_rate < self.THRESHOLDS["pass_rate_high"]:
            alert_id += 1
            alerts.append(SafetyAlert(
                alert_id=f"SA{alert_id:03d}",
                alert_type="pass_rate",
                level="high" if result.overview.pass_rate < self.THRESHOLDS["pass_rate_critical"] else "medium",
                title="安全检查合格率偏低",
                description=f"当前合格率{result.overview.pass_rate:.1f}%",
                triggered_at=datetime.now().isoformat(),
                action_required="加强安全巡查"
            ))

        if result.overview.high_level_defects >= self.THRESHOLDS["high_defects_high"]:
            alert_id += 1
            alerts.append(SafetyAlert(
                alert_id=f"SA{alert_id:03d}",
                alert_type="high_defects",
                level="critical" if result.overview.high_level_defects >= self.THRESHOLDS[
                    "high_defects_critical"] else "high",
                title="重大隐患数量较多",
                description=f"存在{result.overview.high_level_defects}项重大隐患",
                triggered_at=datetime.now().isoformat(),
                action_required="立即组织整改"
            ))

        return alerts

    async def _generate_ai_insights(self, result: SafetyAnalysisResult) -> List[str]:
        """生成AI洞察"""
        try:
            context = f"""
            项目安全分析结果：
            - 检查合格率: {result.overview.pass_rate}%
            - 重大隐患数: {result.overview.high_level_defects}
            - 未闭环隐患: {result.overview.open_defects}
            - 闭环率: {result.overview.closure_rate}%
            - 趋势: {result.trend_direction}
            """
            query = "基于以上安全分析结果，请提供专业的安全管理建议"
            rag_result = await run_rag(query, context=context)
            if rag_result and "answer" in rag_result:
                insights = rag_result["answer"].split("\n")
                return [i.strip() for i in insights if i.strip()]
            return ["建议持续加强安全巡查"]
        except Exception as e:
            logger.warning(f"AI洞察生成失败: {e}")
            return []

    def _start_workflow(self, project_id: str, workflow_type: str) -> Optional[AgentWorkflowLog]:
        """开始工作流日志"""
        try:
            log = AgentWorkflowLog(
                project_id=project_id, workflow_type=workflow_type,
                start_time=datetime.now(), status="running",
                input_params=json.dumps({"project_id": project_id})
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            return log
        except Exception as e:
            logger.warning(f"记录工作流开始失败: {e}")
            return None

    def _complete_workflow(self, log: Optional[AgentWorkflowLog], result: Any, start_time: datetime):
        """完成工作流日志"""
        if log:
            try:
                log.end_time = datetime.now()
                log.status = "completed"
                summary = {
                    "pass_rate": result.overview.pass_rate if hasattr(result, 'overview') else 0,
                    "risk_level": result.overview.risk_level if hasattr(result, 'overview') else "unknown"
                }
                log.output_result = json.dumps(summary)
                self.db.commit()
            except Exception as e:
                logger.warning(f"记录工作流完成失败: {e}")

    def _fail_workflow(self, log: Optional[AgentWorkflowLog], error: str):
        """记录工作流失败"""
        if log:
            try:
                log.end_time = datetime.now()
                log.status = "failed"
                log.error_message = error[:1000]
                self.db.commit()
            except Exception as e:
                logger.warning(f"记录工作流失败状态失败: {e}")


def get_safety_agent(db: Session) -> SafetyAnalysisAgent:
    """工厂函数：创建安全分析Agent实例"""
    return SafetyAnalysisAgent(db)