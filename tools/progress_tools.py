"""
进度分析工具库（完整注释版）
位置: F:\\LLM\\Enterprise_RAG\\tools\\progress_tools.py

📚 模块说明：
- 提供8个专业的进度分析工具
- 供ProgressAnalysisAgent调用
- 所有工具返回结构化的Dict数据

🔧 工具列表：
1. get_project_overview      - 项目概览
2. get_progress_status       - 进度状态（SPI计算）
3. get_delayed_tasks         - 延期任务识别
4. get_critical_path_tasks   - 关键路径任务
5. analyze_progress_trend    - 进度趋势分析
6. predict_completion_time   - 完成时间预测
7. identify_bottlenecks      - 瓶颈识别
8. get_resource_allocation   - 资源配置评估

💡 使用方式：
    from tools.progress_tools import ProgressTools

    tools = ProgressTools(db)
    overview = tools.get_project_overview("P001")
"""

from typing import Dict, List, Optional, Any
from datetime import date, timedelta
from sqlalchemy.orm import Session

from models.project import ProjectBasic, TaskSchedule
from services.project_service import ProjectService, TaskService


class ProgressTools:
    """
    进度分析工具集

    属性:
        db (Session): SQLAlchemy数据库会话
    """

    def __init__(self, db: Session):
        """
        初始化工具实例

        参数:
            db: 数据库会话对象
        """
        self.db = db

    def get_project_overview(self, project_id: str) -> Dict[str, Any]:
        """
        工具1: 获取项目概览

        功能:
            - 返回项目基本信息
            - 统计任务状态分布
            - 计算整体进度和平均SPI

        参数:
            project_id: 项目ID

        返回:
            包含以下字段的字典:
            - project_id: 项目ID
            - project_name: 项目名称
            - project_type: 项目类型
            - project_manager: 项目经理
            - start_date: 开始日期
            - planned_end_date: 计划结束日期
            - total_tasks: 总任务数
            - completed_tasks: 已完成任务数
            - in_progress_tasks: 进行中任务数
            - delayed_tasks: 延期任务数
            - not_started_tasks: 未开始任务数
            - overall_progress: 整体进度率（%）
            - average_spi: 平均进度绩效指数

        示例:
            >>> tools = ProgressTools(db)
            >>> overview = tools.get_project_overview("P001")
            >>> print(overview["overall_progress"])
            45.3
        """
        # 获取项目基本信息
        project = ProjectService.get_project(self.db, project_id)
        if not project:
            return {"error": f"Project {project_id} not found"}

        # 获取所有任务
        tasks = TaskService.get_tasks_by_project(self.db, project_id)

        # 统计各状态任务数量
        total_tasks = len(tasks)
        completed = len([t for t in tasks if t.status == "completed"])
        in_progress = len([t for t in tasks if t.status == "in_progress"])
        delayed = len([t for t in tasks if t.status == "delayed"])
        not_started = len([t for t in tasks if t.status == "not_started"])

        # 计算整体进度（来自项目的progress_rate属性）
        overall_progress = project.progress_rate

        # 计算平均SPI（进度绩效指数）
        # SPI = 实际进度 / 计划进度，SPI>1表示超前，SPI<1表示延期
        spi_values = [t.spi for t in tasks if t.spi is not None]
        average_spi = sum(spi_values) / len(spi_values) if spi_values else None

        return {
            "project_id": project_id,
            "project_name": project.project_name,
            "project_type": project.project_type,
            "project_manager": project.project_manager,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "planned_end_date": project.planned_end_date.isoformat() if project.planned_end_date else None,
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "in_progress_tasks": in_progress,
            "delayed_tasks": delayed,
            "not_started_tasks": not_started,
            "overall_progress": overall_progress,  # 整体进度百分比
            "average_spi": round(average_spi, 3) if average_spi else None
        }

    def get_progress_status(self, project_id: str) -> Dict[str, Any]:
        """
        工具2: 获取进度状态分析

        功能:
            - 计算项目整体SPI
            - 分析进度偏差
            - 判定风险等级（green/yellow/red）

        参数:
            project_id: 项目ID

        返回:
            包含以下字段的字典:
            - total_tasks: 任务总数
            - avg_planned_progress: 平均计划进度（%）
            - avg_actual_progress: 平均实际进度（%）
            - variance: 进度偏差（实际-计划）
            - variance_rate: 进度偏差率（%）
            - overall_spi: 整体SPI
            - risk_level: 风险等级（green/yellow/red）
            - risk_description: 风险描述

        风险等级判定标准:
            - Green: SPI >= 0.95 (进度正常)
            - Yellow: 0.85 <= SPI < 0.95 (略有延期)
            - Red: SPI < 0.85 (严重延期)
        """
        # 获取项目所有任务
        tasks = TaskService.get_tasks_by_project(self.db, project_id)

        if not tasks:
            return {
                "error": "No tasks found",
                "overall_spi": None,
                "risk_level": "unknown"
            }

        # 计算总体计划进度和实际进度
        total_planned = sum(float(t.planned_progress or 0) for t in tasks)
        total_actual = sum(float(t.actual_progress or 0) for t in tasks)

        # 计算平均进度
        avg_planned = total_planned / len(tasks) if tasks else 0
        avg_actual = total_actual / len(tasks) if tasks else 0

        # 计算整体SPI（Schedule Performance Index）
        # SPI是项目管理中衡量进度的关键指标
        overall_spi = (avg_actual / avg_planned) if avg_planned > 0 else None

        # 计算进度偏差
        variance = avg_actual - avg_planned  # 绝对偏差
        variance_rate = (variance / avg_planned * 100) if avg_planned > 0 else 0  # 相对偏差

        # 判断风险等级
        if overall_spi is None:
            risk_level = "unknown"
            risk_description = "无法计算SPI，缺少有效数据"
        elif overall_spi >= 0.95:
            risk_level = "green"
            risk_description = "进度正常，基本按计划执行"
        elif overall_spi >= 0.85:
            risk_level = "yellow"
            risk_description = "进度略有延期，需要关注并采取措施"
        else:
            risk_level = "red"
            risk_description = "进度严重延期，需要立即采取纠正措施"

        return {
            "total_tasks": len(tasks),
            "avg_planned_progress": round(avg_planned, 2),
            "avg_actual_progress": round(avg_actual, 2),
            "variance": round(variance, 2),
            "variance_rate": round(variance_rate, 2),
            "overall_spi": round(overall_spi, 3) if overall_spi else None,
            "risk_level": risk_level,
            "risk_description": risk_description
        }

    def get_delayed_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        """
        工具3: 获取延期任务列表

        功能:
            - 识别所有进度落后的任务
            - 分析延期原因
            - 按严重程度排序

        参数:
            project_id: 项目ID

        返回:
            延期任务列表，每个任务包含:
            - task_id: 任务ID
            - task_name: 任务名称
            - planned_progress: 计划进度
            - actual_progress: 实际进度
            - variance: 进度偏差
            - spi: 任务的SPI值
            - severity: 严重程度（严重/中等/轻微）
            - reason: 延期原因说明
            - is_critical_path: 是否在关键路径上

        延期判定逻辑:
            1. 任务状态标记为"delayed"
            2. SPI < 0.95
            3. 进度偏差 < -5%

        严重程度判定:
            - 严重: SPI < 0.8
            - 中等: 0.8 <= SPI < 0.9
            - 轻微: SPI >= 0.9

        排序规则:
            1. 严重程度（严重 > 中等 > 轻微）
            2. 是否关键路径（是 > 否）
            3. 偏差大小（大 > 小）
        """
        # 获取所有任务
        tasks = TaskService.get_tasks_by_project(self.db, project_id)

        delayed_tasks = []

        for task in tasks:
            # 判断是否延期
            is_delayed = False
            delay_reason = ""

            # 延期判定条件1: 任务状态为delayed
            if task.status == "delayed":
                is_delayed = True
                delay_reason = "任务已标记为延期状态"
            # 延期判定条件2: SPI小于0.95
            elif task.spi and task.spi < 0.95:
                is_delayed = True
                delay_reason = f"SPI={task.spi:.2f}，进度落后于计划"
            # 延期判定条件3: 进度偏差超过-5%
            elif task.variance and task.variance < -5:
                is_delayed = True
                delay_reason = f"进度偏差{task.variance:.1f}%，明显落后"

            if is_delayed:
                # 计算延期严重程度
                if task.spi and task.spi < 0.8:
                    severity = "严重"  # 进度严重落后
                elif task.spi and task.spi < 0.9:
                    severity = "中等"  # 进度中等落后
                else:
                    severity = "轻微"  # 进度轻微落后

                delayed_tasks.append({
                    "task_id": task.task_id,
                    "task_name": task.task_name,
                    "planned_progress": float(task.planned_progress or 0),
                    "actual_progress": float(task.actual_progress or 0),
                    "variance": task.variance,
                    "spi": task.spi,
                    "severity": severity,
                    "reason": delay_reason,
                    "is_critical_path": task.is_critical_path
                })

        # 按严重程度、关键路径、偏差排序
        severity_order = {"严重": 0, "中等": 1, "轻微": 2}
        delayed_tasks.sort(key=lambda x: (
            severity_order.get(x['severity'], 3),  # 先按严重程度
            not x['is_critical_path'],  # 再按是否关键路径（关键路径优先）
            x['variance'] if x['variance'] else 0  # 最后按偏差大小
        ))

        return delayed_tasks

    def get_critical_path_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        """
        工具4: 获取关键路径任务

        功能:
            - 识别项目关键路径上的所有任务
            - 分析关键任务的进度状态
            - 标记延期的关键任务

        参数:
            project_id: 项目ID

        返回:
            关键路径任务列表，每个任务包含:
            - task_id: 任务ID
            - task_name: 任务名称
            - planned_progress: 计划进度
            - actual_progress: 实际进度
            - spi: 任务SPI
            - status: 任务状态
            - planned_start: 计划开始日期
            - planned_end: 计划结束日期
            - is_delayed: 是否延期（布尔值）

        注意:
            关键路径任务的延期会直接影响项目整体工期，
            因此这些任务需要重点关注和资源倾斜
        """
        # 获取所有标记为关键路径的任务
        critical_tasks = TaskService.get_critical_tasks(self.db, project_id)

        result = []
        for task in critical_tasks:
            # 判断任务是否延期（SPI < 0.95视为延期）
            is_delayed = task.spi < 0.95 if task.spi else False

            result.append({
                "task_id": task.task_id,
                "task_name": task.task_name,
                "planned_progress": float(task.planned_progress or 0),
                "actual_progress": float(task.actual_progress or 0),
                "spi": task.spi,
                "status": task.status,
                "planned_start": task.planned_start.isoformat() if task.planned_start else None,
                "planned_end": task.planned_end.isoformat() if task.planned_end else None,
                "is_delayed": is_delayed
            })

        return result

    def analyze_progress_trend(self, project_id: str, days: int = 30) -> Dict[str, Any]:
        """
        工具5: 分析进度趋势

        功能:
            - 分析最近N天的进度变化
            - 识别高风险和中风险任务数量
            - 判断整体趋势（恶化/平稳）

        参数:
            project_id: 项目ID
            days: 分析时间窗口（默认30天）

        返回:
            包含以下字段的字典:
            - analysis_period: 分析周期描述
            - updated_tasks: 期间内有更新的任务数
            - high_risk_tasks: 高风险任务数（SPI<0.85）
            - medium_risk_tasks: 中风险任务数（0.85<=SPI<0.95）
            - trend: 趋势判断（恶化/平稳）

        趋势判定逻辑:
            - 恶化: 高风险任务数 > 3
            - 平稳: 高风险任务数 <= 3
        """
        # 获取所有任务
        tasks = TaskService.get_tasks_by_project(self.db, project_id)

        # 计算截止日期（当前日期 - N天）
        cutoff_date = date.today() - timedelta(days=days)

        # 筛选最近N天内有更新的任务
        # 通过updated_at字段判断任务是否在分析窗口内有更新
        recent_tasks = [
            t for t in tasks
            if t.updated_at and t.updated_at.date() >= cutoff_date
        ]

        if not recent_tasks:
            return {
                "message": f"最近{days}天内没有任务更新",
                "trend": "unknown"
            }

        # 统计高风险和中风险任务
        # 高风险: SPI < 0.85（严重延期）
        high_risk_count = len([t for t in recent_tasks if t.spi and t.spi < 0.85])
        # 中风险: 0.85 <= SPI < 0.95（轻微延期）
        medium_risk_count = len([t for t in recent_tasks if t.spi and 0.85 <= t.spi < 0.95])

        # 判断趋势
        # 如果高风险任务超过3个，认为趋势恶化
        trend = "恶化" if high_risk_count > 3 else "平稳"

        return {
            "analysis_period": f"最近{days}天",
            "updated_tasks": len(recent_tasks),
            "high_risk_tasks": high_risk_count,
            "medium_risk_tasks": medium_risk_count,
            "trend": trend
        }

    def predict_completion_time(self, project_id: str) -> Dict[str, Any]:
        """
        工具6: 预测完成时间

        功能:
            - 基于当前SPI预测项目完成时间
            - 计算预计延期天数
            - 提供预测置信度

        参数:
            project_id: 项目ID

        返回:
            包含以下字段的字典:
            - current_progress: 当前进度（%）
            - remaining_progress: 剩余进度（%）
            - average_spi: 平均SPI
            - planned_end_date: 计划结束日期
            - predicted_delay_days: 预计延期天数
            - prediction_confidence: 预测置信度（高/中/低）

        预测逻辑:
            1. 计算平均SPI
            2. 调整系数 = 1 / SPI
            3. 预测剩余天数 = 计划剩余天数 × 调整系数
            4. 延期天数 = 预测剩余天数 - 计划剩余天数

        置信度判定:
            - 高: 有效SPI样本 > 10
            - 中: 有效SPI样本 5-10
            - 低: 有效SPI样本 < 5
        """
        # 获取项目基本信息
        project = ProjectService.get_project(self.db, project_id)
        if not project:
            return {"error": "Project not found"}

        # 获取所有任务
        tasks = TaskService.get_tasks_by_project(self.db, project_id)

        # 计算平均SPI
        # 只考虑有效的SPI值（SPI > 0）
        spi_values = [t.spi for t in tasks if t.spi is not None and t.spi > 0]
        if not spi_values:
            return {
                "error": "无法计算，缺少有效的SPI数据",
                "status": "insufficient_data"
            }

        avg_spi = sum(spi_values) / len(spi_values)

        # 计算剩余工作量
        remaining_progress = 100 - project.progress_rate

        # 根据SPI预测完成时间
        # SPI = 1: 按计划完成
        # SPI < 1: 需要更多时间（调整系数 > 1）
        # SPI > 1: 提前完成（调整系数 < 1）
        if avg_spi > 0:
            adjustment_factor = 1 / avg_spi
        else:
            adjustment_factor = 2.0  # 默认延期100%

        # 计算预计延期天数
        if project.planned_end_date:
            # 计算计划剩余天数
            planned_remaining_days = (project.planned_end_date - date.today()).days
            if planned_remaining_days > 0:
                # 预测实际需要的天数
                predicted_days = int(planned_remaining_days * adjustment_factor)
                # 延期天数 = 预测天数 - 计划天数
                delay_days = predicted_days - planned_remaining_days
            else:
                # 已经超过计划结束日期
                predicted_days = 0
                delay_days = 0
        else:
            predicted_days = 0
            delay_days = 0

        # 确定预测置信度
        # 有效样本越多，预测越可靠
        if len(spi_values) > 10:
            confidence = "高"
        elif len(spi_values) > 5:
            confidence = "中"
        else:
            confidence = "低"

        return {
            "current_progress": project.progress_rate,
            "remaining_progress": remaining_progress,
            "average_spi": round(avg_spi, 3),
            "planned_end_date": project.planned_end_date.isoformat() if project.planned_end_date else None,
            "predicted_delay_days": delay_days,
            "prediction_confidence": confidence
        }

    def identify_bottlenecks(self, project_id: str) -> List[Dict[str, Any]]:
        """
        工具7: 识别瓶颈任务

        功能:
            - 找出影响项目整体进度的瓶颈
            - 评估瓶颈的影响程度
            - 提供针对性建议

        参数:
            project_id: 项目ID

        返回:
            瓶颈任务列表，每个任务包含:
            - task_id: 任务ID
            - task_name: 任务名称
            - spi: 任务SPI
            - actual_progress: 实际进度
            - impact: 影响程度（高/中/低）
            - reason: 识别为瓶颈的原因
            - recommendation: 针对性建议

        瓶颈识别标准:
            必须同时满足：
            1. 在关键路径上
            2. 任务未完成
            3. SPI < 0.95（进度落后）

        影响程度判定:
            - 高: SPI < 0.85（严重延期）
            - 中: 0.85 <= SPI < 0.95（中等延期）
            - 低: 其他情况
        """
        # 获取所有关键路径任务
        # 只有关键路径上的任务才可能成为瓶颈
        critical_tasks = TaskService.get_critical_tasks(self.db, project_id)

        bottlenecks = []

        for task in critical_tasks:
            # 瓶颈判定逻辑
            is_bottleneck = False
            impact = "低"
            recommendation = ""

            # 任务必须未完成才可能是瓶颈
            if task.status != "completed":
                # 判定条件1: SPI < 0.85（严重延期）
                if task.spi and task.spi < 0.85:
                    is_bottleneck = True
                    impact = "高"
                    recommendation = "立即增加资源投入，优先解决该任务，避免影响整体工期"
                # 判定条件2: SPI < 0.95（中等延期）
                elif task.spi and task.spi < 0.95:
                    is_bottleneck = True
                    impact = "中"
                    recommendation = "密切关注任务进展，适当增加资源，确保不进一步延期"

            # 如果识别为瓶颈，添加到结果列表
            if is_bottleneck:
                bottlenecks.append({
                    "task_id": task.task_id,
                    "task_name": task.task_name,
                    "spi": task.spi,
                    "actual_progress": float(task.actual_progress or 0),
                    "impact": impact,
                    "reason": f"关键路径任务，当前SPI={task.spi:.2f}，进度落后",
                    "recommendation": recommendation
                })

        return bottlenecks

    def get_resource_allocation(self, project_id: str) -> Dict[str, Any]:
        """
        工具8: 评估资源配置

        功能:
            - 分析当前并行任务数量
            - 评估资源负荷状态
            - 提供资源调配建议

        参数:
            project_id: 项目ID

        返回:
            包含以下字段的字典:
            - parallel_tasks: 当前并行任务数（进行中的任务）
            - load_status: 负荷状态（过载/正常/充足）
            - suggestion: 资源调配建议
            - critical_tasks_in_progress: 进行中的关键任务数

        负荷状态判定:
            - 过载: 并行任务 > 10
            - 正常: 5 < 并行任务 <= 10
            - 充足: 并行任务 <= 5

        注意:
            这是一个简化的资源评估模型，
            实际项目中应结合团队规模、任务复杂度等因素综合评估
        """
        # 获取所有任务
        tasks = TaskService.get_tasks_by_project(self.db, project_id)

        # 筛选进行中的任务
        # 进行中的任务代表当前需要资源的任务
        in_progress_tasks = [t for t in tasks if t.status == "in_progress"]

        # 统计并行任务数
        parallel_count = len(in_progress_tasks)

        # 评估负荷状态并提供建议
        if parallel_count > 10:
            load_status = "过载"
            suggestion = "并行任务过多（>10个），建议：\n" \
                        "1. 优先完成关键路径任务\n" \
                        "2. 暂停部分非关键任务\n" \
                        "3. 考虑增加人员或延长工期"
        elif parallel_count > 5:
            load_status = "正常"
            suggestion = "资源配置合理，继续保持当前节奏"
        else:
            load_status = "充足"
            suggestion = "资源充足，可以考虑：\n" \
                        "1. 适当增加并行任务\n" \
                        "2. 提前启动后续任务\n" \
                        "3. 加快项目整体进度"

        # 统计进行中的关键任务数
        # 关键任务应该优先分配资源
        critical_in_progress = len([
            t for t in in_progress_tasks
            if t.is_critical_path
        ])

        return {
            "parallel_tasks": parallel_count,
            "load_status": load_status,
            "suggestion": suggestion,
            "critical_tasks_in_progress": critical_in_progress
        }


def get_progress_tools(db: Session) -> ProgressTools:
    """
    工厂函数：创建进度工具实例

    参数:
        db: 数据库会话

    返回:
        ProgressTools实例

    使用示例:
        >>> from core.database import get_project_db
        >>> from tools.progress_tools import get_progress_tools
        >>>
        >>> db = next(get_project_db())
        >>> tools = get_progress_tools(db)
        >>> overview = tools.get_project_overview("P001")
    """
    return ProgressTools(db)