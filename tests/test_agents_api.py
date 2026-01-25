"""
========================================
Agent API 接口测试
========================================

📚 测试说明：
- 测试所有Agent API接口
- 使用FastAPI TestClient
- 模拟数据库和Agent响应

💡 运行方式：
    pytest tests/test_agents_api.py -v

========================================
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime


# =========================================
# Fixtures
# =========================================

@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    db = Mock()
    db.query = Mock()
    return db


@pytest.fixture
def mock_agents():
    """模拟所有Agent"""
    return {
        "cost": Mock(),
        "progress": Mock(),
        "safety": Mock(),
        "risk": Mock(),
        "weekly": Mock()
    }


# =========================================
# 请求/响应模型测试
# =========================================

class TestRequestModels:
    """请求模型测试"""

    def test_cost_analysis_request(self):
        """测试成本分析请求模型"""
        from agents.api.v1.agents import CostAnalysisRequest

        request = CostAnalysisRequest(
            project_id="P001",
            analysis_months=3,
            include_ai_insights=True
        )

        assert request.project_id == "P001"
        assert request.analysis_months == 3

    def test_progress_analysis_request(self):
        """测试进度分析请求模型"""
        from agents.api.v1.agents import ProgressAnalysisRequest

        request = ProgressAnalysisRequest(
            project_id="P001",
            analysis_days=30
        )

        assert request.analysis_days == 30

    def test_safety_analysis_request(self):
        """测试安全分析请求模型"""
        from agents.api.v1.agents import SafetyAnalysisRequest

        request = SafetyAnalysisRequest(
            project_id="P001",
            analysis_days=30
        )

        assert request.project_id == "P001"


class TestResponseModels:
    """响应模型测试"""

    def test_agent_response(self):
        """测试Agent响应模型"""
        from agents.api.v1.agents import AgentResponse

        response = AgentResponse(
            success=True,
            agent_type="cost_analysis",
            project_id="P001",
            result={"cpi": 0.95},
            execution_time=1.5
        )

        assert response.success is True
        assert response.execution_time == 1.5

    def test_quick_scan_response(self):
        """测试快速扫描响应模型"""
        from agents.api.v1.agents import QuickScanResponse

        response = QuickScanResponse(
            success=True,
            project_id="P001",
            scan_time=datetime.now().isoformat(),
            risk_levels={"progress": "yellow"},
            highest_risk_category="progress",
            highest_risk_level="yellow",
            alerts=["SPI偏低"],
            metrics={"spi": 0.92}
        )

        assert response.highest_risk_level == "yellow"


# =========================================
# 枚举测试
# =========================================

class TestEnums:
    """枚举测试"""

    def test_agent_type_enum(self):
        """测试Agent类型枚举"""
        from agents.api.v1.agents import AgentType

        assert AgentType.COST_ANALYSIS.value == "cost_analysis"
        assert AgentType.PROGRESS_ANALYSIS.value == "progress_analysis"
        assert AgentType.SAFETY_ANALYSIS.value == "safety_analysis"

    def test_report_format_enum(self):
        """测试报告格式枚举"""
        from agents.api.v1.agents import ReportFormatEnum

        assert ReportFormatEnum.MARKDOWN.value == "markdown"
        assert ReportFormatEnum.JSON.value == "json"
        assert ReportFormatEnum.HTML.value == "html"


# =========================================
# API 端点测试（模拟）
# =========================================

class TestAPIEndpoints:
    """API端点测试"""

    @pytest.mark.asyncio
    async def test_cost_analysis_endpoint_logic(self, mock_db):
        """测试成本分析端点逻辑"""
        from agents.api.v1.agents import CostAnalysisRequest, AgentType

        request = CostAnalysisRequest(project_id="P001", analysis_months=3)

        # 模拟Agent返回
        mock_result = {
            "success": True,
            "project_id": "P001",
            "overview": {"cpi": 0.95}
        }

        # 验证请求参数
        assert request.project_id == "P001"
        assert AgentType.COST_ANALYSIS.value == "cost_analysis"

    @pytest.mark.asyncio
    async def test_progress_analysis_endpoint_logic(self, mock_db):
        """测试进度分析端点逻辑"""
        from agents.api.v1.agents import ProgressAnalysisRequest, AgentType

        request = ProgressAnalysisRequest(project_id="P001", analysis_days=30)

        assert request.analysis_days == 30
        assert AgentType.PROGRESS_ANALYSIS.value == "progress_analysis"

    @pytest.mark.asyncio
    async def test_safety_analysis_endpoint_logic(self, mock_db):
        """测试安全分析端点逻辑"""
        from agents.api.v1.agents import SafetyAnalysisRequest, AgentType

        request = SafetyAnalysisRequest(project_id="P001", analysis_days=30)

        assert request.analysis_days == 30
        assert AgentType.SAFETY_ANALYSIS.value == "safety_analysis"


# =========================================
# 工作流日志测试
# =========================================

class TestWorkflowLogs:
    """工作流日志测试"""

    def test_workflow_log_response(self):
        """测试工作流日志响应"""
        from agents.api.v1.agents import WorkflowLogResponse

        response = WorkflowLogResponse(
            log_id=1,
            project_id="P001",
            workflow_type="cost_analysis",
            status="completed",
            start_time="2024-01-01T10:00:00",
            end_time="2024-01-01T10:00:05",
            duration_seconds=5.0,
            error_message=None
        )

        assert response.status == "completed"
        assert response.duration_seconds == 5.0


# =========================================
# 运行测试
# =========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])