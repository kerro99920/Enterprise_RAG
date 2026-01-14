"""
========================================
项目相关的CRUD操作
========================================

📚 模块说明：
- 项目、任务、成本、安全记录的业务逻辑层
- 提供完整的CRUD操作
- 包含统计和查询功能

🎯 核心服务类：
1. ProjectService - 项目管理
2. TaskService - 任务管理
3. CostService - 成本管理
4. SafetyService - 安全管理

========================================
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

from models.project import (
    ProjectBasic, TaskSchedule, CostDetail, 
    SafetyRecord, QualityReport
)
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, TaskCreate, TaskUpdate,
    CostCreate, SafetyRecordCreate, ProjectStatistics
)


class ProjectService:
    """项目服务类"""
    
    @staticmethod
    def get_project(db: Session, project_id: str) -> Optional[ProjectBasic]:
        """获取单个项目"""
        return db.query(ProjectBasic).filter(
            ProjectBasic.project_id == project_id
        ).first()
    
    @staticmethod
    def get_projects(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[ProjectBasic]:
        """获取项目列表"""
        query = db.query(ProjectBasic)
        
        if status:
            query = query.filter(ProjectBasic.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def create_project(db: Session, project: ProjectCreate) -> ProjectBasic:
        """创建项目"""
        db_project = ProjectBasic(**project.model_dump())
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project
    
    @staticmethod
    def update_project(
        db: Session, 
        project_id: str, 
        project_update: ProjectUpdate
    ) -> Optional[ProjectBasic]:
        """更新项目"""
        db_project = ProjectService.get_project(db, project_id)
        if not db_project:
            return None
        
        update_data = project_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_project, field, value)
        
        db.commit()
        db.refresh(db_project)
        return db_project
    
    @staticmethod
    def delete_project(db: Session, project_id: str) -> bool:
        """删除项目"""
        db_project = ProjectService.get_project(db, project_id)
        if not db_project:
            return False
        
        db.delete(db_project)
        db.commit()
        return True
    
    @staticmethod
    def get_project_statistics(
        db: Session, 
        project_id: str
    ) -> Optional[ProjectStatistics]:
        """获取项目统计数据"""
        project = ProjectService.get_project(db, project_id)
        if not project:
            return None
        
        # 任务统计
        tasks = db.query(TaskSchedule).filter(
            TaskSchedule.project_id == project_id
        ).all()
        
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == 'completed'])
        delayed_tasks = len([t for t in tasks if t.status == 'delayed'])
        
        # 平均SPI
        spi_values = [t.spi for t in tasks if t.spi is not None]
        average_spi = sum(spi_values) / len(spi_values) if spi_values else None
        
        # 成本统计
        costs = db.query(CostDetail).filter(
            CostDetail.project_id == project_id
        ).all()
        
        total_actual_cost = sum(c.actual_amount or 0 for c in costs)
        cost_variance = total_actual_cost - (project.total_budget or 0)
        cost_variance_rate = (
            float(cost_variance / project.total_budget) 
            if project.total_budget and project.total_budget > 0 
            else 0.0
        )
        
        # 成本分类
        material_cost = sum(
            c.actual_amount or 0 
            for c in costs 
            if c.cost_category == '材料'
        )
        labor_cost = sum(
            c.actual_amount or 0 
            for c in costs 
            if c.cost_category == '人工'
        )
        equipment_cost = sum(
            c.actual_amount or 0 
            for c in costs 
            if c.cost_category == '机械'
        )
        subcontract_cost = sum(
            c.actual_amount or 0 
            for c in costs 
            if c.cost_category == '分包'
        )
        
        # 安全统计
        safety_records = db.query(SafetyRecord).filter(
            SafetyRecord.project_id == project_id
        ).all()
        
        total_safety_checks = len(set(r.check_date for r in safety_records))
        total_defects = len(safety_records)
        high_level_defects = len([r for r in safety_records if r.defect_level == 'high'])
        open_defects = len([r for r in safety_records if r.status == 'open'])
        
        return ProjectStatistics(
            project_id=project.project_id,
            project_name=project.project_name,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            delayed_tasks=delayed_tasks,
            overall_progress=project.progress_rate,
            average_spi=average_spi,
            total_budget=project.total_budget or 0,
            total_actual_cost=total_actual_cost,
            cost_variance=cost_variance,
            cost_variance_rate=cost_variance_rate,
            material_cost=material_cost,
            labor_cost=labor_cost,
            equipment_cost=equipment_cost,
            subcontract_cost=subcontract_cost,
            total_safety_checks=total_safety_checks,
            total_defects=total_defects,
            high_level_defects=high_level_defects,
            open_defects=open_defects
        )


class TaskService:
    """任务服务类"""
    
    @staticmethod
    def get_tasks_by_project(
        db: Session, 
        project_id: str,
        status: Optional[str] = None
    ) -> List[TaskSchedule]:
        """获取项目的所有任务"""
        query = db.query(TaskSchedule).filter(
            TaskSchedule.project_id == project_id
        )
        
        if status:
            query = query.filter(TaskSchedule.status == status)
        
        return query.all()
    
    @staticmethod
    def create_task(db: Session, task: TaskCreate) -> TaskSchedule:
        """创建任务"""
        db_task = TaskSchedule(**task.model_dump())
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task
    
    @staticmethod
    def update_task(
        db: Session, 
        task_id: int, 
        task_update: TaskUpdate
    ) -> Optional[TaskSchedule]:
        """更新任务"""
        db_task = db.query(TaskSchedule).filter(
            TaskSchedule.task_id == task_id
        ).first()
        
        if not db_task:
            return None
        
        update_data = task_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_task, field, value)
        
        db.commit()
        db.refresh(db_task)
        return db_task
    
    @staticmethod
    def get_critical_tasks(db: Session, project_id: str) -> List[TaskSchedule]:
        """获取关键路径任务"""
        return db.query(TaskSchedule).filter(
            and_(
                TaskSchedule.project_id == project_id,
                TaskSchedule.is_critical_path == True
            )
        ).all()
    
    @staticmethod
    def get_delayed_tasks(db: Session, project_id: str) -> List[TaskSchedule]:
        """获取延期任务"""
        return db.query(TaskSchedule).filter(
            and_(
                TaskSchedule.project_id == project_id,
                TaskSchedule.status == 'delayed'
            )
        ).all()


class CostService:
    """成本服务类"""
    
    @staticmethod
    def get_costs_by_project(
        db: Session, 
        project_id: str,
        category: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[CostDetail]:
        """获取项目的成本记录"""
        query = db.query(CostDetail).filter(
            CostDetail.project_id == project_id
        )
        
        if category:
            query = query.filter(CostDetail.cost_category == category)
        
        if start_date:
            query = query.filter(CostDetail.cost_date >= start_date)
        
        if end_date:
            query = query.filter(CostDetail.cost_date <= end_date)
        
        return query.all()
    
    @staticmethod
    def create_cost(db: Session, cost: CostCreate) -> CostDetail:
        """创建成本记录"""
        db_cost = CostDetail(**cost.model_dump())
        db.add(db_cost)
        db.commit()
        db.refresh(db_cost)
        return db_cost
    
    @staticmethod
    def get_cost_summary_by_category(
        db: Session, 
        project_id: str
    ) -> dict:
        """按类别汇总成本"""
        result = db.query(
            CostDetail.cost_category,
            func.sum(CostDetail.planned_amount).label('total_planned'),
            func.sum(CostDetail.actual_amount).label('total_actual')
        ).filter(
            CostDetail.project_id == project_id
        ).group_by(
            CostDetail.cost_category
        ).all()
        
        return {
            row.cost_category: {
                'planned': float(row.total_planned or 0),
                'actual': float(row.total_actual or 0)
            }
            for row in result
        }


class SafetyService:
    """安全服务类"""
    
    @staticmethod
    def get_safety_records_by_project(
        db: Session, 
        project_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        defect_level: Optional[str] = None
    ) -> List[SafetyRecord]:
        """获取安全检查记录"""
        query = db.query(SafetyRecord).filter(
            SafetyRecord.project_id == project_id
        )
        
        if start_date:
            query = query.filter(SafetyRecord.check_date >= start_date)
        
        if end_date:
            query = query.filter(SafetyRecord.check_date <= end_date)
        
        if defect_level:
            query = query.filter(SafetyRecord.defect_level == defect_level)
        
        return query.all()
    
    @staticmethod
    def create_safety_record(
        db: Session, 
        record: SafetyRecordCreate
    ) -> SafetyRecord:
        """创建安全记录"""
        db_record = SafetyRecord(**record.model_dump())
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        return db_record
    
    @staticmethod
    def get_open_defects(db: Session, project_id: str) -> List[SafetyRecord]:
        """获取未关闭的安全问题"""
        return db.query(SafetyRecord).filter(
            and_(
                SafetyRecord.project_id == project_id,
                SafetyRecord.status == 'open'
            )
        ).all()
    
    @staticmethod
    def get_defect_statistics(db: Session, project_id: str) -> dict:
        """获取缺陷统计"""
        result = db.query(
            SafetyRecord.defect_type,
            SafetyRecord.defect_level,
            func.count(SafetyRecord.record_id).label('count')
        ).filter(
            SafetyRecord.project_id == project_id
        ).group_by(
            SafetyRecord.defect_type,
            SafetyRecord.defect_level
        ).all()
        
        statistics = {}
        for row in result:
            if row.defect_type not in statistics:
                statistics[row.defect_type] = {}
            statistics[row.defect_type][row.defect_level] = row.count
        
        return statistics
