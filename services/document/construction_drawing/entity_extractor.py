"""
========================================
施工图实体提取器
========================================

📚 模块说明：
- 从解析结果中提取结构化实体
- 支持规则+LLM混合提取策略
- 输出标准化的图谱节点

🎯 提取实体类型：
1. 构件实体（Component）
2. 材料实体（Material）
3. 尺寸实体（Dimension）
4. 规范实体（Specification）

========================================
"""
from typing import List, Dict, Any, Optional
import uuid

from models.graph_models import (
    GraphNode, ComponentNode, MaterialNode, DimensionNode,
    SpecificationNode, NodeLabel, ComponentType, MaterialType,
    DimensionType, create_component_node, create_material_node,
    create_specification_node, create_dimension_node
)
from core.logger import logger


class EntityExtractor:
    """
    实体提取器

    🔧 提取策略：
    1. 规则提取：基于正则表达式和模式匹配
    2. LLM提取：使用大模型识别复杂实体（可选）
    3. 后处理：去重、规范化、验证
    """

    def __init__(self, use_llm: bool = True):
        """
        初始化提取器

        参数：
            use_llm: 是否使用 LLM 增强提取
        """
        self.use_llm = use_llm
        self._llm_client = None

    @property
    def llm_client(self):
        """延迟加载 LLM 客户端"""
        if self._llm_client is None and self.use_llm:
            try:
                from services.llm.llm_client import LLMClient
                self._llm_client = LLMClient()
            except ImportError:
                logger.warning("LLMClient 未找到，LLM 增强提取不可用")
                self.use_llm = False
        return self._llm_client

    def extract_entities(
        self,
        parsed_drawing: Dict[str, Any],
        document_id: str
    ) -> Dict[str, List[GraphNode]]:
        """
        提取所有实体

        参数：
            parsed_drawing: 施工图解析结果
            document_id: 文档 ID

        返回：
            {
                "components": List[ComponentNode],
                "materials": List[MaterialNode],
                "dimensions": List[DimensionNode],
                "specifications": List[SpecificationNode],
            }
        """
        logger.info(f"开始提取实体: doc_id={document_id}")

        entities = {
            "components": [],
            "materials": [],
            "dimensions": [],
            "specifications": [],
        }

        # 1. 规则提取
        entities["components"] = self._extract_components(
            parsed_drawing.get("components", []),
            document_id
        )

        entities["materials"] = self._extract_materials(
            parsed_drawing.get("materials", []),
            document_id
        )

        entities["dimensions"] = self._extract_dimensions(
            parsed_drawing.get("dimensions", []),
            document_id
        )

        entities["specifications"] = self._extract_specifications(
            parsed_drawing.get("specifications", []),
            document_id
        )

        # 2. LLM 增强提取（可选）
        if self.use_llm and self.llm_client:
            text = parsed_drawing.get("text", "")
            if text and len(text) > 100:
                try:
                    llm_entities = self._llm_extract_entities(text, document_id)
                    # 合并 LLM 提取的实体
                    for key in entities:
                        if key in llm_entities:
                            entities[key].extend(llm_entities[key])
                except Exception as e:
                    logger.warning(f"LLM 实体提取失败: {e}")

        # 3. 后处理：去重
        for key in entities:
            entities[key] = self._deduplicate_entities(entities[key])

        logger.info(
            f"实体提取完成 | "
            f"构件: {len(entities['components'])} | "
            f"材料: {len(entities['materials'])} | "
            f"尺寸: {len(entities['dimensions'])} | "
            f"规范: {len(entities['specifications'])}"
        )

        return entities

    def _extract_components(
        self,
        components: List[Dict],
        document_id: str
    ) -> List[ComponentNode]:
        """提取构件实体"""
        nodes = []

        for comp in components:
            comp_type = comp.get("type", "other")
            code = comp.get("code", "")

            if not code:
                continue

            node = create_component_node(
                code=code,
                component_type=comp_type,
                doc_id=document_id,
            )
            node.properties["confidence"] = comp.get("confidence", 0.9)
            node.properties["source"] = comp.get("source", "rule")
            nodes.append(node)

        return nodes

    def _extract_materials(
        self,
        materials: List[Dict],
        document_id: str
    ) -> List[MaterialNode]:
        """提取材料实体"""
        nodes = []

        for mat in materials:
            mat_type = mat.get("type", "other")
            grade = mat.get("grade", "")

            if not grade:
                continue

            node = create_material_node(
                material_type=mat_type,
                grade=grade,
                doc_id=document_id,
            )
            node.properties["confidence"] = mat.get("confidence", 0.9)
            node.properties["source"] = mat.get("source", "rule")
            nodes.append(node)

        return nodes

    def _extract_dimensions(
        self,
        dimensions: List[Dict],
        document_id: str
    ) -> List[DimensionNode]:
        """提取尺寸实体"""
        nodes = []

        for dim in dimensions:
            dim_type = dim.get("type", "length")
            value_str = str(dim.get("value", "0"))

            # 解析数值
            value = self._parse_dimension_value(value_str)

            node = create_dimension_node(
                dim_type=dim_type,
                value=value,
                value_str=value_str,
                unit=dim.get("unit", "mm"),
            )
            node.properties["doc_id"] = document_id
            node.properties["source"] = dim.get("source", "rule")
            nodes.append(node)

        return nodes

    def _extract_specifications(
        self,
        specs: List[Dict],
        document_id: str
    ) -> List[SpecificationNode]:
        """提取规范实体"""
        nodes = []

        for spec in specs:
            code = spec.get("code", "")

            if not code:
                continue

            node = create_specification_node(
                spec_code=code,
            )
            node.properties["doc_id"] = document_id
            node.properties["confidence"] = spec.get("confidence", 0.95)
            node.properties["source"] = spec.get("source", "rule")
            nodes.append(node)

        return nodes

    def _llm_extract_entities(
        self,
        text: str,
        document_id: str
    ) -> Dict[str, List[GraphNode]]:
        """使用 LLM 提取实体"""
        # 截取文本避免超长
        text_sample = text[:3000] if len(text) > 3000 else text

        prompt = f"""请从以下施工图文本中提取实体信息，返回 JSON 格式。

文本：
{text_sample}

请提取以下类型的实体：
1. 构件（type: beam/column/slab/wall/foundation）- 识别构件编号如 KL-1, KZ-2
2. 材料（type: concrete/steel/rebar）- 识别材料等级如 C30, HRB400
3. 规范引用（识别规范编号如 GB50010-2010）

返回格式（仅返回JSON，不要其他内容）：
{{
    "components": [{{"type": "beam", "code": "KL-1"}}],
    "materials": [{{"type": "concrete", "grade": "C30"}}],
    "specifications": [{{"code": "GB50010-2010"}}]
}}
"""

        try:
            # 这里调用 LLM，实际实现时需要根据 LLMClient 的接口调整
            # response = self.llm_client.chat(prompt)
            # 解析 JSON 响应...
            pass
        except Exception as e:
            logger.warning(f"LLM 提取失败: {e}")

        return {"components": [], "materials": [], "specifications": []}

    def _parse_dimension_value(self, value_str: str) -> float:
        """解析尺寸数值"""
        try:
            # 处理类似 "300x500" 的情况，取第一个值
            if "x" in value_str.lower():
                return float(value_str.lower().split("x")[0])

            # 移除非数字字符
            import re
            numbers = re.findall(r"[\d.]+", value_str)
            if numbers:
                return float(numbers[0])

            return 0.0
        except (ValueError, IndexError):
            return 0.0

    def _deduplicate_entities(self, entities: List[GraphNode]) -> List[GraphNode]:
        """实体去重"""
        seen = set()
        unique = []

        for entity in entities:
            # 根据关键属性生成去重键
            if isinstance(entity, ComponentNode):
                key = f"comp:{entity.code}"
            elif isinstance(entity, MaterialNode):
                key = f"mat:{entity.properties.get('grade', '')}"
            elif isinstance(entity, SpecificationNode):
                key = f"spec:{entity.spec_code}"
            elif isinstance(entity, DimensionNode):
                key = f"dim:{entity.properties.get('dimension_type', '')}:{entity.properties.get('value', '')}"
            else:
                key = f"{entity.label}:{entity.id}"

            if key not in seen:
                seen.add(key)
                unique.append(entity)

        return unique

    def extract_from_tables(
        self,
        tables: List[Dict],
        document_id: str
    ) -> Dict[str, List[GraphNode]]:
        """
        从表格中提取实体

        参数：
            tables: 表格数据列表
            document_id: 文档 ID

        返回：
            提取的实体字典
        """
        entities = {
            "components": [],
            "materials": [],
            "dimensions": [],
        }

        for table in tables:
            data = table.get("data", [])
            if not data or len(data) < 2:
                continue

            # 尝试识别表格类型
            header = data[0] if data else []
            header_text = " ".join([str(h) for h in header if h]).lower()

            # 材料表
            if "材料" in header_text or "混凝土" in header_text or "钢筋" in header_text:
                self._extract_from_material_table(data, document_id, entities)

            # 构件表
            elif "构件" in header_text or "梁" in header_text or "柱" in header_text:
                self._extract_from_component_table(data, document_id, entities)

        return entities

    def _extract_from_material_table(
        self,
        data: List[List],
        document_id: str,
        entities: Dict
    ):
        """从材料表提取"""
        import re

        for row in data[1:]:  # 跳过表头
            row_text = " ".join([str(cell) for cell in row if cell])

            # 提取混凝土等级
            concrete_matches = re.findall(r"C\d{2,3}", row_text)
            for grade in concrete_matches:
                node = create_material_node("concrete", grade, document_id)
                node.properties["source"] = "table"
                entities["materials"].append(node)

            # 提取钢筋等级
            rebar_matches = re.findall(r"HRB\d{3}", row_text)
            for grade in rebar_matches:
                node = create_material_node("rebar", grade, document_id)
                node.properties["source"] = "table"
                entities["materials"].append(node)

    def _extract_from_component_table(
        self,
        data: List[List],
        document_id: str,
        entities: Dict
    ):
        """从构件表提取"""
        import re

        for row in data[1:]:  # 跳过表头
            row_text = " ".join([str(cell) for cell in row if cell])

            # 提取构件编号
            component_patterns = [
                (r"[KDL]+[-\s]?\d+[a-zA-Z]?", "beam"),
                (r"[KZ]+[-\s]?\d+[a-zA-Z]?", "column"),
            ]

            for pattern, comp_type in component_patterns:
                matches = re.findall(pattern, row_text)
                for code in matches:
                    node = create_component_node(code, comp_type, document_id)
                    node.properties["source"] = "table"
                    entities["components"].append(node)
