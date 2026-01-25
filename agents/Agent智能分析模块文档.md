# Agent 智能分析模块文档

## 📚 模块概述

Agent模块是企业级RAG智能问答系统的核心组件，负责编排各种分析工具，提供项目管理领域的智能分析能力。

### 🎯 核心价值

- **自动化分析**：自动采集和分析项目数据
- **多维度评估**：从进度、成本、安全多角度评估项目状态
- **智能预警**：基于阈值和趋势自动生成风险预警
- **AI增强**：集成RAG技术生成专业建议

---

## 🏗️ 模块架构

```
agents/
├── __init__.py              # 包初始化，导出所有Agent
├── cost_agent.py            # 成本分析Agent
├── progress_agent.py        # 进度分析Agent
├── safety_agent.py          # 安全分析Agent
├── risk_agent.py            # 风险分析Agent (已有)
├── weekly_report_agent.py   # 周报生成Agent (已有)
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       └── agents.py        # API路由接口
tests/
├── __init__.py
├── test_agents.py           # 单元测试
└── test_agents_api.py       # API测试
```

---

## 📊 Agent 详细说明

### 1. CostAnalysisAgent (成本分析Agent)

**文件位置**：`agents/cost_agent.py`

**职责**：多维度成本分析与评估

**核心功能**：

| 功能 | 说明 |
|------|------|
| 成本概览 | 预算执行情况、CPI计算 |
| 分类统计 | 按材料/人工/机械等分类 |
| 超支识别 | 识别超支项和原因分析 |
| 趋势分析 | 成本变化趋势判断 |
| 预测分析 | 最终成本预测 |
| 风险评估 | 成本风险识别 |
| 建议生成 | 基于RAG生成控制建议 |

**风险阈值**：

| 等级 | CPI | 偏差率 |
|------|-----|--------|
| Critical | < 0.75 | > 15% |
| High | 0.75-0.85 | 10-15% |
| Medium | 0.85-0.95 | 5-10% |
| Low | >= 0.95 | < 5% |

**使用示例**：

```python
from agents import get_cost_agent

agent = get_cost_agent(db)

# 全面分析
result = await agent.analyze_costs(
    project_id="P001",
    analysis_months=3,
    include_ai_insights=True
)

# 快速检查
quick_result = await agent.quick_cost_check("P001")
```

---

### 2. ProgressAnalysisAgent (进度分析Agent)

**文件位置**：`agents/progress_agent.py`

**职责**：项目进度多维度分析

**核心功能**：

| 功能 | 说明 |
|------|------|
| 进度概览 | 项目整体进度状态 |
| SPI分析 | 进度绩效指数计算 |
| 延期识别 | 延期任务检测与分类 |
| 关键路径 | 关键路径任务分析 |
| 趋势分析 | 进度变化趋势 |
| 完工预测 | 项目完工时间预测 |
| 瓶颈识别 | 资源和进度瓶颈 |

**风险阈值**：

| 等级 | SPI | 延期任务数 |
|------|-----|-----------|
| Critical | < 0.75 | >= 10 |
| High | 0.75-0.85 | >= 5 |
| Medium | 0.85-0.95 | - |
| Low | >= 0.95 | < 5 |

**使用示例**：

```python
from agents import get_progress_agent

agent = get_progress_agent(db)

# 全面分析
result = await agent.analyze_progress(
    project_id="P001",
    analysis_days=30,
    include_ai_insights=True
)

# 快速检查
quick_result = await agent.quick_progress_check("P001")
```

---

### 3. SafetyAnalysisAgent (安全分析Agent)

**文件位置**：`agents/safety_agent.py`

**职责**：安全检查数据分析与预警

**核心功能**：

| 功能 | 说明 |
|------|------|
| 安全概览 | 检查合格率、隐患统计 |
| 隐患分析 | 按类型、等级分类 |
| 频发问题 | 识别高频安全问题 |
| 未闭环项 | 跟踪待整改问题 |
| 趋势分析 | 安全状况变化趋势 |
| 整改计划 | 生成分阶段整改方案 |
| 预警机制 | 安全风险自动预警 |

**风险阈值**：

