"""
========================================
项目管理API接口
========================================

📚 模块说明：
- 项目、任务、成本、安全记录的CRUD接口
- 项目统计和风险分析

🎯 核心功能：
1. 项目管理（增删改查）
2. 任务管理
3. 成本管理
4. 安全管理
5. 统计分析

========================================
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from loguru import logger
from core.database import get_db
from services.project_service import (
    ProjectService,
    TaskService,
    CostService,
    SafetyService,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetail,
    ProjectStatistics,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    CostCreate,
    CostResponse,
    SafetyRecordCreate,
    SafetyRecordResponse,
    ResponseModel,
    PaginationResponse,
)

router = APIRouter()


# =========================================
# 项目相关接口
# =========================================

@router.post("/", response_model=ResponseModel, summary="创建项目")
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db)
):
    """创建新项目"""
    try:
        db_project = ProjectService.create_project(db, project)
        return ResponseModel(
            code=200,
            message="项目创建成功",
            data=ProjectResponse.model_validate(db_project).model_dump()
        )
    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建项目失败: {str(e)}"
        )


@router.get("/", response_model=PaginationResponse, summary="获取项目列表")
async def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="项目状态筛选"),
    db: Session = Depends(get_db)
):
    """获取项目列表"""
    try:
        projects = ProjectService.get_projects(db, skip=skip, limit=limit, status=status)
        total = len(projects)  # 简化版，实际应该用 count()
        
        return PaginationResponse(
            code=200,
            message="获取成功",
            data=[ProjectResponse.model_validate(p).model_dump() for p in projects],
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            page_size=limit,
            total_pages=(total + limit - 1) // limit if limit > 0 else 1
        )
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取项目列表失败: {str(e)}"
        )


@router.get("/{project_id}", response_model=ResponseModel, summary="获取项目详情")
async def get_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """获取单个项目详情"""
    project = ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在"
        )
    
    return ResponseModel(
        code=200,
        message="获取成功",
        data=ProjectResponse.model_validate(project).model_dump()
    )


@router.put("/{project_id}", response_model=ResponseModel, summary="更新项目")
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """更新项目信息"""
    db_project = ProjectService.update_project(db, project_id, project_update)
    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在"
        )
    
    return ResponseModel(
        code=200,
        message="更新成功",
        data=ProjectResponse.model_validate(db_project).model_dump()
    )


@router.delete("/{project_id}", response_model=ResponseModel, summary="删除项目")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """删除项目"""
    success = ProjectService.delete_project(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在"
        )
    
    return ResponseModel(
        code=200,
        message="删除成功",
        data=None
    )


@router.get("/{project_id}/statistics", response_model=ResponseModel, summary="获取项目统计")
async def get_project_statistics(
    project_id: str,
    db: Session = Depends(get_db)
):
    """获取项目统计数据"""
    stats = ProjectService.get_project_statistics(db, project_id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 {project_id} 不存在"
        )
    
    return ResponseModel(
        code=200,
        message="获取成功",
        data=stats.model_dump()
    )


# =========================================
# 任务相关接口
# =========================================

@router.post("/{project_id}/tasks", response_model=ResponseModel, summary="创建任务")
async def create_task(
    project_id: str,
    task: TaskCreate,
    db: Session = Depends(get_db)
):
    """为项目创建任务"""
    task.project_id = project_id
    db_task = TaskService.create_task(db, task)
    return ResponseModel(
        code=200,
        message="任务创建成功",
        data=TaskResponse.model_validate(db_task).model_dump()
    )


@router.get("/{project_id}/tasks", response_model=ResponseModel, summary="获取项目任务列表")
async def get_tasks(
    project_id: str,
    status: Optional[str] = Query(None, description="任务状态筛选"),
    db: Session = Depends(get_db)
):
    """获取项目的所有任务"""
    tasks = TaskService.get_tasks_by_project(db, project_id, status=status)
    return ResponseModel(
        code=200,
        message="获取成功",
        data=[TaskResponse.model_validate(t).model_dump() for t in tasks]
    )


@router.put("/tasks/{task_id}", response_model=ResponseModel, summary="更新任务")
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """更新任务信息"""
    db_task = TaskService.update_task(db, task_id, task_update)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )
    
    return ResponseModel(
        code=200,
        message="更新成功",
        data=TaskResponse.model_validate(db_task).model_dump()
    )


@router.get("/{project_id}/tasks/critical", response_model=ResponseModel, summary="获取关键路径任务")
async def get_critical_tasks(
    project_id: str,
    db: Session = Depends(get_db)
):
    """获取项目的关键路径任务"""
    tasks = TaskService.get_critical_tasks(db, project_id)
    return ResponseModel(
        code=200,
        message="获取成功",
        data=[TaskResponse.model_validate(t).model_dump() for t in tasks]
    )


@router.get("/{project_id}/tasks/delayed", response_model=ResponseModel, summary="获取延期任务")
async def get_delayed_tasks(
    project_id: str,
    db: Session = Depends(get_db)
):
    """获取项目的延期任务"""
    tasks = TaskService.get_delayed_tasks(db, project_id)
    return ResponseModel(
        code=200,
        message="获取成功",
        data=[TaskResponse.model_validate(t).model_dump() for t in tasks]
    )


# =========================================
# 成本相关接口
# =========================================

@router.post("/{project_id}/costs", response_model=ResponseModel, summary="创建成本记录")
async def create_cost(
    project_id: str,
    cost: CostCreate,
    db: Session = Depends(get_db)
):
    """为项目创建成本记录"""
    cost.project_id = project_id
    db_cost = CostService.create_cost(db, cost)
    return ResponseModel(
        code=200,
        message="成本记录创建成功",
        data=CostResponse.model_validate(db_cost).model_dump()
    )


@router.get("/{project_id}/costs", response_model=ResponseModel, summary="获取项目成本列表")
async def get_costs(
    project_id: str,
    category: Optional[str] = Query(None, description="成本类别筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """获取项目的成本记录"""
    costs = CostService.get_costs_by_project(
        db, project_id, category=category,
        start_date=start_date, end_date=end_date
    )
    return ResponseModel(
        code=200,
        message="获取成功",
        data=[CostResponse.model_validate(c).model_dump() for c in costs]
    )


@router.get("/{project_id}/costs/summary", response_model=ResponseModel, summary="获取成本汇总")
async def get_cost_summary(
    project_id: str,
    db: Session = Depends(get_db)
):
    """按类别汇总项目成本"""
    summary = CostService.get_cost_summary_by_category(db, project_id)
    return ResponseModel(
        code=200,
        message="获取成功",
        data=summary
    )


# =========================================
# 安全记录相关接口
# =========================================

@router.post("/{project_id}/safety", response_model=ResponseModel, summary="创建安全记录")
async def create_safety_record(
    project_id: str,
    record: SafetyRecordCreate,
    db: Session = Depends(get_db)
):
    """为项目创建安全检查记录"""
    record.project_id = project_id
    db_record = SafetyService.create_safety_record(db, record)
    return ResponseModel(
        code=200,
        message="安全记录创建成功",
        data=SafetyRecordResponse.model_validate(db_record).model_dump()
    )


@router.get("/{project_id}/safety", response_model=ResponseModel, summary="获取安全记录列表")
async def get_safety_records(
    project_id: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    defect_level: Optional[str] = Query(None, description="缺陷等级筛选"),
    db: Session = Depends(get_db)
):
    """获取项目的安全检查记录"""
    records = SafetyService.get_safety_records_by_project(
        db, project_id,
        start_date=start_date,
        end_date=end_date,
        defect_level=defect_level
    )
    return ResponseModel(
        code=200,
        message="获取成功",
        data=[SafetyRecordResponse.model_validate(r).model_dump() for r in records]
    )


@router.get("/{project_id}/safety/open-defects", response_model=ResponseModel, summary="获取未关闭的安全问题")
async def get_open_defects(
    project_id: str,
    db: Session = Depends(get_db)
):
    """获取项目的未关闭安全问题"""
    defects = SafetyService.get_open_defects(db, project_id)
    return ResponseModel(
        code=200,
        message="获取成功",
        data=[SafetyRecordResponse.model_validate(d).model_dump() for d in defects]
    )


@router.get("/{project_id}/safety/statistics", response_model=ResponseModel, summary="获取缺陷统计")
async def get_defect_statistics(
    project_id: str,
    db: Session = Depends(get_db)
):
    """获取项目的缺陷统计"""
    stats = SafetyService.get_defect_statistics(db, project_id)
    return ResponseModel(
        code=200,
        message="获取成功",
        data=stats
    )
