"""
成本分析工具库（完整注释版）
位置: F:\\LLM\\Enterprise_RAG\\tools\\cost_tools.py

📚 模块说明：
- 提供8个专业的成本分析工具
- 供CostAnalysisAgent调用
- 支持CPI计算、成本预测、对标分析

🔧 工具列表：
1. get_cost_overview       - 成本概览（CPI、预算消耗率）
2. get_cost_by_category    - 按类别统计（材料/人工/机械/分包）
3. identify_cost_overruns  - 识别超支项
4. predict_final_cost      - 预测最终成本（EAC）
5. compare_with_benchmark  - 对标历史项目
6. analyze_cost_trend      - 成本趋势分析
7. identify_cost_risks     - 识别成本风险
8. get_cost_control_suggestions - 生成控制建议

💡 关键概念：
- CPI (Cost Performance Index): 成本绩效指数 = 挣值 / 实际成本
  - CPI > 1: 成本低于预算（良好）
  - CPI = 1: 成本符合预算
  - CPI < 1: 成本超支
- EAC (Estimate at Completion): 完成时成本预测
"""

from typing import Dict, List, Optional, Any
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from models.project import ProjectBasic, CostDetail
from services.project_service import ProjectService, CostService


class CostTools:
    """成本分析工具集"""

    def __init__(self, db: Session):
        """初始化工具实例"""
        self.db = db

    def get_cost_overview(self, project_id: str) -> Dict[str, Any]:
        """
        工具1: 获取成本概览

        功能:
            - 计算总体成本状况
            - 计算CPI（成本绩效指数）
            - 判定成本风险等级

        返回字段:
            - total_budget: 总预算
            - total_actual: 实际支出
            - variance: 成本偏差
            - variance_rate: 偏差率（%）
            - budget_usage_rate: 预算消耗率（%）
            - cpi: 成本绩效指数
            - risk_level: green/yellow/red

        CPI计算公式:
            CPI = 挣值 / 实际成本
            挣值 = 总预算 × (进度率 / 100)
        """
        project = ProjectService.get_project(self.db, project_id)
        if not project:
            return {"error": f"Project {project_id} not found"}

        costs = CostService.get_costs_by_project(self.db, project_id)

        # 1. 计算总成本
        total_planned = sum(float(c.planned_amount or 0) for c in costs)
        total_actual = sum(float(c.actual_amount or 0) for c in costs)

        # 2. 计算偏差
        variance = total_actual - total_planned
        variance_rate = (variance / total_planned * 100) if total_planned > 0 else 0

        # 3. 计算预算消耗率
        budget = float(project.total_budget or 0)
        budget_usage_rate = (total_actual / budget * 100) if budget > 0 else 0

        # 4. 计算CPI (Cost Performance Index)
        progress_rate = project.progress_rate  # 当前进度率
        earned_value = budget * (progress_rate / 100) if budget > 0 else 0  # 挣值
        cpi = (earned_value / total_actual) if total_actual > 0 else 0

        # 5. 风险等级判定
        if cpi >= 1.05:
            risk_level, risk_desc = "green", "成本控制良好，低于预算"
        elif cpi >= 0.95:
            risk_level, risk_desc = "green", "成本基本符合预算"
        elif cpi >= 0.85:
            risk_level, risk_desc = "yellow", "成本有超支风险，需关注"
        else:
            risk_level, risk_desc = "red", "成本严重超支，需立即采取措施"

        return {
            "project_id": project_id,
            "project_name": project.project_name,
            "total_budget": budget,
            "total_actual": total_actual,
            "variance": variance,
            "variance_rate": round(variance_rate, 2),
            "budget_usage_rate": round(budget_usage_rate, 2),
            "progress_rate": progress_rate,
            "earned_value": earned_value,
            "cpi": round(cpi, 3),
            "risk_level": risk_level,
            "risk_description": risk_desc
        }

    def get_cost_by_category(self, project_id: str) -> Dict[str, Any]:
        """
        工具2: 按类别统计成本

        分析四大类别成本：材料、人工、机械、分包
        识别超支最严重的类别
        """
        costs = CostService.get_costs_by_project(self.db, project_id)

        category_stats = {}
        categories = ["材料", "人工", "机械", "分包"]

        for category in categories:
            cat_costs = [c for c in costs if c.cost_category == category]

            if cat_costs:
                planned = sum(float(c.planned_amount or 0) for c in cat_costs)
                actual = sum(float(c.actual_amount or 0) for c in cat_costs)
                variance = actual - planned
                variance_rate = (variance / planned * 100) if planned > 0 else 0

                category_stats[category] = {
                    "planned": planned,
                    "actual": actual,
                    "variance": variance,
                    "variance_rate": round(variance_rate, 2),
                    "count": len(cat_costs),
                    "status": "超支" if variance > 0 else "正常"
                }

        # 找出超支最严重的类别
        max_overrun_cat = None
        max_overrun_rate = 0
        for cat, stats in category_stats.items():
            if stats["variance_rate"] > max_overrun_rate:
                max_overrun_rate = stats["variance_rate"]
                max_overrun_cat = cat

        return {
            "categories": category_stats,
            "max_overrun_category": max_overrun_cat,
            "max_overrun_rate": round(max_overrun_rate, 2)
        }

    def identify_cost_overruns(self, project_id: str, threshold: float = 5.0) -> List[Dict]:
        """
        工具3: 识别超支成本项

        参数:
            threshold: 超支阈值（%），默认5%

        返回:
            超支项列表（按超支率降序）
        """
        costs = CostService.get_costs_by_project(self.db, project_id)

        overruns = []
        for cost in costs:
            if cost.planned_amount and cost.actual_amount:
                variance = float(cost.actual_amount - cost.planned_amount)
                variance_rate = (variance / float(cost.planned_amount) * 100)

                if variance_rate > threshold:
                    overruns.append({
                        "cost_id": cost.cost_id,
                        "category": cost.cost_category,
                        "item": cost.cost_item,
                        "planned": float(cost.planned_amount),
                        "actual": float(cost.actual_amount),
                        "variance": variance,
                        "variance_rate": round(variance_rate, 2),
                        "severity": "严重" if variance_rate > 20 else "中等" if variance_rate > 10 else "轻微"
                    })

        overruns.sort(key=lambda x: x['variance_rate'], reverse=True)
        return overruns

    def predict_final_cost(self, project_id: str) -> Dict[str, Any]:
        """
        工具4: 预测项目最终成本

        预测方法:
            EAC (Estimate at Completion) = BAC / CPI
            其中 BAC = Budget at Completion (总预算)

        返回:
            - predicted_final_cost: 预测最终成本
            - predicted_overrun: 预测超支额
            - will_exceed_budget: 是否会超支
        """
        overview = self.get_cost_overview(project_id)

        budget = overview["total_budget"]
        cpi = overview["cpi"]
        progress = overview["progress_rate"]

        if cpi > 0 and progress > 0:
            # EAC = BAC / CPI
            predicted_final_cost = budget / cpi
            predicted_overrun = predicted_final_cost - budget
            predicted_overrun_rate = (predicted_overrun / budget * 100)

            return {
                "current_budget": budget,
                "cpi": cpi,
                "progress_rate": progress,
                "predicted_final_cost": round(predicted_final_cost, 2),
                "predicted_overrun": round(predicted_overrun, 2),
                "predicted_overrun_rate": round(predicted_overrun_rate, 2),
                "will_exceed_budget": predicted_overrun > 0,
                "confidence": "中等" if progress > 30 else "低"
            }

        return {"error": "数据不足，无法预测"}

    def compare_with_benchmark(self, project_id: str) -> Dict[str, Any]:
        """
        工具5: 与历史项目对标

        对比同类型项目的成本水平
        """
        project = ProjectService.get_project(self.db, project_id)
        if not project:
            return {"error": "Project not found"}

        # 查找同类型项目
        similar_projects = self.db.query(ProjectBasic).filter(
            ProjectBasic.project_type == project.project_type,
            ProjectBasic.project_id != project_id,
            ProjectBasic.status.in_(['completed', 'active'])
        ).all()

        if not similar_projects:
            return {"message": "没有找到可对标的同类项目", "benchmark_available": False}

        # 计算标杆成本率
        cost_rates = [p.cost_rate for p in similar_projects if p.cost_rate > 0]

        if not cost_rates:
            return {"message": "对标项目数据不足", "benchmark_available": False}

        avg_cost_rate = sum(cost_rates) / len(cost_rates)
        current_cost_rate = project.cost_rate

        # 对比分析
        if current_cost_rate < avg_cost_rate * 0.95:
            performance = "优于平均"
        elif current_cost_rate < avg_cost_rate * 1.05:
            performance = "符合平均"
        else:
            performance = "高于平均"

        return {
            "benchmark_available": True,
            "similar_projects_count": len(similar_projects),
            "benchmark_avg_cost_rate": round(avg_cost_rate, 4),
            "current_cost_rate": round(current_cost_rate, 4),
            "performance": performance,
            "gap": round((current_cost_rate - avg_cost_rate) * 100, 2)
        }

    def analyze_cost_trend(self, project_id: str, months: int = 3) -> Dict[str, Any]:
        """
        工具6: 分析成本趋势（最近N个月）
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)

        costs = CostService.get_costs_by_project(
            self.db, project_id, start_date=start_date, end_date=end_date
        )

        # 按月分组
        monthly_costs = {}
        for cost in costs:
            if cost.cost_date:
                month_key = cost.cost_date.strftime('%Y-%m')
                if month_key not in monthly_costs:
                    monthly_costs[month_key] = {"planned": 0, "actual": 0, "count": 0}

                monthly_costs[month_key]["planned"] += float(cost.planned_amount or 0)
                monthly_costs[month_key]["actual"] += float(cost.actual_amount or 0)
                monthly_costs[month_key]["count"] += 1

        # 计算趋势
        sorted_months = sorted(monthly_costs.keys())
        if len(sorted_months) >= 2:
            first_actual = monthly_costs[sorted_months[0]]["actual"]
            last_actual = monthly_costs[sorted_months[-1]]["actual"]
            growth_rate = ((last_actual - first_actual) / first_actual * 100) if first_actual > 0 else 0
            trend = "上升" if growth_rate > 10 else "平稳" if growth_rate > -10 else "下降"
        else:
            growth_rate = 0
            trend = "数据不足"

        return {
            "analysis_period": f"{start_date} 至 {end_date}",
            "monthly_data": monthly_costs,
            "trend": trend,
            "growth_rate": round(growth_rate, 2)
        }

    def identify_cost_risks(self, project_id: str) -> List[Dict[str, Any]]:
        """
        工具7: 识别成本风险

        综合分析多个维度识别潜在风险
        """
        risks = []

        overview = self.get_cost_overview(project_id)
        overruns = self.identify_cost_overruns(project_id)
        prediction = self.predict_final_cost(project_id)

        # 风险1: CPI过低
        cpi = overview.get("cpi", 1)
        if cpi < 0.85:
            risks.append({
                "risk_type": "成本绩效差",
                "severity": "high",
                "description": f"CPI为{cpi:.2f}，远低于1.0",
                "recommendation": "立即审查成本明细，识别超支原因"
            })

        # 风险2: 预算消耗过快
        budget_usage = overview.get("budget_usage_rate", 0)
        progress = overview.get("progress_rate", 0)
        if progress > 0 and budget_usage > progress * 1.1:
            risks.append({
                "risk_type": "预算消耗过快",
                "severity": "high",
                "description": f"预算消耗{budget_usage:.1f}%，但进度仅{progress:.1f}%",
                "recommendation": "严格控制后续支出"
            })

        # 风险3: 预测超支
        if prediction.get("will_exceed_budget", False):
            overrun_rate = prediction.get("predicted_overrun_rate", 0)
            risks.append({
                "risk_type": "预计总成本超支",
                "severity": "high" if overrun_rate > 10 else "medium",
                "description": f"预计最终超支{overrun_rate:.1f}%",
                "recommendation": "调整后续采购计划" if overrun_rate > 10 else "监控成本趋势"
            })

        return risks

    def get_cost_control_suggestions(self, project_id: str) -> List[str]:
        """
        工具8: 生成成本控制建议

        基于分析结果生成可执行的控制措施
        """
        suggestions = []

        overview = self.get_cost_overview(project_id)
        category_stats = self.get_cost_by_category(project_id)
        risks = self.identify_cost_risks(project_id)

        # 基于CPI生成建议
        cpi = overview.get("cpi", 1)
        if cpi < 0.9:
            suggestions.append("🔴 优先级1：CPI过低，建议立即召开成本分析会")
            suggestions.append("   - 重点审查材料采购和分包合同")

        # 基于类别超支生成建议
        max_overrun_cat = category_stats.get("max_overrun_category")
        if max_overrun_cat:
            max_rate = category_stats.get("max_overrun_rate", 0)
            if max_rate > 10:
                suggestions.append(f"🟡 优先级2：{max_overrun_cat}成本超支{max_rate:.1f}%")
                if max_overrun_cat == "材料":
                    suggestions.append("   - 检查材料市场价格变化，优化采购策略")
                elif max_overrun_cat == "人工":
                    suggestions.append("   - 评估人工效率，优化施工组织")

        # 通用建议
        if not suggestions:
            suggestions.append("✅ 当前成本控制良好，建议继续保持")

        return suggestions


def get_cost_tools(db: Session) -> CostTools:
    """工厂函数：创建成本工具实例"""
    return CostTools(db)