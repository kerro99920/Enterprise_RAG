# README 更新补充 - Agent智能分析模块

> 本文档是对主README.md的补充，新增Agent智能分析模块说明

---

## 📦 新增模块：Agent 智能分析

### 模块说明

Agent模块提供项目管理领域的智能分析能力，包括成本、进度、安全三大维度的自动化分析和AI增强建议。

### 目录结构更新

在原有目录结构基础上，新增以下内容：

```
enterprise_rag/
├── agents/                     # 🆕 Agent智能分析模块
│   ├── __init__.py             # 包初始化，导出所有Agent
│   ├── weekly_report_agent.py  # 周报生成Agent
│   ├── risk_agent.py           # 风险分析Agent
│   ├── cost_agent.py           # 🆕 成本分析Agent
│   ├── progress_agent.py       # 🆕 进度分析Agent
│   ├── safety_agent.py         # 🆕 安全分析Agent
│   └── api/
│       └── v1/
│           ├── __init__.py
│           └── agents.py       # Agent API路由
│
├── tools/                      # 工具模块（Agent依赖）
│   ├── progress_tools.py       # 进度分析工具
│   ├── cost_tools.py           # 成本分析工具
│   ├── safety_tools.py         # 安全分析工具
│   └── rag_tool.py             # RAG检索工具
│
├── tests/                      # 🆕 测试用例更新
│   ├── test_agents.py          # Agent单元测试
│   └── test_agents_api.py      # API接口测试
│
└── docs/
    └── AGENTS_MODULE.md        # 🆕 Agent模块详细文档
```

---

## 🤖 Agent 列表

| Agent | 文件 | 功能描述 |
|-------|------|----------|
| **WeeklyReportAgent** | `weekly_report_agent.py` | 自动生成项目周报 |
| **RiskAnalysisAgent** | `risk_agent.py` | 多维度风险分析与预警 |
| **CostAnalysisAgent** | `cost_agent.py` | 成本分析、CPI计算、超支识别 |
| **ProgressAnalysisAgent** | `progress_agent.py` | 进度分析、SPI计算、延期识别 |
| **SafetyAnalysisAgent** | `safety_agent.py` | 安全检查分析、隐患跟踪 |

---

## 🔌 API 接口新增

### 基础路径
```
/api/v1/agents
```

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/weekly-report` | 生成项目周报 |
| POST | `/risk-analysis` | 执行风险分析 |
| GET | `/risk-analysis/{project_id}/quick-scan` | 快速风险扫描 |
| POST | `/cost-analysis` | 执行成本分析 |
| GET | `/cost-analysis/{project_id}/quick-check` | 快速成本检查 |
| POST | `/progress-analysis` | 执行进度分析 |
| GET | `/progress-analysis/{project_id}/quick-check` | 快速进度检查 |
| POST | `/safety-analysis` | 执行安全分析 |
| GET | `/safety-analysis/{project_id}/quick-check` | 快速安全检查 |
| GET | `/dashboard/{project_id}` | 项目仪表盘（聚合数据） |
| GET | `/workflows` | 查询工作流日志 |
| GET | `/workflows/{log_id}` | 工作流详情 |

---

## 📖 使用示例

### 1. Python 代码调用

```python
# 成本分析
from agents import get_cost_agent

async def analyze_project_cost(db, project_id):
    agent = get_cost_agent(db)
    result = await agent.analyze_costs(
        project_id=project_id,
        analysis_months=3,
        include_ai_insights=True
    )
    return result

# 进度分析
from agents import get_progress_agent

async def analyze_project_progress(db, project_id):
    agent = get_progress_agent(db)
    result = await agent.analyze_progress(
        project_id=project_id,
        analysis_days=30
    )
    return result

# 安全分析
from agents import get_safety_agent

async def analyze_project_safety(db, project_id):
    agent = get_safety_agent(db)
    result = await agent.analyze_safety(
        project_id=project_id,
        analysis_days=30
    )
    return result
