"""
========================================
施工图关系提取器
========================================

📚 模块说明：
- 从实体之间提取关系
- 支持规则+上下文推理
- 输出标准化的图谱关系

🔗 提取关系类型：
1. USES_MATERIAL - 构件使用材料
2. HAS_DIMENSION - 构件具有尺寸
3. REFERS_TO - 引用规范
4. CONNECTED_TO - 构件连接关系
5. BELONGS_TO - 属于文档

========================================
"""
from typing import List, Dict, Any

from models.graph_models import (
    GraphNode, GraphRelationship, RelationType,
    ComponentNode, MaterialNode, DimensionNode, SpecificationNode,
    create_relationship
)
from core.logger import logger


class RelationExtractor:
    """
    关系提取器

    🔧 提取策略：
    1. 邻近关系：同一页面/段落中的实体
    2. 共现关系：同一句子中的实体
    3. 规则推理：基于领域知识的推理
    """

    # 构件-材料兼容性规则
    COMPONENT_MATERIAL_RULES = {
        # 混凝土构件使用混凝土和钢筋
        "beam": ["concrete", "rebar"],
        "column": ["concrete", "rebar"],
        "slab": ["concrete", "rebar"],
        "wall": ["concrete", "rebar"],
        "foundation": ["concrete", "rebar"],
        "shear_wall": ["concrete", "rebar"],
        # 钢结构构件使用钢材
        "steel_beam": ["steel"],
        "steel_column": ["steel"],
    }

    def __init__(self):
        """初始化关系提取器"""
        pass

    def extract_relations(
        self,
        entities: Dict[str, List[GraphNode]],
        parsed_drawing: Dict[str, Any],
        document_id: str
    ) -> List[GraphRelationship]:
        """
        提取所有关系

        参数：
            entities: 提取的实体字典
            parsed_drawing: 解析结果
            document_id: 文档 ID

        返回：
            List[GraphRelationship]: 关系列表
        """
        logger.info(f"开始提取关系: doc_id={document_id}")

        relations = []

        # 1. 构件-材料关系
        relations.extend(
            self._extract_component_material_relations(
                entities.get("components", []),
                entities.get("materials", []),
            )
        )

        # 2. 构件-尺寸关系
        relations.extend(
            self._extract_component_dimension_relations(
                entities.get("components", []),
                entities.get("dimensions", []),
            )
        )

        # 3. 文档-规范引用关系
        relations.extend(
            self._extract_document_spec_relations(
                document_id,
                entities.get("specifications", [])
            )
        )

        # 4. 构件-文档归属关系
        relations.extend(
            self._extract_belongs_to_relations(
                entities.get("components", []),
                document_id
            )
        )

        # 5. 材料-文档归属关系
        relations.extend(
            self._extract_material_belongs_to_relations(
                entities.get("materials", []),
                document_id
            )
        )

        logger.info(f"关系提取完成 | 总计: {len(relations)} 条关系")

        return relations

    def _extract_component_material_relations(
        self,
        components: List[ComponentNode],
        materials: List[MaterialNode],
    ) -> List[GraphRelationship]:
        """
        提取构件-材料关系

        基于领域规则推断构件使用的材料
        """
        relations = []

        for comp in components:
            comp_type = comp.properties.get("component_type", "other")

            # 获取该类型构件可能使用的材料类型
            allowed_materials = self.COMPONENT_MATERIAL_RULES.get(comp_type, [])

            for mat in materials:
                mat_type = mat.properties.get("material_type", "")

                # 检查材料是否适用于该构件
                if mat_type in allowed_materials:
                    rel = create_relationship(
                        from_node_id=comp.id,
                        to_node_id=mat.id,
                        rel_type="uses_material",
                        properties={
                            "source": "rule_inference",
                            "confidence": 0.8,
                        }
                    )
                    relations.append(rel)

        return relations

    def _extract_component_dimension_relations(
        self,
        components: List[ComponentNode],
        dimensions: List[DimensionNode],
    ) -> List[GraphRelationship]:
        """
        提取构件-尺寸关系

        将尺寸关联到构件（基于同文档共现）
        """
        relations = []

        # 简化策略：同一文档中的尺寸关联到所有构件
        # 实际应用中可以基于位置或上下文进行更精确的匹配
        for comp in components:
            comp_doc_id = comp.properties.get("doc_id", "")

            for dim in dimensions:
                dim_doc_id = dim.properties.get("doc_id", "")

                # 同一文档中的实体才建立关系
                if comp_doc_id == dim_doc_id:
                    # 根据尺寸类型判断是否适用
                    dim_type = dim.properties.get("dimension_type", "")

                    if self._is_dimension_applicable(comp, dim_type):
                        rel = create_relationship(
                            from_node_id=comp.id,
                            to_node_id=dim.id,
                            rel_type="has_dimension",
                            properties={
                                "source": "co_occurrence",
                                "confidence": 0.7,
                            }
                        )
                        relations.append(rel)

        return relations

    def _extract_document_spec_relations(
        self,
        document_id: str,
        specifications: List[SpecificationNode]
    ) -> List[GraphRelationship]:
        """提取文档-规范引用关系"""
        relations = []

        for spec in specifications:
            rel = create_relationship(
                from_node_id=f"doc_{document_id}",
                to_node_id=spec.id,
                rel_type="refers_to",
                properties={
                    "source": "extraction",
                    "confidence": 0.95,
                }
            )
            relations.append(rel)

        return relations

    def _extract_belongs_to_relations(
        self,
        components: List[ComponentNode],
        document_id: str
    ) -> List[GraphRelationship]:
        """提取构件-文档归属关系"""
        relations = []

        for comp in components:
            rel = create_relationship(
                from_node_id=comp.id,
                to_node_id=f"doc_{document_id}",
                rel_type="belongs_to",
                properties={
                    "source": "document",
                }
            )
            relations.append(rel)

        return relations

    def _extract_material_belongs_to_relations(
        self,
        materials: List[MaterialNode],
        document_id: str
    ) -> List[GraphRelationship]:
        """提取材料-文档归属关系"""
        relations = []

        for mat in materials:
            rel = create_relationship(
                from_node_id=mat.id,
                to_node_id=f"doc_{document_id}",
                rel_type="belongs_to",
                properties={
                    "source": "document",
                }
            )
            relations.append(rel)

        return relations

    def _is_dimension_applicable(
        self,
        component: ComponentNode,
        dim_type: str
    ) -> bool:
        """判断尺寸类型是否适用于构件"""
        comp_type = component.properties.get("component_type", "")

        # 定义构件-尺寸适用规则
        applicable_rules = {
            "beam": ["section", "span", "height", "width"],
            "column": ["section", "height"],
            "slab": ["thickness", "span"],
            "wall": ["thickness", "height", "length"],
            "foundation": ["thickness", "width", "length"],
        }

        allowed_dims = applicable_rules.get(comp_type, [])
        return dim_type in allowed_dims

    def extract_connected_relations(
        self,
        components: List[ComponentNode],
        parsed_drawing: Dict[str, Any]
    ) -> List[GraphRelationship]:
        """
        提取构件连接关系

        基于构件编号和类型推断连接关系
        例如：梁连接柱，板支撑在梁上
        """
        relations = []

        # 按类型分组
        beams = [c for c in components if c.properties.get("component_type") == "beam"]
        columns = [c for c in components if c.properties.get("component_type") == "column"]
        slabs = [c for c in components if c.properties.get("component_type") == "slab"]

        # 梁-柱连接（同一楼层的梁和柱）
        for beam in beams:
            beam_floor = beam.properties.get("floor", "")

            for column in columns:
                column_floor = column.properties.get("floor", "")

                if beam_floor == column_floor and beam_floor:
                    rel = create_relationship(
                        from_node_id=beam.id,
                        to_node_id=column.id,
                        rel_type="connected_to",
                        properties={
                            "connection_type": "beam_column",
                            "source": "inference",
                            "confidence": 0.6,
                        }
                    )
                    relations.append(rel)

        # 板-梁连接（同一楼层的板和梁）
        for slab in slabs:
            slab_floor = slab.properties.get("floor", "")

            for beam in beams:
                beam_floor = beam.properties.get("floor", "")

                if slab_floor == beam_floor and slab_floor:
                    rel = create_relationship(
                        from_node_id=slab.id,
                        to_node_id=beam.id,
                        rel_type="connected_to",
                        properties={
                            "connection_type": "slab_beam",
                            "source": "inference",
                            "confidence": 0.6,
                        }
                    )
                    relations.append(rel)

        return relations