| 等级 | 合格率 | 重大隐患数 |
|------|--------|-----------|
| Critical | < 80% | >= 5 |
| High | 80-90% | >= 3 |
| Medium | 90-95% | - |
| Low | >= 95% | < 3 |

**使用示例**：

```python
from agents import get_safety_agent

agent = get_safety_agent(db)

# 全面分析
result = await agent.analyze_safety(
    project_id="P001",
    analysis_days=30,
    include_ai_insights=True
)

# 快速检查
quick_result = await agent.quick_safety_check("P001", days=7)
```

---

## 🔌 API 接口说明

### 基础路径

```
/api/v1/agents
```

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/cost-analysis` | 执行成本分析 |
| GET | `/cost-analysis/{project_id}/quick-check` | 快速成本检查 |
| POST | `/progress-analysis` | 执行进度分析 |
| GET | `/progress-analysis/{project_id}/quick-check` | 快速进度检查 |
| POST | `/safety-analysis` | 执行安全分析 |
| GET | `/safety-analysis/{project_id}/quick-check` | 快速安全检查 |
| POST | `/risk-analysis` | 执行风险分析 |
| GET | `/risk-analysis/{project_id}/quick-scan` | 快速风险扫描 |
| POST | `/weekly-report` | 生成周报 |
| GET | `/dashboard/{project_id}` | 项目仪表盘 |
| GET | `/workflows` | 工作流日志列表 |
| GET | `/workflows/{log_id}` | 工作流详情 |

### 请求示例

**成本分析**：

```bash
curl -X POST "/api/v1/agents/cost-analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "P001",
    "analysis_months": 3,
    "include_ai_insights": true
  }'
```

**项目仪表盘**：

```bash
curl -X GET "/api/v1/agents/dashboard/P001"
```

### 响应格式

```json
{
  "success": true,
  "agent_type": "cost_analysis",
  "project_id": "P001",
  "result": {
    "overview": {
      "cpi": 0.95,
      "variance_rate": -5.0,
      "risk_level": "medium"
    },
    "suggestions": ["..."],
    "ai_insights": ["..."]
  },
  "execution_time": 2.5
}
```

---

## 🧪 测试说明

### 运行测试

```bash
# 运行所有Agent测试
pytest tests/test_agents.py -v

# 运行API测试
pytest tests/test_agents_api.py -v

# 运行特定测试
pytest tests/test_agents.py::TestCostAnalysisAgent -v

# 生成覆盖率报告
pytest tests/ -v --cov=agents --cov-report=html
```

### 测试覆盖

| 测试类 | 覆盖内容 |
|--------|----------|
| TestCostAnalysisAgent | 成本分析全流程 |
| TestProgressAnalysisAgent | 进度分析全流程 |
| TestSafetyAnalysisAgent | 安全分析全流程 |
| TestDataStructures | 数据结构验证 |
| TestThresholds | 阈值判断逻辑 |
| TestAPIEndpoints | API接口逻辑 |

---

## 🔧 集成指南

### 1. 注册路由

在 `main.py` 中添加：

```python
from agents.api.v1 import agents

app.include_router(
    agents.router,
    prefix="/api/v1/agents",
    tags=["Agents"]
)
```

### 2. 依赖配置

确保以下工具模块可用：

- `tools/progress_tools.py`
- `tools/cost_tools.py`
- `tools/safety_tools.py`
- `tools/rag_tool.py`

### 3. 数据库模型

确保 `AgentWorkflowLog` 模型已创建：

```python
from models.project import AgentWorkflowLog
```

---

## 📈 性能建议

1. **快速检查**：仪表盘展示使用 `quick_check` 方法
2. **完整分析**：详细报告使用完整 `analyze` 方法
3. **AI洞察**：非必要时可关闭 `include_ai_insights=False`
4. **并发控制**：高并发场景考虑添加限流

---

## 🔄 更新日志

| 版本 | 日期      | 更新内容 |
|------|---------|----------|
| 1.0.0 | 2026-01 | 初始版本，包含周报和风险Agent |
| 1.1.0 | 2026-01 | 新增成本、进度、安全分析Agent |
| 1.1.1 | 2026-01 | 修复API路由导入问题 |
| 1.1.2 | 2026-01 | 添加单元测试和文档 |