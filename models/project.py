"""
项目与Agent相关数据库模型
=========================

包含：
- ProjectBasic：项目基本信息
- TaskSchedule：任务进度
- CostDetail：成本明细
- SafetyRecord：安全检查记录
- QualityReport：质量报告
- AgentWorkflowLog：智能体工作流日志
"""

from sqlalchemy import Column, String, Date, Numeric, Integer, Boolean, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.document import Base


class ProjectBasic(Base):
    """项目基本信息表"""

    __tablename__ = "project_basic"

    project_id = Column(String(50), primary_key=True, index=True)
    project_name = Column(String(200), nullable=False)
    project_type = Column(String(50))  # 市政工程、房建工程、装修工程等
    start_date = Column(Date)
    planned_end_date = Column(Date)
    total_budget = Column(Numeric(15, 2))
    project_manager = Column(String(100))
    status = Column(String(20), default="active")  # active, completed, suspended
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    tasks = relationship("TaskSchedule", back_populates="project", cascade="all, delete-orphan")
    costs = relationship("CostDetail", back_populates="project", cascade="all, delete-orphan")
    safety_records = relationship("SafetyRecord", back_populates="project", cascade="all, delete-orphan")
    quality_reports = relationship("QualityReport", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.project_id}, name={self.project_name})>"

    @property
    def progress_rate(self) -> float:
        """计算整体进度率（基于任务）"""
        if not self.tasks:
            return 0.0

        total_progress = sum(task.actual_progress or 0 for task in self.tasks)
        return round(total_progress / len(self.tasks), 2)

    @property
    def cost_rate(self) -> float:
        """计算成本消耗率"""
        if not self.total_budget or self.total_budget == 0:
            return 0.0

        total_actual = sum(cost.actual_amount or 0 for cost in self.costs)
        return round(float(total_actual / self.total_budget), 4)


class TaskSchedule(Base):
    """任务进度表"""

    __tablename__ = "task_schedule"

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), ForeignKey("project_basic.project_id"), nullable=False, index=True)
    task_name = Column(String(200), nullable=False)
    planned_start = Column(Date)
    planned_end = Column(Date)
    actual_start = Column(Date)
    actual_end = Column(Date)
    planned_progress = Column(Numeric(5, 2))  # 计划进度 0-100
    actual_progress = Column(Numeric(5, 2))  # 实际进度 0-100
    status = Column(String(20))  # not_started, in_progress, completed, delayed
    is_critical_path = Column(Boolean, default=False)  # 是否在关键路径上
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    project = relationship("ProjectBasic", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task(id={self.task_id}, name={self.task_name}, progress={self.actual_progress}%)>"

    @property
    def variance(self) -> float | None:
        """进度偏差"""
        if self.planned_progress is None or self.actual_progress is None:
            return None
        return float(self.actual_progress - self.planned_progress)

    @property
    def spi(self) -> float | None:
        """进度绩效指数 (Schedule Performance Index)"""
        if not self.planned_progress or self.planned_progress == 0:
            return None
        return round(float(self.actual_progress / self.planned_progress), 3)


class CostDetail(Base):
    """成本明细表"""

    __tablename__ = "cost_detail"

    cost_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), ForeignKey("project_basic.project_id"), nullable=False, index=True)
    cost_category = Column(String(50), nullable=False)  # 材料、人工、机械、分包
    cost_item = Column(String(200))  # 具体成本项
    planned_amount = Column(Numeric(15, 2))  # 计划金额
    actual_amount = Column(Numeric(15, 2))  # 实际金额
    cost_date = Column(Date)  # 发生日期
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 关系
    project = relationship("ProjectBasic", back_populates="costs")

    def __repr__(self) -> str:
        return f"<Cost(id={self.cost_id}, category={self.cost_category}, actual={self.actual_amount})>"

    @property
    def variance(self) -> float | None:
        """成本偏差"""
        if self.planned_amount is None or self.actual_amount is None:
            return None
        return float(self.actual_amount - self.planned_amount)

    @property
    def variance_rate(self) -> float | None:
        """成本偏差率"""
        if not self.planned_amount or self.planned_amount == 0:
            return None
        return round(float(self.variance / self.planned_amount), 4)


class SafetyRecord(Base):
    """安全检查记录表"""

    __tablename__ = "safety_record"

    record_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), ForeignKey("project_basic.project_id"), nullable=False, index=True)
    check_date = Column(Date, nullable=False)
    checker_name = Column(String(100))
    check_type = Column(String(50))  # 日检、周检、月检、专项检查
    defect_type = Column(String(100))  # 模板支撑、防护栏杆、用电安全等
    defect_level = Column(String(20))  # high, medium, low
    defect_description = Column(Text)
    status = Column(String(20))  # open, closed
    closed_date = Column(Date)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 关系
    project = relationship("ProjectBasic", back_populates="safety_records")

    def __repr__(self) -> str:
        return f"<SafetyRecord(id={self.record_id}, type={self.defect_type}, level={self.defect_level})>"


class QualityReport(Base):
    """质量报告表"""

    __tablename__ = "quality_report"

    report_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), ForeignKey("project_basic.project_id"), nullable=False, index=True)
    report_date = Column(Date, nullable=False)
    check_item = Column(String(200))  # 检查项目
    standard_value = Column(String(100))  # 标准值
    actual_value = Column(String(100))  # 实际值
    is_qualified = Column(Boolean)  # 是否合格
    remarks = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # 关系
    project = relationship("ProjectBasic", back_populates="quality_reports")

    def __repr__(self) -> str:
        return f"<QualityReport(id={self.report_id}, item={self.check_item}, qualified={self.is_qualified})>"


class AgentWorkflowLog(Base):
    """Agent工作流日志表"""

    __tablename__ = "agent_workflow_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), index=True)
    workflow_type = Column(String(50))  # weekly_report, risk_analysis, cost_analysis等
    start_time = Column(TIMESTAMP)
    end_time = Column(TIMESTAMP)
    status = Column(String(20))  # running, completed, failed
    input_params = Column(Text)  # JSON格式
    output_result = Column(Text)  # JSON格式
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self) -> str:
        return f"<AgentLog(id={self.log_id}, type={self.workflow_type}, status={self.status})>"

    @property
    def duration_seconds(self) -> float | None:
        """执行时长（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