```

### 2. API 调用示例

```bash
# 成本分析
curl -X POST "http://localhost:8000/api/v1/agents/cost-analysis" \
     -H "Content-Type: application/json" \
     -d '{"project_id": "P001", "analysis_months": 3, "include_ai_insights": true}'

# 进度分析
curl -X POST "http://localhost:8000/api/v1/agents/progress-analysis" \
     -H "Content-Type: application/json" \
     -d '{"project_id": "P001", "analysis_days": 30}'

# 安全分析
curl -X POST "http://localhost:8000/api/v1/agents/safety-analysis" \
     -H "Content-Type: application/json" \
     -d '{"project_id": "P001", "analysis_days": 30}'

# 快速检查（适用于仪表盘）
curl "http://localhost:8000/api/v1/agents/cost-analysis/P001/quick-check"
curl "http://localhost:8000/api/v1/agents/progress-analysis/P001/quick-check"
curl "http://localhost:8000/api/v1/agents/safety-analysis/P001/quick-check"

# 项目仪表盘（一次获取所有关键指标）
curl "http://localhost:8000/api/v1/agents/dashboard/P001"
```

### 3. 响应示例

```json
{
  "success": true,
  "agent_type": "cost_analysis",
  "project_id": "P001",
  "result": {
    "overview": {
      "total_budget": 1000000,
      "total_actual": 650000,
      "cpi": 0.95,
      "variance_rate": -5.0,
      "risk_level": "medium"
    },
    "category_costs": [...],
    "overruns": [...],
    "trends": [...],
    "suggestions": [
      "加强材料采购管理",
      "优化施工组织"
    ],
    "ai_insights": [
      "基于历史数据分析，建议重点关注材料成本控制"
    ]
  },
  "execution_time": 2.5
}
```

---

## ⚙️ 集成配置

### 1. 路由注册 (main.py)

```python
from agents.api.v1 import agents

app.include_router(
    agents.router,
    prefix="/api/v1/agents",
    tags=["Agents"]
)
```

### 2. 依赖检查

确保以下模块已正确配置：

- `tools/progress_tools.py` - 进度工具
- `tools/cost_tools.py` - 成本工具
- `tools/safety_tools.py` - 安全工具
- `tools/rag_tool.py` - RAG检索工具
- `models/project.py` - 包含 `AgentWorkflowLog` 模型

---

## 🧪 测试

```bash
# 运行所有Agent测试
pytest tests/test_agents.py -v

# 运行API测试
pytest tests/test_agents_api.py -v

# 生成覆盖率报告
pytest tests/ --cov=agents --cov-report=html
```

---

## 📊 风险阈值说明

### 成本风险 (CPI)
| 等级 | CPI范围 | 偏差率 |
|------|---------|--------|
| Critical | < 0.75 | > 15% |
| High | 0.75-0.85 | 10-15% |
| Medium | 0.85-0.95 | 5-10% |
| Low | >= 0.95 | < 5% |

### 进度风险 (SPI)
| 等级 | SPI范围 | 延期任务数 |
|------|---------|-----------|
| Critical | < 0.75 | >= 10 |
| High | 0.75-0.85 | >= 5 |
| Medium | 0.85-0.95 | - |
| Low | >= 0.95 | < 5 |

### 安全风险
| 等级 | 合格率 | 重大隐患数 |
|------|--------|-----------|
| Critical | < 80% | >= 5 |
| High | 80-90% | >= 3 |
| Medium | 90-95% | - |
| Low | >= 95% | < 3 |

---

## 🔄 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | - | 初始版本，包含周报和风险Agent |
| **1.1.0** | **当前** | **新增成本、进度、安全分析Agent** |
| 1.1.1 | - | 修复API路由导入问题 |
| 1.1.2 | - | 添加单元测试和完整文档 |

---

## 📚 相关文档

- [Agent模块详细文档](docs/AGENTS_MODULE.md)
- [API接口文档](http://localhost:8000/docs)
- [Tools工具模块说明](tools/README.md)