"""
========================================
Neo4j 图数据库 Repository
========================================

📚 模块说明：
- 提供图数据库的数据访问层
- 封装常用的图操作
- 支持施工图知识图谱的 CRUD

🎯 核心功能：
1. 节点管理（创建、查询、更新、删除）
2. 关系管理（创建、查询、删除）
3. 图谱遍历和路径查询
4. 批量操作支持

🔧 使用方式：
    from repository.graph_repo import GraphRepository

    graph_repo = GraphRepository()

    # 创建构件节点
    graph_repo.create_component("KL-1", "beam", {"name": "框架梁"})

    # 查询构件
    components = graph_repo.find_components_by_type("beam")

========================================
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

from services.graph.neo4j_client import neo4j_client
from core.logger import logger


class GraphRepository:
    """
    图数据库 Repository

    职责：
    - 封装 Neo4j 操作
    - 提供领域特定的图操作方法
    - 管理施工图知识图谱数据
    """

    def __init__(self):
        """初始化 Repository"""
        self.client = neo4j_client

    # =========================================
    # 文档节点操作
    # =========================================

    def create_document_node(
        self,
        doc_id: str,
        name: str,
        doc_type: str,
        project_id: str = None,
        properties: Dict = None
    ) -> Dict:
        """
        创建文档节点

        参数：
            doc_id: 文档 ID
            name: 文档名称
            doc_type: 文档类型（construction_drawing, specification, etc.）
            project_id: 关联项目 ID
            properties: 额外属性
        """
        props = {
            "id": doc_id,
            "name": name,
            "doc_type": doc_type,
            "created_at": datetime.now().isoformat(),
        }
        if project_id:
            props["project_id"] = project_id
        if properties:
            props.update(properties)

        return self.client.create_node(["Document"], props)

    def find_document(self, doc_id: str) -> Optional[Dict]:
        """查找文档节点"""
        results = self.client.find_nodes("Document", {"id": doc_id}, limit=1)
        return results[0]["n"] if results else None

    def delete_document_and_relations(self, doc_id: str) -> Dict:
        """删除文档及其所有关联节点和关系"""
        query = """
        MATCH (d:Document {id: $doc_id})
        OPTIONAL MATCH (d)-[r1]->(n)
        OPTIONAL MATCH (n)-[r2]->()
        DETACH DELETE d, n
        """
        return self.client.execute_write(query, {"doc_id": doc_id})

    # =========================================
    # 构件节点操作
    # =========================================

    def create_component(
        self,
        component_id: str,
        code: str,
        component_type: str,
        doc_id: str,
        properties: Dict = None
    ) -> Dict:
        """
        创建构件节点

        参数：
            component_id: 构件 ID
            code: 构件编号（如 KL-1, KZ-2）
            component_type: 构件类型（beam, column, slab, wall, etc.）
            doc_id: 所属文档 ID
            properties: 额外属性
        """
        props = {
            "id": component_id,
            "code": code,
            "type": component_type,
            "doc_id": doc_id,
            "created_at": datetime.now().isoformat(),
        }
        if properties:
            props.update(properties)

        result = self.client.create_node(["Component"], props)

        # 创建与文档的归属关系
        self.create_belongs_to_relation(component_id, "Component", doc_id, "Document")

        return result

    def find_components_by_type(
        self,
        component_type: str,
        doc_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        按类型查找构件

        参数：
            component_type: 构件类型
            doc_id: 可选，限定文档范围
            limit: 返回数量限制
        """
        if doc_id:
            query = """
            MATCH (c:Component {type: $type, doc_id: $doc_id})
            RETURN c
            LIMIT $limit
            """
            params = {"type": component_type, "doc_id": doc_id, "limit": limit}
        else:
            query = """
            MATCH (c:Component {type: $type})
            RETURN c
            LIMIT $limit
            """
            params = {"type": component_type, "limit": limit}

        return self.client.execute_query(query, params)

    def find_component_by_code(self, code: str, doc_id: str = None) -> Optional[Dict]:
        """按编号查找构件"""
        if doc_id:
            results = self.client.find_nodes("Component", {"code": code, "doc_id": doc_id}, limit=1)
        else:
            results = self.client.find_nodes("Component", {"code": code}, limit=1)
        return results[0]["n"] if results else None

    # =========================================
    # 材料节点操作
    # =========================================

    def create_material(
        self,
        material_id: str,
        material_type: str,
        grade: str,
        doc_id: str,
        properties: Dict = None
    ) -> Dict:
        """
        创建材料节点

        参数：
            material_id: 材料 ID
            material_type: 材料类型（concrete, steel, rebar, etc.）
            grade: 材料等级（如 C30, HRB400）
            doc_id: 所属文档 ID
            properties: 额外属性
        """
        props = {
            "id": material_id,
            "type": material_type,
            "grade": grade,
            "doc_id": doc_id,
            "created_at": datetime.now().isoformat(),
        }
        if properties:
            props.update(properties)

        return self.client.create_node(["Material"], props)

    def find_materials_by_grade(self, grade: str, limit: int = 100) -> List[Dict]:
        """按等级查找材料"""
        return self.client.find_nodes("Material", {"grade": grade}, limit=limit)

    # =========================================
    # 规范节点操作
    # =========================================

    def create_specification(
        self,
        spec_id: str,
        code: str,
        name: str = None,
        properties: Dict = None
    ) -> Dict:
        """
        创建规范节点

        参数：
            spec_id: 规范 ID
            code: 规范编号（如 GB50010-2010）
            name: 规范名称
            properties: 额外属性
        """
        props = {
            "id": spec_id,
            "code": code,
            "created_at": datetime.now().isoformat(),
        }
        if name:
            props["name"] = name
        if properties:
            props.update(properties)

        return self.client.create_node(["Specification"], props)

    def find_or_create_specification(self, code: str) -> str:
        """查找或创建规范节点，返回规范 ID"""
        results = self.client.find_nodes("Specification", {"code": code}, limit=1)
        if results:
            return results[0]["n"]["id"]
        else:
            spec_id = f"spec_{uuid.uuid4().hex[:8]}"
            self.create_specification(spec_id, code)
            return spec_id

    # =========================================
    # 尺寸节点操作
    # =========================================

    def create_dimension(
        self,
        dim_id: str,
        dim_type: str,
        value: float,
        unit: str = "mm",
        properties: Dict = None
    ) -> Dict:
        """
        创建尺寸节点

        参数：
            dim_id: 尺寸 ID
            dim_type: 尺寸类型（length, width, height, thickness, etc.）
            value: 数值
            unit: 单位
            properties: 额外属性
        """
        props = {
            "id": dim_id,
            "type": dim_type,
            "value": value,
            "unit": unit,
            "created_at": datetime.now().isoformat(),
        }
        if properties:
            props.update(properties)

        return self.client.create_node(["Dimension"], props)

    # =========================================
    # 关系操作
    # =========================================

    def create_belongs_to_relation(
        self,
        from_id: str,
        from_label: str,
        to_id: str,
        to_label: str
    ) -> Dict:
        """创建 BELONGS_TO 关系"""
        return self.client.create_relationship(
            {"label": from_label, "props": {"id": from_id}},
            {"label": to_label, "props": {"id": to_id}},
            "BELONGS_TO"
        )

    def create_uses_material_relation(
        self,
        component_id: str,
        material_id: str,
        properties: Dict = None
    ) -> Dict:
        """创建构件使用材料关系"""
        return self.client.create_relationship(
            {"label": "Component", "props": {"id": component_id}},
            {"label": "Material", "props": {"id": material_id}},
            "USES_MATERIAL",
            properties
        )

    def create_has_dimension_relation(
        self,
        component_id: str,
        dimension_id: str
    ) -> Dict:
        """创建构件尺寸关系"""
        return self.client.create_relationship(
            {"label": "Component", "props": {"id": component_id}},
            {"label": "Dimension", "props": {"id": dimension_id}},
            "HAS_DIMENSION"
        )

    def create_refers_to_relation(
        self,
        doc_id: str,
        spec_id: str
    ) -> Dict:
        """创建文档引用规范关系"""
        return self.client.create_relationship(
            {"label": "Document", "props": {"id": doc_id}},
            {"label": "Specification", "props": {"id": spec_id}},
            "REFERS_TO"
        )

    def create_connected_to_relation(
        self,
        from_component_id: str,
        to_component_id: str,
        properties: Dict = None
    ) -> Dict:
        """创建构件连接关系"""
        return self.client.create_relationship(
            {"label": "Component", "props": {"id": from_component_id}},
            {"label": "Component", "props": {"id": to_component_id}},
            "CONNECTED_TO",
            properties
        )

    # =========================================
    # 图谱查询
    # =========================================

    def get_component_with_relations(self, component_id: str) -> Dict:
        """
        获取构件及其所有关联信息

        返回：
            {
                "component": {...},
                "materials": [...],
                "dimensions": [...],
                "specifications": [...],
                "connected_components": [...],
            }
        """
        query = """
        MATCH (c:Component {id: $id})
        OPTIONAL MATCH (c)-[:USES_MATERIAL]->(m:Material)
        OPTIONAL MATCH (c)-[:HAS_DIMENSION]->(d:Dimension)
        OPTIONAL MATCH (c)-[:BELONGS_TO]->(doc:Document)-[:REFERS_TO]->(s:Specification)
        OPTIONAL MATCH (c)-[:CONNECTED_TO]->(cc:Component)
        RETURN c as component,
               collect(DISTINCT m) as materials,
               collect(DISTINCT d) as dimensions,
               collect(DISTINCT s) as specifications,
               collect(DISTINCT cc) as connected_components
        """
        results = self.client.execute_query(query, {"id": component_id})
        if results:
            return results[0]
        return {}

    def get_document_graph(self, doc_id: str) -> Dict:
        """
        获取文档的完整知识图谱

        返回：
            {
                "nodes": [...],
                "relationships": [...],
            }
        """
        query = """
        MATCH (d:Document {id: $doc_id})
        OPTIONAL MATCH (d)-[r1]->(n1)
        OPTIONAL MATCH (n1)-[r2]->(n2)
        WITH d, collect(DISTINCT n1) + collect(DISTINCT n2) as nodes,
             collect(DISTINCT r1) + collect(DISTINCT r2) as rels
        RETURN d as document, nodes, rels
        """
        results = self.client.execute_query(query, {"doc_id": doc_id})
        if results:
            return results[0]
        return {"document": None, "nodes": [], "rels": []}

    def find_related_components(
        self,
        component_id: str,
        depth: int = 2
    ) -> List[Dict]:
        """
        查找关联构件（支持多层关系）

        参数：
            component_id: 起始构件 ID
            depth: 遍历深度
        """
        query = f"""
        MATCH (c:Component {{id: $id}})
        MATCH path = (c)-[:CONNECTED_TO*1..{depth}]-(related:Component)
        RETURN DISTINCT related
        """
        return self.client.execute_query(query, {"id": component_id})

    def search_by_specification(self, spec_code: str) -> List[Dict]:
        """根据规范编号搜索相关文档和构件"""
        query = """
        MATCH (s:Specification {code: $code})<-[:REFERS_TO]-(d:Document)
        OPTIONAL MATCH (d)<-[:BELONGS_TO]-(c:Component)
        RETURN d as document, collect(c) as components
        """
        return self.client.execute_query(query, {"code": spec_code})

    # =========================================
    # 批量操作
    # =========================================

    def batch_create_nodes(
        self,
        label: str,
        nodes_data: List[Dict]
    ) -> Dict:
        """
        批量创建节点

        参数：
            label: 节点标签
            nodes_data: 节点数据列表
        """
        query = f"""
        UNWIND $nodes as node
        CREATE (n:{label})
        SET n = node
        RETURN count(n) as created
        """
        return self.client.execute_write(query, {"nodes": nodes_data})

    def batch_create_relationships(
        self,
        relationships: List[Dict]
    ) -> Dict:
        """
        批量创建关系

        参数：
            relationships: 关系列表，每项包含：
                - from_id: 起始节点 ID
                - from_label: 起始节点标签
                - to_id: 目标节点 ID
                - to_label: 目标节点标签
                - rel_type: 关系类型
                - properties: 关系属性（可选）
        """
        query = """
        UNWIND $rels as rel
        MATCH (a {id: rel.from_id}), (b {id: rel.to_id})
        CALL apoc.create.relationship(a, rel.rel_type, rel.properties, b)
        YIELD rel as created
        RETURN count(created) as count
        """

        # 如果没有 APOC 插件，使用简单方式
        created_count = 0
        for rel in relationships:
            try:
                self.client.create_relationship(
                    {"label": rel["from_label"], "props": {"id": rel["from_id"]}},
                    {"label": rel["to_label"], "props": {"id": rel["to_id"]}},
                    rel["rel_type"],
                    rel.get("properties")
                )
                created_count += 1
            except Exception as e:
                logger.warning(f"创建关系失败: {e}")

        return {"relationships_created": created_count}

    # =========================================
    # 统计和维护
    # =========================================

    def get_graph_statistics(self, doc_id: str = None) -> Dict:
        """
        获取图谱统计信息

        参数：
            doc_id: 可选，限定文档范围
        """
        if doc_id:
            query = """
            MATCH (d:Document {id: $doc_id})
            OPTIONAL MATCH (d)<-[:BELONGS_TO]-(c:Component)
            OPTIONAL MATCH (d)<-[:BELONGS_TO]-(m:Material)
            OPTIONAL MATCH (d)-[:REFERS_TO]->(s:Specification)
            RETURN count(DISTINCT c) as components,
                   count(DISTINCT m) as materials,
                   count(DISTINCT s) as specifications
            """
            result = self.client.execute_query(query, {"doc_id": doc_id})
            if result:
                return {
                    "doc_id": doc_id,
                    **result[0]
                }
            return {}
        else:
            return self.client.get_statistics()

    def clear_document_graph(self, doc_id: str) -> Dict:
        """清除文档相关的所有图数据"""
        return self.delete_document_and_relations(doc_id)
