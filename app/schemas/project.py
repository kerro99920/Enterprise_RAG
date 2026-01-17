"""
Pydantic Schema定义 - 用于API请求和响应
路径: app/schemas/project.py
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


# ============ 项目相关 Schema ============


class ProjectBase(BaseModel):
    """项目基础Schema"""

    project_name: str = Field(..., description="项目名称")
    project_type: Optional[str] = Field(None, description="项目类型")
    start_date: Optional[date] = Field(None, description="开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划结束日期")
    total_budget: Optional[Decimal] = Field(None, description="总预算")
    project_manager: Optional[str] = Field(None, description="项目经理")
    status: Optional[str] = Field("active", description="项目状态")


class ProjectCreate(ProjectBase):
    """创建项目的Schema"""

    project_id: str = Field(..., description="项目ID", min_length=1, max_length=50)


class ProjectUpdate(BaseModel):
    """更新项目的Schema"""

    project_name: Optional[str] = None
    project_type: Optional[str] = None
    start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    total_budget: Optional[Decimal] = None
    project_manager: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    """项目响应Schema"""

    project_id: str
    progress_rate: float = Field(0.0, description="整体进度率")
    cost_rate: float = Field(0.0, description="成本消耗率")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDetail(ProjectResponse):
    """项目详情Schema（包含任务和成本）"""

    task_count: int = Field(0, description="任务数量")
    completed_task_count: int = Field(0, description="已完成任务数")
    total_actual_cost: Decimal = Field(0, description="实际总成本")
    safety_issue_count: int = Field(0, description="安全问题数")

    model_config = ConfigDict(from_attributes=True)


# ============ 任务相关 Schema ============


class TaskBase(BaseModel):
    """任务基础Schema"""

    task_name: str = Field(..., description="任务名称")
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    planned_progress: Optional[Decimal] = Field(None, ge=0, le=100, description="计划进度")
    actual_progress: Optional[Decimal] = Field(None, ge=0, le=100, description="实际进度")
    status: Optional[str] = Field("not_started", description="任务状态")
    is_critical_path: Optional[bool] = Field(False, description="是否关键路径")


class TaskCreate(TaskBase):
    """创建任务的Schema"""

    project_id: str = Field(..., description="项目ID")


class TaskUpdate(BaseModel):
    """更新任务的Schema"""

    task_name: Optional[str] = None
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    planned_progress: Optional[Decimal] = None
    actual_progress: Optional[Decimal] = None
    status: Optional[str] = None
    is_critical_path: Optional[bool] = None


class TaskResponse(TaskBase):
    """任务响应Schema"""

    task_id: int
    project_id: str
    variance: Optional[float] = Field(None, description="进度偏差")
    spi: Optional[float] = Field(None, description="进度绩效指数")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ 成本相关 Schema ============


class CostBase(BaseModel):
    """成本基础Schema"""

    cost_category: str = Field(..., description="成本类别")
    cost_item: Optional[str] = Field(None, description="成本项")
    planned_amount: Optional[Decimal] = Field(None, description="计划金额")
    actual_amount: Optional[Decimal] = Field(None, description="实际金额")
    cost_date: Optional[date] = Field(None, description="发生日期")


class CostCreate(CostBase):
    """创建成本的Schema"""

    project_id: str = Field(..., description="项目ID")


class CostResponse(CostBase):
    """成本响应Schema"""

    cost_id: int
    project_id: str
    variance: Optional[float] = Field(None, description="成本偏差")
    variance_rate: Optional[float] = Field(None, description="成本偏差率")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ 安全记录相关 Schema ============


class SafetyRecordBase(BaseModel):
    """安全记录基础Schema"""

    check_date: date = Field(..., description="检查日期")
    checker_name: Optional[str] = Field(None, description="检查员")
    check_type: Optional[str] = Field(None, description="检查类型")
    defect_type: Optional[str] = Field(None, description="缺陷类型")
    defect_level: Optional[str] = Field(None, description="缺陷等级")
    defect_description: Optional[str] = Field(None, description="缺陷描述")
    status: Optional[str] = Field("open", description="状态")
    closed_date: Optional[date] = Field(None, description="关闭日期")


class SafetyRecordCreate(SafetyRecordBase):
    """创建安全记录的Schema"""

    project_id: str = Field(..., description="项目ID")


class SafetyRecordResponse(SafetyRecordBase):
    """安全记录响应Schema"""

    record_id: int
    project_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ 统计分析 Schema ============


class ProjectStatistics(BaseModel):
    """项目统计数据"""

    project_id: str
    project_name: str

    # 进度统计
    total_tasks: int = Field(0, description="总任务数")
    completed_tasks: int = Field(0, description="已完成任务数")
    delayed_tasks: int = Field(0, description="延期任务数")
    overall_progress: float = Field(0.0, description="整体进度")
    average_spi: Optional[float] = Field(None, description="平均进度绩效指数")

    # 成本统计
    total_budget: Decimal = Field(0, description="总预算")
    total_actual_cost: Decimal = Field(0, description="实际总成本")
    cost_variance: Decimal = Field(0, description="成本偏差")
    cost_variance_rate: float = Field(0.0, description="成本偏差率")

    # 成本分类
    material_cost: Decimal = Field(0, description="材料成本")
    labor_cost: Decimal = Field(0, description="人工成本")
    equipment_cost: Decimal = Field(0, description="机械成本")
    subcontract_cost: Decimal = Field(0, description="分包成本")

    # 安全统计
    total_safety_checks: int = Field(0, description="安全检查次数")
    total_defects: int = Field(0, description="缺陷总数")
    high_level_defects: int = Field(0, description="高级别缺陷数")
    open_defects: int = Field(0, description="未关闭缺陷数")

    model_config = ConfigDict(from_attributes=True)


class RiskAlert(BaseModel):
    """风险预警"""

    risk_type: str = Field(..., description="风险类型: progress/cost/safety")
    risk_level: str = Field(..., description="风险等级: high/medium/low")
    title: str = Field(..., description="风险标题")
    description: str = Field(..., description="风险描述")
    recommendations: List[str] = Field(default_factory=list, description="建议措施")

    model_config = ConfigDict(from_attributes=True)


# ============ 通用响应 Schema ============


class ResponseBase(BaseModel):
    """基础响应"""

    code: int = Field(200, description="状态码")
    message: str = Field("success", description="消息")


class ResponseModel(ResponseBase):
    """通用响应模型"""

    data: Optional[dict | list] = Field(None, description="数据")


class PaginationResponse(ResponseBase):
    """分页响应"""

    data: List[dict] = Field(default_factory=list, description="数据列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页")
    page_size: int = Field(20, description="每页数量")
    total_pages: int = Field(0, description="总页数")

