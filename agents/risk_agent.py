"""
风险分析Agent
==============

📚 模块说明：
- 多维度风险识别与评估
- 整合进度、成本、安全三大风险域
- 预警等级判定与趋势预测
- 风险应对建议生成

🎯 核心功能：
1. 风险扫描：定期扫描各维度风险
2. 风险评估：量化风险等级和影响
3. 预警生成：触发风险预警通知
4. 建议生成：基于RAG生成应对建议

💡 使用方式：
    from agents.risk_agent import RiskAnalysisAgent

    agent = RiskAnalysisAgent(db)
    result = await agent.analyze_risks("P001")
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from sqlalchemy.orm import Session
from loguru import logger

# 导入工具模块
from tools.progress_tools import ProgressTools, get_progress_tools
from tools.cost_tools import CostTools, get_cost_tools
from tools.safety_tools import SafetyTools, get_safety_tools
from tools.rag_tool import run_rag

# 导入数据模型
from models.project import AgentWorkflowLog


class RiskCategory(str, Enum):
    """风险类别"""
    PROGRESS = "progress"  # 进度风险
    COST = "cost"  # 成本风险
    SAFETY = "safety"  # 安全风险
    QUALITY = "quality"  # 质量风险
    RESOURCE = "resource"  # 资源风险
    EXTERNAL = "external"  # 外部风险


class RiskLevel(str, Enum):
    """风险等级"""
    CRITICAL = "critical"  # 紧急 (红色)
    HIGH = "high"  # 高 (橙色)
    MEDIUM = "medium"  # 中 (黄色)
    LOW = "low"  # 低 (绿色)


class RiskStatus(str, Enum):
    """风险状态"""
    ACTIVE = "active"  # 活跃
    MONITORING = "monitoring"  # 监控中
    MITIGATING = "mitigating"  # 处理中
    RESOLVED = "resolved"  # 已解决
    ACCEPTED = "accepted"  # 已接受


@dataclass
class RiskItem:
    """风险项"""
    risk_id: str = ""
    category: str = ""
    level: str = ""
    status: str = "active"
    title: str = ""
    description: str = ""
    impact: str = ""
    probability: float = 0.5  # 发生概率 0-1
    impact_score: float = 0.5  # 影响程度 0-1
    risk_score: float = 0.25  # 风险分数 = 概率 × 影响
    indicators: Dict[str, Any] = field(default_factory=dict)  # 相关指标
    recommendations: List[str] = field(default_factory=list)  # 应对建议
    owner: str = ""  # 责任人
    deadline: str = ""  # 处理期限
    created_at: str = ""
    updated_at: str = ""


@dataclass
class RiskAlert:
    """风险预警"""
    alert_id: str = ""
    risk_id: str = ""
    level: str = ""
    title: str = ""
    message: str = ""
    triggered_at: str = ""
    acknowledged: bool = False


@dataclass
class RiskTrend:
    """风险趋势"""
    category: str = ""
    current_level: str = ""
    previous_level: str = ""
    trend: str = ""  # improving/stable/deteriorating
    key_changes: List[str] = field(default_factory=list)


@dataclass
class RiskAnalysisResult:
    """风险分析结果"""
    # 基本信息
    project_id: str = ""
    project_name: str = ""
    analysis_date: str = ""
    analysis_period: str = ""

    # 风险汇总
    total_risks: int = 0
    critical_risks: int = 0
    high_risks: int = 0
    medium_risks: int = 0
    low_risks: int = 0

    # 综合风险评级
    overall_risk_level: str = "low"
    overall_risk_score: float = 0.0

    # 各维度风险
    progress_risks: List[RiskItem] = field(default_factory=list)
    cost_risks: List[RiskItem] = field(default_factory=list)
    safety_risks: List[RiskItem] = field(default_factory=list)

    # 风险预警
    alerts: List[RiskAlert] = field(default_factory=list)

    # 风险趋势
    trends: List[RiskTrend] = field(default_factory=list)

    # Top风险
    top_risks: List[RiskItem] = field(default_factory=list)

    # 应对建议
    mitigation_plan: List[Dict] = field(default_factory=list)

    # AI建议
    ai_insights: List[str] = field(default_factory=list)


class RiskAnalysisAgent:
    """
    风险分析Agent

    职责：
    - 多维度风险扫描
    - 风险量化评估
    - 预警生成
    - 应对建议

    工作流程：
    1. 扫描进度风险
    2. 扫描成本风险
    3. 扫描安全风险
    4. 综合风险评估
    5. 生成预警和建议
    """

    # 风险阈值配置
    THRESHOLDS = {
        "progress": {
            "spi_critical": 0.75,
            "spi_high": 0.85,
            "spi_medium": 0.95,
            "delayed_tasks_critical": 10,
            "delayed_tasks_high": 5,
            "critical_path_delayed": 2
        },
        "cost": {
            "cpi_critical": 0.75,
            "cpi_high": 0.85,
            "cpi_medium": 0.95,
            "variance_rate_critical": 15,
            "variance_rate_high": 10,
            "variance_rate_medium": 5
        },
        "safety": {
            "high_defects_critical": 5,
            "high_defects_high": 3,
            "open_defects_critical": 15,
            "open_defects_high": 10,
            "pass_rate_critical": 80,
            "pass_rate_high": 90
        }
    }

    def __init__(self, db: Session):
        """初始化Agent"""
        self.db = db

        # 初始化工具模块
        self.progress_tools = get_progress_tools(db)
        self.cost_tools = get_cost_tools(db)
        self.safety_tools = get_safety_tools(db)

        # 风险ID计数器
        self._risk_counter = 0

        logger.info("RiskAnalysisAgent 初始化完成")

    async def analyze_risks(
            self,
            project_id: str,
            include_ai_insights: bool = True,
            historical_days: int = 30
    ) -> Dict[str, Any]:
        """
        执行全面风险分析

        参数:
            project_id: 项目ID
            include_ai_insights: 是否包含AI洞察
            historical_days: 历史数据分析天数

        返回:
            风险分析结果字典
        """
        start_time = datetime.now()
        workflow_log = None

        try:
            # 记录工作流
            workflow_log = self._start_workflow(project_id, "risk_analysis")

            logger.info(f"开始项目 {project_id} 风险分析")

            # 初始化结果
            result = RiskAnalysisResult(
                project_id=project_id,
                analysis_date=date.today().isoformat(),
                analysis_period=f"最近{historical_days}天"
            )

            # Step 1: 获取项目信息
            overview = self.progress_tools.get_project_overview(project_id)
            result.project_name = overview.get("project_name", "未知项目")

            # Step 2: 扫描进度风险
            result.progress_risks = await self._scan_progress_risks(project_id)

            # Step 3: 扫描成本风险
            result.cost_risks = await self._scan_cost_risks(project_id)

            # Step 4: 扫描安全风险
            result.safety_risks = await self._scan_safety_risks(project_id)

            # Step 5: 汇总统计
            all_risks = result.progress_risks + result.cost_risks + result.safety_risks
            result.total_risks = len(all_risks)
            result.critical_risks = len([r for r in all_risks if r.level == "critical"])
            result.high_risks = len([r for r in all_risks if r.level == "high"])
            result.medium_risks = len([r for r in all_risks if r.level == "medium"])
            result.low_risks = len([r for r in all_risks if r.level == "low"])

            # Step 6: 综合风险评估
            result.overall_risk_level, result.overall_risk_score = self._calculate_overall_risk(all_risks)

            # Step 7: 生成预警
            result.alerts = self._generate_alerts(all_risks)

            # Step 8: 分析趋势
            result.trends = await self._analyze_risk_trends(project_id, historical_days)

            # Step 9: Top风险排名
            result.top_risks = self._rank_top_risks(all_risks, top_n=5)

            # Step 10: 生成应对计划
            result.mitigation_plan = self._generate_mitigation_plan(result.top_risks)

            # Step 11: AI洞察（可选）
            if include_ai_insights:
                result.ai_insights = await self._generate_ai_insights(project_id, result)

            # 记录完成
            self._complete_workflow(workflow_log, result, start_time)

            logger.info(f"项目 {project_id} 风险分析完成，识别 {result.total_risks} 个风险")

            return {
                "success": True,
                "project_id": project_id,
                "result": asdict(result),
                "metadata": {
                    "analysis_time": (datetime.now() - start_time).total_seconds(),
                    "overall_risk_level": result.overall_risk_level,
                    "total_risks": result.total_risks,
                    "alerts_count": len(result.alerts)
                }
            }

        except Exception as e:
            logger.error(f"风险分析失败: {str(e)}")
            self._fail_workflow(workflow_log, str(e))
            return {
                "success": False,
                "project_id": project_id,
                "error": str(e)
            }

    # =========================================
    # 风险扫描方法
    # =========================================

    async def _scan_progress_risks(self, project_id: str) -> List[RiskItem]:
        """扫描进度风险"""
        risks = []
        thresholds = self.THRESHOLDS["progress"]

        try:
            # 获取进度数据
            status = self.progress_tools.get_progress_status(project_id)
            overview = self.progress_tools.get_project_overview(project_id)
            delayed_tasks = self.progress_tools.get_delayed_tasks(project_id)
            critical_tasks = self.progress_tools.get_critical_path_tasks(project_id)
            prediction = self.progress_tools.predict_completion_time(project_id)

            spi = status.get("overall_spi", 1.0) or 1.0
            delayed_count = overview.get("delayed_tasks", 0)
            critical_delayed = len([t for t in critical_tasks if t.get("is_delayed", False)])

            # 风险1: SPI过低
            if spi < thresholds["spi_critical"]:
                risks.append(self._create_risk(
                    category="progress",
                    level="critical",
                    title="进度严重滞后",
                    description=f"SPI={spi:.2f}，远低于计划进度",
                    impact="项目可能无法按时完成，需要大幅调整计划",
                    probability=0.9,
                    impact_score=0.9,
                    indicators={"spi": spi},
                    recommendations=[
                        "立即召开进度协调会",
                        "增加资源投入或调整计划",
                        "考虑缩减范围或延期"
                    ]
                ))
            elif spi < thresholds["spi_high"]:
                risks.append(self._create_risk(
                    category="progress",
                    level="high",
                    title="进度明显落后",
                    description=f"SPI={spi:.2f}，进度落后于计划",
                    impact="可能导致项目延期",
                    probability=0.7,
                    impact_score=0.7,
                    indicators={"spi": spi},
                    recommendations=[
                        "分析延期原因",
                        "制定赶工计划",
                        "优化资源配置"
                    ]
                ))
            elif spi < thresholds["spi_medium"]:
                risks.append(self._create_risk(
                    category="progress",
                    level="medium",
                    title="进度轻微落后",
                    description=f"SPI={spi:.2f}，略低于计划",
                    impact="需要关注，防止进一步恶化",
                    probability=0.5,
                    impact_score=0.5,
                    indicators={"spi": spi},
                    recommendations=["持续监控进度", "及时处理延期任务"]
                ))

            # 风险2: 大量任务延期
            if delayed_count >= thresholds["delayed_tasks_critical"]:
                risks.append(self._create_risk(
                    category="progress",
                    level="critical",
                    title="大量任务延期",
                    description=f"共有{delayed_count}个任务延期",
                    impact="项目进度失控风险",
                    probability=0.85,
                    impact_score=0.8,
                    indicators={"delayed_tasks": delayed_count},
                    recommendations=[
                        "逐一分析延期原因",
                        "重新评估任务优先级",
                        "考虑任务并行处理"
                    ]
                ))
            elif delayed_count >= thresholds["delayed_tasks_high"]:
                risks.append(self._create_risk(
                    category="progress",
                    level="high",
                    title="多个任务延期",
                    description=f"共有{delayed_count}个任务延期",
                    impact="可能影响后续任务",
                    probability=0.65,
                    impact_score=0.6,
                    indicators={"delayed_tasks": delayed_count},
                    recommendations=["重点关注延期任务", "加强进度跟踪"]
                ))

            # 风险3: 关键路径任务延期
            if critical_delayed >= thresholds["critical_path_delayed"]:
                risks.append(self._create_risk(
                    category="progress",
                    level="critical",
                    title="关键路径任务延期",
                    description=f"关键路径上有{critical_delayed}个任务延期",
                    impact="直接影响项目完成日期",
                    probability=0.95,
                    impact_score=0.95,
                    indicators={"critical_delayed": critical_delayed},
                    recommendations=[
                        "优先保障关键路径资源",
                        "考虑赶工或快速跟进",
                        "评估工期延长可能性"
                    ]
                ))

            # 风险4: 预测延期
            predicted_delay = prediction.get("predicted_delay_days", 0)
            if predicted_delay and predicted_delay > 30:
                risks.append(self._create_risk(
                    category="progress",
                    level="high",
                    title="预计项目延期",
                    description=f"按当前进度预测将延期约{predicted_delay}天",
                    impact="需要提前沟通和调整计划",
                    probability=0.7,
                    impact_score=0.7,
                    indicators={"predicted_delay_days": predicted_delay},
                    recommendations=[
                        "提前与相关方沟通",
                        "评估加速可能性",
                        "准备应急预案"
                    ]
                ))

        except Exception as e:
            logger.warning(f"扫描进度风险异常: {e}")

        return risks

    async def _scan_cost_risks(self, project_id: str) -> List[RiskItem]:
        """扫描成本风险"""
        risks = []
        thresholds = self.THRESHOLDS["cost"]

        try:
            # 获取成本数据
            overview = self.cost_tools.get_cost_overview(project_id)
            overruns = self.cost_tools.identify_cost_overruns(project_id)
            prediction = self.cost_tools.predict_final_cost(project_id)

            cpi = overview.get("cpi", 1.0) or 1.0
            variance_rate = abs(overview.get("variance_rate", 0))
            budget_usage = overview.get("budget_usage_rate", 0)

            # 风险1: CPI过低
            if cpi < thresholds["cpi_critical"]:
                risks.append(self._create_risk(
                    category="cost",
                    level="critical",
                    title="成本严重超支",
                    description=f"CPI={cpi:.2f}，成本控制失效",
                    impact="项目预算可能大幅超支",
                    probability=0.9,
                    impact_score=0.9,
                    indicators={"cpi": cpi, "variance_rate": variance_rate},
                    recommendations=[
                        "立即开展成本审计",
                        "暂停非必要支出",
                        "申请追加预算或调整范围"
                    ]
                ))
            elif cpi < thresholds["cpi_high"]:
                risks.append(self._create_risk(
                    category="cost",
                    level="high",
                    title="成本超支风险",
                    description=f"CPI={cpi:.2f}，成本超出计划",
                    impact="预算可能不足",
                    probability=0.7,
                    impact_score=0.7,
                    indicators={"cpi": cpi},
                    recommendations=[
                        "分析超支原因",
                        "加强成本控制",
                        "优化采购策略"
                    ]
                ))
            elif cpi < thresholds["cpi_medium"]:
                risks.append(self._create_risk(
                    category="cost",
                    level="medium",
                    title="成本偏差",
                    description=f"CPI={cpi:.2f}，成本略有超支",
                    impact="需要加强监控",
                    probability=0.5,
                    impact_score=0.5,
                    indicators={"cpi": cpi},
                    recommendations=["加强成本监控", "控制变更"]
                ))

            # 风险2: 偏差率过高
            if variance_rate >= thresholds["variance_rate_critical"]:
                risks.append(self._create_risk(
                    category="cost",
                    level="critical",
                    title="成本偏差严重",
                    description=f"成本偏差率{variance_rate:.1f}%",
                    impact="预算控制失败风险",
                    probability=0.85,
                    impact_score=0.85,
                    indicators={"variance_rate": variance_rate},
                    recommendations=[
                        "深入分析偏差来源",
                        "制定成本削减计划"
                    ]
                ))
            elif variance_rate >= thresholds["variance_rate_high"]:
                risks.append(self._create_risk(
                    category="cost",
                    level="high",
                    title="成本偏差较大",
                    description=f"成本偏差率{variance_rate:.1f}%",
                    impact="预算压力增大",
                    probability=0.65,
                    impact_score=0.65,
                    indicators={"variance_rate": variance_rate},
                    recommendations=["严格控制支出", "审查合同和变更"]
                ))

            # 风险3: 预测超支
            will_exceed = prediction.get("will_exceed_budget", False)
            overrun_rate = prediction.get("predicted_overrun_rate", 0)
            if will_exceed and overrun_rate > 10:
                risks.append(self._create_risk(
                    category="cost",
                    level="high",
                    title="预计预算超支",
                    description=f"预计最终超支{overrun_rate:.1f}%",
                    impact="需要提前申请追加预算",
                    probability=0.75,
                    impact_score=0.7,
                    indicators={"predicted_overrun_rate": overrun_rate},
                    recommendations=[
                        "提前申请预算调整",
                        "评估范围缩减可能"
                    ]
                ))

            # 风险4: 具体超支项
            for overrun in overruns[:3]:  # 取前3个最严重的
                item_variance = overrun.get("variance_rate", 0)
                if item_variance > 20:
                    risks.append(self._create_risk(
                        category="cost",
                        level="high" if item_variance > 30 else "medium",
                        title=f"{overrun.get('cost_item', '未知项目')}超支",
                        description=f"该项目超支{item_variance:.1f}%",
                        impact="影响整体成本控制",
                        probability=0.6,
                        impact_score=0.5,
                        indicators={"item": overrun.get('cost_item'), "variance_rate": item_variance},
                        recommendations=[f"审查{overrun.get('cost_item')}相关支出"]
                    ))

        except Exception as e:
            logger.warning(f"扫描成本风险异常: {e}")

        return risks

    async def _scan_safety_risks(self, project_id: str) -> List[RiskItem]:
        """扫描安全风险"""
        risks = []
        thresholds = self.THRESHOLDS["safety"]

        try:
            # 获取安全数据
            overview = self.safety_tools.get_safety_overview(project_id, days=30)
            frequent = self.safety_tools.identify_frequent_issues(project_id, days=60)
            open_defects = self.safety_tools.get_open_defects(project_id)
            safety_risks = self.safety_tools.identify_safety_risks(project_id)

            high_defects = overview.get("high_level_defects", 0)
            open_count = overview.get("open_defects", 0)
            pass_rate = overview.get("pass_rate", 100)

            # 风险1: 高级别隐患过多
            if high_defects >= thresholds["high_defects_critical"]:
                risks.append(self._create_risk(
                    category="safety",
                    level="critical",
                    title="高级别安全隐患严重",
                    description=f"存在{high_defects}个高级别安全隐患",
                    impact="可能引发安全事故",
                    probability=0.9,
                    impact_score=0.95,
                    indicators={"high_defects": high_defects},
                    recommendations=[
                        "立即停工整改高危隐患",
                        "召开安全专题会议",
                        "加强安全检查频次"
                    ]
                ))
            elif high_defects >= thresholds["high_defects_high"]:
                risks.append(self._create_risk(
                    category="safety",
                    level="high",
                    title="高级别安全隐患",
                    description=f"存在{high_defects}个高级别安全隐患",
                    impact="安全风险较高",
                    probability=0.7,
                    impact_score=0.8,
                    indicators={"high_defects": high_defects},
                    recommendations=[
                        "优先整改高级别隐患",
                        "加强安全教育培训"
                    ]
                ))

            # 风险2: 未关闭问题积压
            if open_count >= thresholds["open_defects_critical"]:
                risks.append(self._create_risk(
                    category="safety",
                    level="critical",
                    title="安全问题积压严重",
                    description=f"有{open_count}个安全问题未关闭",
                    impact="安全管理失控风险",
                    probability=0.8,
                    impact_score=0.8,
                    indicators={"open_defects": open_count},
                    recommendations=[
                        "制定整改攻坚计划",
                        "落实整改责任人",
                        "建立每日销项机制"
                    ]
                ))
            elif open_count >= thresholds["open_defects_high"]:
                risks.append(self._create_risk(
                    category="safety",
                    level="high",
                    title="安全问题积压",
                    description=f"有{open_count}个安全问题未关闭",
                    impact="需要加快整改进度",
                    probability=0.65,
                    impact_score=0.65,
                    indicators={"open_defects": open_count},
                    recommendations=["加快整改进度", "增加整改资源"]
                ))

            # 风险3: 合格率过低
            if pass_rate < thresholds["pass_rate_critical"]:
                risks.append(self._create_risk(
                    category="safety",
                    level="critical",
                    title="安全合格率过低",
                    description=f"安全检查合格率仅{pass_rate:.1f}%",
                    impact="现场安全管理严重不足",
                    probability=0.85,
                    impact_score=0.85,
                    indicators={"pass_rate": pass_rate},
                    recommendations=[
                        "开展全面安全整治",
                        "追究安全责任"
                    ]
                ))
            elif pass_rate < thresholds["pass_rate_high"]:
                risks.append(self._create_risk(
                    category="safety",
                    level="high",
                    title="安全合格率偏低",
                    description=f"安全检查合格率{pass_rate:.1f}%",
                    impact="安全管理需要加强",
                    probability=0.6,
                    impact_score=0.6,
                    indicators={"pass_rate": pass_rate},
                    recommendations=["加强现场安全管理", "完善安全制度"]
                ))

            # 风险4: 频发问题
            for issue in frequent[:2]:  # 取前2个
                if issue.get("trend") == "上升" and issue.get("total_count", 0) > 5:
                    risks.append(self._create_risk(
                        category="safety",
                        level="high",
                        title=f"'{issue.get('defect_type')}'问题频发",
                        description=f"该类问题出现{issue.get('total_count')}次且呈上升趋势",
                        impact="系统性安全管理漏洞",
                        probability=0.7,
                        impact_score=0.65,
                        indicators={"defect_type": issue.get('defect_type'), "count": issue.get('total_count')},
                        recommendations=[
                            f"专项整治'{issue.get('defect_type')}'问题",
                            "分析根本原因",
                            "制定防范措施"
                        ]
                    ))

        except Exception as e:
            logger.warning(f"扫描安全风险异常: {e}")

        return risks

    # =========================================
    # 风险评估方法
    # =========================================

    def _create_risk(
            self,
            category: str,
            level: str,
            title: str,
            description: str,
            impact: str,
            probability: float,
            impact_score: float,
            indicators: Dict,
            recommendations: List[str]
    ) -> RiskItem:
        """创建风险项"""
        self._risk_counter += 1
        return RiskItem(
            risk_id=f"RISK-{self._risk_counter:04d}",
            category=category,
            level=level,
            status="active",
            title=title,
            description=description,
            impact=impact,
            probability=probability,
            impact_score=impact_score,
            risk_score=round(probability * impact_score, 2),
            indicators=indicators,
            recommendations=recommendations,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

    def _calculate_overall_risk(self, risks: List[RiskItem]) -> Tuple[str, float]:
        """计算综合风险等级和分数"""
        if not risks:
            return "low", 0.0

        # 按等级加权计算
        level_weights = {
            "critical": 1.0,
            "high": 0.7,
            "medium": 0.4,
            "low": 0.1
        }

        total_score = sum(
            r.risk_score * level_weights.get(r.level, 0.5)
            for r in risks
        )

        # 归一化分数
        max_possible = len(risks) * 1.0  # 假设最大权重为1.0
        normalized_score = min(total_score / max_possible, 1.0) if max_possible > 0 else 0.0

        # 确定等级
        critical_count = len([r for r in risks if r.level == "critical"])
        high_count = len([r for r in risks if r.level == "high"])

        if critical_count >= 2 or (critical_count >= 1 and high_count >= 2):
            level = "critical"
        elif critical_count >= 1 or high_count >= 3:
            level = "high"
        elif high_count >= 1 or normalized_score > 0.4:
            level = "medium"
        else:
            level = "low"

        return level, round(normalized_score * 100, 1)

    def _generate_alerts(self, risks: List[RiskItem]) -> List[RiskAlert]:
        """生成风险预警"""
        alerts = []

        for risk in risks:
            if risk.level in ["critical", "high"]:
                alert = RiskAlert(
                    alert_id=f"ALERT-{risk.risk_id}",
                    risk_id=risk.risk_id,
                    level=risk.level,
                    title=f"【{risk.level.upper()}】{risk.title}",
                    message=risk.description,
                    triggered_at=datetime.now().isoformat(),
                    acknowledged=False
                )
                alerts.append(alert)

        return alerts

    async def _analyze_risk_trends(self, project_id: str, days: int) -> List[RiskTrend]:
        """分析风险趋势"""
        trends = []

        try:
            # 进度趋势
            progress_trend = self.progress_tools.analyze_progress_trend(project_id, days=days)
            trends.append(RiskTrend(
                category="progress",
                current_level=progress_trend.get("risk_level", "unknown"),
                trend=self._map_trend(progress_trend.get("trend", "平稳")),
                key_changes=[f"高风险任务数: {progress_trend.get('high_risk_tasks', 0)}"]
            ))

            # 成本趋势
            cost_trend = self.cost_tools.analyze_cost_trend(project_id, months=1)
            trends.append(RiskTrend(
                category="cost",
                trend=self._map_trend(cost_trend.get("trend", "平稳")),
                key_changes=[f"成本增长率: {cost_trend.get('growth_rate', 0):.1f}%"]
            ))

            # 安全趋势
            safety_trend = self.safety_tools.analyze_safety_trend(project_id, months=1)
            trends.append(RiskTrend(
                category="safety",
                trend=self._map_trend(safety_trend.get("overall_trend", "平稳")),
                key_changes=[f"缺陷趋势: {safety_trend.get('defect_trend', '平稳')}"]
            ))

        except Exception as e:
            logger.warning(f"分析风险趋势异常: {e}")

        return trends

    def _map_trend(self, trend_str: str) -> str:
        """映射趋势描述"""
        mapping = {
            "上升": "deteriorating",
            "恶化": "deteriorating",
            "下降": "improving",
            "好转": "improving",
            "平稳": "stable"
        }
        return mapping.get(trend_str, "stable")

    def _rank_top_risks(self, risks: List[RiskItem], top_n: int = 5) -> List[RiskItem]:
        """排名Top风险"""
        # 按风险分数排序
        sorted_risks = sorted(risks, key=lambda r: r.risk_score, reverse=True)
        return sorted_risks[:top_n]

    def _generate_mitigation_plan(self, top_risks: List[RiskItem]) -> List[Dict]:
        """生成应对计划"""
        plan = []

        priority_map = {"critical": "P0-立即", "high": "P1-本周", "medium": "P2-本月", "low": "P3-持续"}
        owner_map = {"progress": "项目经理", "cost": "商务经理", "safety": "安全主管"}

        for risk in top_risks:
            plan.append({
                "risk_id": risk.risk_id,
                "risk_title": risk.title,
                "priority": priority_map.get(risk.level, "P2-本月"),
                "owner": owner_map.get(risk.category, "项目经理"),
                "actions": risk.recommendations,
                "deadline": self._calculate_deadline(risk.level),
                "status": "待处理"
            })

        return plan

    def _calculate_deadline(self, level: str) -> str:
        """计算处理期限"""
        days_map = {"critical": 1, "high": 3, "medium": 7, "low": 14}
        days = days_map.get(level, 7)
        deadline = date.today() + timedelta(days=days)
        return deadline.isoformat()

    async def _generate_ai_insights(
            self,
            project_id: str,
            result: RiskAnalysisResult
    ) -> List[str]:
        """生成AI洞察"""
        insights = []

        try:
            # 构建上下文
            context = f"""
            项目风险概况：
            - 总风险数：{result.total_risks}
            - 紧急风险：{result.critical_risks}
            - 高风险：{result.high_risks}
            - 综合风险等级：{result.overall_risk_level}

            主要问题：
            {', '.join([r.title for r in result.top_risks[:3]])}
            """

            # 查询改进建议
            rag_result = await run_rag(
                query="项目风险管理最佳实践和应对措施",
                top_k=3,
                project_id=project_id,
                extra_context=context
            )

            if rag_result.get("answer"):
                insights.append(f"【风险管理建议】{rag_result['answer'][:300]}")

            # 针对具体风险类型的建议
            if result.critical_risks > 0 or result.high_risks > 2:
                rag_result = await run_rag(
                    query="紧急风险处理方法和escalation流程",
                    top_k=2,
                    project_id=project_id
                )
                if rag_result.get("answer"):
                    insights.append(f"【紧急处理建议】{rag_result['answer'][:200]}")

        except Exception as e:
            logger.warning(f"生成AI洞察失败: {e}")

        return insights

    # =========================================
    # 快速分析方法
    # =========================================

    async def quick_scan(self, project_id: str) -> Dict[str, Any]:
        """
        快速风险扫描（轻量级）

        只返回关键指标和预警，不包含详细分析
        """
        try:
            # 获取核心指标
            progress_status = self.progress_tools.get_progress_status(project_id)
            cost_overview = self.cost_tools.get_cost_overview(project_id)
            safety_overview = self.safety_tools.get_safety_overview(project_id, days=7)

            # 计算风险等级
            risk_levels = {
                "progress": progress_status.get("risk_level", "green"),
                "cost": cost_overview.get("risk_level", "green"),
                "safety": safety_overview.get("risk_level", "green")
            }

            # 确定最高风险
            level_priority = {"red": 0, "yellow": 1, "green": 2}
            highest_risk = min(risk_levels.items(), key=lambda x: level_priority.get(x[1], 2))

            # 生成简要预警
            alerts = []
            if risk_levels["progress"] == "red":
                alerts.append("⚠️ 进度严重滞后")
            if risk_levels["cost"] == "red":
                alerts.append("⚠️ 成本严重超支")
            if risk_levels["safety"] == "red":
                alerts.append("⚠️ 安全隐患严重")

            return {
                "success": True,
                "project_id": project_id,
                "scan_time": datetime.now().isoformat(),
                "risk_levels": risk_levels,
                "highest_risk_category": highest_risk[0],
                "highest_risk_level": highest_risk[1],
                "alerts": alerts,
                "metrics": {
                    "spi": progress_status.get("overall_spi"),
                    "cpi": cost_overview.get("cpi"),
                    "safety_pass_rate": safety_overview.get("pass_rate")
                }
            }

        except Exception as e:
            return {
                "success": False,
                "project_id": project_id,
                "error": str(e)
            }

    # =========================================
    # 工作流日志方法
    # =========================================

    def _start_workflow(self, project_id: str, workflow_type: str) -> Optional[AgentWorkflowLog]:
        """开始工作流日志"""
        try:
            log = AgentWorkflowLog(
                project_id=project_id,
                workflow_type=workflow_type,
                start_time=datetime.now(),
                status="running",
                input_params=json.dumps({"project_id": project_id})
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            return log
        except Exception as e:
            logger.warning(f"记录工作流开始失败: {e}")
            return None

    def _complete_workflow(
            self,
            log: Optional[AgentWorkflowLog],
            result: Any,
            start_time: datetime
    ):
        """完成工作流日志"""
        if log:
            try:
                log.end_time = datetime.now()
                log.status = "completed"
                # 只存储摘要信息
                summary = {
                    "total_risks": result.total_risks if hasattr(result, 'total_risks') else 0,
                    "overall_level": result.overall_risk_level if hasattr(result, 'overall_risk_level') else "unknown",
                    "alerts_count": len(result.alerts) if hasattr(result, 'alerts') else 0
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


# =========================================
# 工厂函数
# =========================================

def get_risk_agent(db: Session) -> RiskAnalysisAgent:
    """工厂函数：创建风险分析Agent实例"""
    return RiskAnalysisAgent(db)