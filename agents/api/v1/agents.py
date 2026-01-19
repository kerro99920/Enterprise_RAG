"""
========================================
Agent 调度 API 接口
========================================

📚 模块说明：
- Agent 触发和调度接口
- 支持周报生成、风险分析、成本分析等
- 异步执行和状态查询

🎯 核心功能：
1. 周报生成接口
2. 风险分析接口
3. 成本分析接口
4. 进度分析接口
5. 安全分析接口
6. 快速风险扫描
7. 工作流状态查询

========================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum

from loguru import logger
from core.database import get_db

# 导入 Agents
from agents.weekly_report_agent import WeeklyReportAgent, ReportFormat, get_weekly_report_agent
from agents.risk_agent import RiskAnalysisAgent, get_risk_agent

# 导入 Tools
from tools.progress_tools import get_progress_tools
from tools.cost_tools import get_cost_tools
from tools.safety_tools import get_safety_tools

# 导入模型
from models.project import AgentWorkflowLog

router = APIRouter()


# =========================================
# 枚举和请求/响应模型
# =========================================

class AgentType(str, Enum):
    """Agent类型"""
    WEEKLY_REPORT = "weekly_report"
    RISK_ANALYSIS = "risk_analysis"
    COST_ANALYSIS = "cost_analysis"
    PROGRESS_ANALYSIS = "progress_analysis"
    SAFETY_ANALYSIS = "safety_analysis"


class ReportFormatEnum(str, Enum):
    """报告格式"""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class WeeklyReportRequest(BaseModel):
    """周报生成请求"""
    project_id: str = Field(..., description="项目ID")
    format: ReportFormatEnum = Field(ReportFormatEnum.MARKDOWN, description="输出格式")
    include_ai_suggestions: bool = Field(True, description="是否包含AI建议")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "P001",
                "format": "markdown",
                "include_ai_suggestions": True
            }
        }


class RiskAnalysisRequest(BaseModel):
    """风险分析请求"""
    project_id: str = Field(..., description="项目ID")
    include_ai_insights: bool = Field(True, description="是否包含AI洞察")
    historical_days: int = Field(30, ge=7, le=90, description="历史数据分析天数")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "P001",
                "include_ai_insights": True,
                "historical_days": 30
            }
        }


class CostAnalysisRequest(BaseModel):
    """成本分析请求"""
    project_id: str = Field(..., description="项目ID")
    analysis_months: int = Field(3, ge=1, le=12, description="分析月数")


class ProgressAnalysisRequest(BaseModel):
    """进度分析请求"""
    project_id: str = Field(..., description="项目ID")
    analysis_days: int = Field(30, ge=7, le=90, description="分析天数")


class SafetyAnalysisRequest(BaseModel):
    """安全分析请求"""
    project_id: str = Field(..., description="项目ID")
    analysis_days: int = Field(30, ge=7, le=90, description="分析天数")


class AgentResponse(BaseModel):
    """Agent响应"""
    success: bool = Field(..., description="是否成功")
    agent_type: str = Field(..., description="Agent类型")
    project_id: str = Field(..., description="项目ID")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间(秒)")


class WorkflowLogResponse(BaseModel):
    """工作流日志响应"""
    log_id: int
    project_id: Optional[str]
    workflow_type: Optional[str]
    status: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    duration_seconds: Optional[float]
    error_message: Optional[str]


class QuickScanResponse(BaseModel):
    """快速扫描响应"""
    success: bool
    project_id: str
    scan_time: str
    risk_levels: Dict[str, str]
    highest_risk_category: str
    highest_risk_level: str
    alerts: List[str]
    metrics: Dict[str, Any]


# =========================================
# 周报生成接口
# =========================================

@router.post(
    "/weekly-report",
    response_model=AgentResponse,
    summary="生成项目周报",
    description="调用周报Agent生成项目周报，支持Markdown/JSON/HTML格式"
)
async def generate_weekly_report(
        request: WeeklyReportRequest,
        db: Session = Depends(get_db)
):
    """
    生成项目周报

    功能：
    - 聚合进度、成本、安全三大模块数据
    - 分析关键风险和问题
    - 生成行动项和下周计划
    - 可选AI建议
    """
    start_time = datetime.now()

    try:
        logger.info(f"开始生成周报: project_id={request.project_id}")

        # 创建Agent实例
        agent = get_weekly_report_agent(db)

        # 映射格式
        format_map = {
            ReportFormatEnum.MARKDOWN: ReportFormat.MARKDOWN,
            ReportFormatEnum.JSON: ReportFormat.JSON,
            ReportFormatEnum.HTML: ReportFormat.HTML
        }
        report_format = format_map.get(request.format, ReportFormat.MARKDOWN)

        # 执行生成
        result = await agent.generate_report(
            project_id=request.project_id,
            report_format=report_format,
            include_ai_suggestions=request.include_ai_suggestions
        )

        execution_time = (datetime.now() - start_time).total_seconds()

        return AgentResponse(
            success=result.get("success", False),
            agent_type=AgentType.WEEKLY_REPORT.value,
            project_id=request.project_id,
            result=result,
            execution_time=execution_time
        )

    except Exception as e:
        logger.error(f"生成周报失败: {e}")
        return AgentResponse(
            success=False,
            agent_type=AgentType.WEEKLY_REPORT.value,
            project_id=request.project_id,
            error=str(e),
            execution_time=(datetime.now() - start_time).total_seconds()
        )


# =========================================
# 风险分析接口
# =========================================

@router.post(
    "/risk-analysis",
    response_model=AgentResponse,
    summary="执行风险分析",
    description="调用风险Agent进行多维度风险分析"
)
async def analyze_risks(
        request: RiskAnalysisRequest,
        db: Session = Depends(get_db)
):
    """
    执行风险分析

    功能：
    - 扫描进度、成本、安全风险
    - 量化风险等级和影响
    - 生成预警和应对建议
    - 可选AI洞察
    """
    start_time = datetime.now()

    try:
        logger.info(f"开始风险分析: project_id={request.project_id}")

        # 创建Agent实例
        agent = get_risk_agent(db)

        # 执行分析
        result = await agent.analyze_risks(
            project_id=request.project_id,
            include_ai_insights=request.include_ai_insights,
            historical_days=request.historical_days
        )

        execution_time = (datetime.now() - start_time).total_seconds()

        return AgentResponse(
            success=result.get("success", False),
            agent_type=AgentType.RISK_ANALYSIS.value,
            project_id=request.project_id,
            result=result,
            execution_time=execution_time
        )

    except Exception as e:
        logger.error(f"风险分析失败: {e}")
        return AgentResponse(
            success=False,
            agent_type=AgentType.RISK_ANALYSIS.value,
            project_id=request.project_id,
            error=str(e),
            execution_time=(datetime.now() - start_time).total_seconds()
        )


@router.get(
    "/risk-analysis/{project_id}/quick-scan",
    response_model=QuickScanResponse,
    summary="快速风险扫描",
    description="轻量级风险扫描，快速获取风险概况"
)
async def quick_risk_scan(
        project_id: str,
        db: Session = Depends(get_db)
):
    """
    快速风险扫描（轻量级）

    适用场景：
    - 仪表盘实时展示
    - 定期自动扫描
    - 快速检查项目状态
    """
    try:
        agent = get_risk_agent(db)
        result = await agent.quick_scan(project_id)

        if result.get("success"):
            return QuickScanResponse(**result)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "快速扫描失败")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"快速扫描失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# =========================================
# 成本分析接口
# =========================================

@router.post(
    "/cost-analysis",
    response_model=AgentResponse,
    summary="执行成本分析",
    description="调用成本工具进行成本分析"
)
async def analyze_costs(
        request: CostAnalysisRequest,
        db: Session = Depends(get_db)
):
    """
    执行成本分析

    功能：
    - 成本概览和CPI计算
    - 分类成本统计
    - 超支项识别
    - 成本趋势分析
    - 控制建议生成
    """
    start_time = datetime.now()

    try:
        logger.info(f"开始成本分析: project_id={request.project_id}")

        # 使用成本工具
        cost_tools = get_cost_tools(db)

        # 聚合分析结果
        result = {
            "overview": cost_tools.get_cost_overview(request.project_id),
            "by_category": cost_tools.get_cost_by_category(request.project_id),
            "overruns": cost_tools.identify_cost_overruns(request.project_id),
            "prediction": cost_tools.predict_final_cost(request.project_id),
            "trend": cost_tools.analyze_cost_trend(request.project_id, months=request.analysis_months),
            "risks": cost_tools.identify_cost_risks(request.project_id),
            "suggestions": cost_tools.get_cost_control_suggestions(request.project_id)
        }

        execution_time = (datetime.now() - start_time).total_seconds()

        return AgentResponse(
            success=True,
            agent_type=AgentType.COST_ANALYSIS.value,
            project_id=request.project_id,
            result=result,
            execution_time=execution_time
        )

    except Exception as e:
        logger.error(f"成本分析失败: {e}")
        return AgentResponse(
            success=False,
            agent_type=AgentType.COST_ANALYSIS.value,
            project_id=request.project_id,
            error=str(e),
            execution_time=(datetime.now() - start_time).total_seconds()
        )


# =========================================
# 进度分析接口
# =========================================

@router.post(
    "/progress-analysis",
    response_model=AgentResponse,
    summary="执行进度分析",
    description="调用进度工具进行进度分析"
)
async def analyze_progress(
        request: ProgressAnalysisRequest,
        db: Session = Depends(get_db)
):
    """
    执行进度分析

    功能：
    - 项目概览和SPI计算
    - 延期任务识别
    - 关键路径分析
    - 进度趋势分析
    - 完成时间预测
    """
    start_time = datetime.now()

    try:
        logger.info(f"开始进度分析: project_id={request.project_id}")

        # 使用进度工具
        progress_tools = get_progress_tools(db)

        # 聚合分析结果
        result = {
            "overview": progress_tools.get_project_overview(request.project_id),
            "status": progress_tools.get_progress_status(request.project_id),
            "delayed_tasks": progress_tools.get_delayed_tasks(request.project_id),
            "critical_path": progress_tools.get_critical_path_tasks(request.project_id),
            "trend": progress_tools.analyze_progress_trend(request.project_id, days=request.analysis_days),
            "prediction": progress_tools.predict_completion_time(request.project_id)
        }

        execution_time = (datetime.now() - start_time).total_seconds()

        return AgentResponse(
            success=True,
            agent_type=AgentType.PROGRESS_ANALYSIS.value,
            project_id=request.project_id,
            result=result,
            execution_time=execution_time
        )

    except Exception as e:
        logger.error(f"进度分析失败: {e}")
        return AgentResponse(
            success=False,
            agent_type=AgentType.PROGRESS_ANALYSIS.value,
            project_id=request.project_id,
            error=str(e),
            execution_time=(datetime.now() - start_time).total_seconds()
        )


# =========================================
# 安全分析接口
# =========================================

@router.post(
    "/safety-analysis",
    response_model=AgentResponse,
    summary="执行安全分析",
    description="调用安全工具进行安全分析"
)
async def analyze_safety(
        request: SafetyAnalysisRequest,
        db: Session = Depends(get_db)
):
    """
    执行安全分析

    功能：
    - 安全概览和合格率
    - 频发问题识别
    - 未关闭问题列表
    - 安全趋势分析
    - 整改计划生成
    """
    start_time = datetime.now()

    try:
        logger.info(f"开始安全分析: project_id={request.project_id}")

        # 使用安全工具
        safety_tools = get_safety_tools(db)

        # 聚合分析结果
        result = {
            "overview": safety_tools.get_safety_overview(request.project_id, days=request.analysis_days),
            "frequent_issues": safety_tools.identify_frequent_issues(request.project_id, days=60),
            "distribution": safety_tools.analyze_defect_distribution(request.project_id),
            "open_defects": safety_tools.get_open_defects(request.project_id),
            "trend": safety_tools.analyze_safety_trend(request.project_id, months=2),
            "risks": safety_tools.identify_safety_risks(request.project_id),
            "suggestions": safety_tools.get_improvement_suggestions(request.project_id),
            "rectification_plan": safety_tools.get_rectification_plan(request.project_id)
        }

        execution_time = (datetime.now() - start_time).total_seconds()

        return AgentResponse(
            success=True,
            agent_type=AgentType.SAFETY_ANALYSIS.value,
            project_id=request.project_id,
            result=result,
            execution_time=execution_time
        )

    except Exception as e:
        logger.error(f"安全分析失败: {e}")
        return AgentResponse(
            success=False,
            agent_type=AgentType.SAFETY_ANALYSIS.value,
            project_id=request.project_id,
            error=str(e),
            execution_time=(datetime.now() - start_time).total_seconds()
        )


# =========================================
# 工作流日志查询
# =========================================

@router.get(
    "/workflows",
    response_model=List[WorkflowLogResponse],
    summary="查询工作流日志",
    description="查询Agent执行的历史记录"
)
async def get_workflow_logs(
        project_id: Optional[str] = Query(None, description="项目ID筛选"),
        workflow_type: Optional[str] = Query(None, description="工作流类型筛选"),
        status: Optional[str] = Query(None, description="状态筛选"),
        limit: int = Query(20, ge=1, le=100, description="返回数量"),
        db: Session = Depends(get_db)
):
    """
    查询工作流日志

    支持按项目ID、工作流类型、状态筛选
    """
    try:
        query = db.query(AgentWorkflowLog)

        if project_id:
            query = query.filter(AgentWorkflowLog.project_id == project_id)
        if workflow_type:
            query = query.filter(AgentWorkflowLog.workflow_type == workflow_type)
        if status:
            query = query.filter(AgentWorkflowLog.status == status)

        logs = query.order_by(AgentWorkflowLog.created_at.desc()).limit(limit).all()

        result = []
        for log in logs:
            result.append(WorkflowLogResponse(
                log_id=log.log_id,
                project_id=log.project_id,
                workflow_type=log.workflow_type,
                status=log.status,
                start_time=log.start_time.isoformat() if log.start_time else None,
                end_time=log.end_time.isoformat() if log.end_time else None,
                duration_seconds=log.duration_seconds,
                error_message=log.error_message
            ))

        return result

    except Exception as e:
        logger.error(f"查询工作流日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/workflows/{log_id}",
    response_model=Dict[str, Any],
    summary="查询单个工作流详情",
    description="获取工作流的详细执行结果"
)
async def get_workflow_detail(
        log_id: int,
        db: Session = Depends(get_db)
):
    """
    查询单个工作流详情

    返回完整的输入参数和执行结果
    """
    try:
        log = db.query(AgentWorkflowLog).filter(
            AgentWorkflowLog.log_id == log_id
        ).first()

        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"工作流日志 {log_id} 不存在"
            )

        import json

        return {
            "log_id": log.log_id,
            "project_id": log.project_id,
            "workflow_type": log.workflow_type,
            "status": log.status,
            "start_time": log.start_time.isoformat() if log.start_time else None,
            "end_time": log.end_time.isoformat() if log.end_time else None,
            "duration_seconds": log.duration_seconds,
            "input_params": json.loads(log.input_params) if log.input_params else None,
            "output_result": json.loads(log.output_result) if log.output_result else None,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询工作流详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# =========================================
# 综合分析接口（聚合多个分析）
# =========================================

@router.get(
    "/dashboard/{project_id}",
    response_model=Dict[str, Any],
    summary="项目仪表盘数据",
    description="一次性获取项目的关键指标，用于仪表盘展示"
)
async def get_dashboard_data(
        project_id: str,
        db: Session = Depends(get_db)
):
    """
    获取项目仪表盘数据

    聚合关键指标：
    - 进度指标（SPI、延期任务数）
    - 成本指标（CPI、偏差率）
    - 安全指标（合格率、未关闭问题数）
    - 风险等级汇总
    """
    try:
        # 初始化工具
        progress_tools = get_progress_tools(db)
        cost_tools = get_cost_tools(db)
        safety_tools = get_safety_tools(db)

        # 获取各模块概览
        progress_overview = progress_tools.get_project_overview(project_id)
        progress_status = progress_tools.get_progress_status(project_id)
        cost_overview = cost_tools.get_cost_overview(project_id)
        safety_overview = safety_tools.get_safety_overview(project_id, days=7)

        # 汇总风险等级
        risk_levels = {
            "progress": progress_status.get("risk_level", "green"),
            "cost": cost_overview.get("risk_level", "green"),
            "safety": safety_overview.get("risk_level", "green")
        }

        # 计算综合风险
        level_priority = {"red": 0, "yellow": 1, "green": 2}
        overall_risk = min(risk_levels.values(), key=lambda x: level_priority.get(x, 2))

        return {
            "project_id": project_id,
            "project_name": progress_overview.get("project_name", ""),
            "last_updated": datetime.now().isoformat(),

            # 进度指标
            "progress": {
                "overall_progress": progress_overview.get("overall_progress", 0),
                "spi": progress_status.get("overall_spi"),
                "delayed_tasks": progress_overview.get("delayed_tasks", 0),
                "risk_level": risk_levels["progress"]
            },

            # 成本指标
            "cost": {
                "budget_usage_rate": cost_overview.get("budget_usage_rate", 0),
                "cpi": cost_overview.get("cpi"),
                "variance_rate": cost_overview.get("variance_rate", 0),
                "risk_level": risk_levels["cost"]
            },

            # 安全指标
            "safety": {
                "pass_rate": safety_overview.get("pass_rate", 100),
                "open_defects": safety_overview.get("open_defects", 0),
                "high_defects": safety_overview.get("high_level_defects", 0),
                "risk_level": risk_levels["safety"]
            },

            # 综合风险
            "overall_risk_level": overall_risk,
            "risk_summary": risk_levels
        }

    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )