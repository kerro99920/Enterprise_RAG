"""
========================================
知识图谱 API 接口
========================================

📚 模块说明：
- 知识图谱查询和管理
- 节点和关系的 CRUD
- 图谱遍历和路径查询
- 统计和可视化数据

🎯 核心功能：
1. 节点查询（构件、材料、规范等）
2. 关系查询和遍历
3. 路径查找
4. 图谱统计
5. 可视化数据导出

========================================
"""

from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

from core.logger import logger

router = APIRouter()


# =========================================
# 枚举定义
# =========================================

class NodeType(str, Enum):
    """节点类型"""
    DOCUMENT = "Document"
    DRAWING = "Drawing"
    COMPONENT = "Component"
    MATERIAL = "Material"
    SPECIFICATION = "Specification"
    DIMENSION = "Dimension"
    LOCATION = "Location"
    ANNOTATION = "Annotation"


class RelationType(str, Enum):
    """关系类型"""
    CONTAINS = "CONTAINS"
    USES_MATERIAL = "USES_MATERIAL"
    REFERS_TO = "REFERS_TO"
    HAS_DIMENSION = "HAS_DIMENSION"
    LOCATED_AT = "LOCATED_AT"
    CONNECTED_TO = "CONNECTED_TO"
    BELONGS_TO = "BELONGS_TO"


class ComponentType(str, Enum):
    """构件类型"""
    BEAM = "beam"
    COLUMN = "column"
    SLAB = "slab"
    WALL = "wall"
    FOUNDATION = "foundation"
    STAIR = "stair"
    OTHER = "other"


# =========================================
# 请求/响应模型
# =========================================

class NodeInfo(BaseModel):
    """节点信息"""
    id: str = Field(..., description="节点ID")
    label: str = Field(..., description="节点标签")
    properties: Dict[str, Any] = Field(default={}, description="节点属性")


class RelationInfo(BaseModel):
    """关系信息"""
    id: str = Field(..., description="关系ID")
    from_node_id: str = Field(..., description="起始节点ID")
    to_node_id: str = Field(..., description="目标节点ID")
    rel_type: str = Field(..., description="关系类型")
    properties: Dict[str, Any] = Field(default={}, description="关系属性")


class GraphStatistics(BaseModel):
    """图谱统计"""
    total_nodes: int = Field(0, description="总节点数")
    total_relationships: int = Field(0, description="总关系数")
    node_labels: Dict[str, int] = Field(default={}, description="各类型节点数量")
    relationship_types: Dict[str, int] = Field(default={}, description="各类型关系数量")


class DocumentGraphResponse(BaseModel):
    """文档图谱响应"""
    success: bool = Field(True, description="是否成功")
    document_id: str = Field(..., description="文档ID")
    nodes: List[NodeInfo] = Field(default=[], description="节点列表")
    relationships: List[RelationInfo] = Field(default=[], description="关系列表")
    statistics: Dict[str, int] = Field(default={}, description="统计信息")


class ComponentDetailResponse(BaseModel):
    """构件详情响应"""
    success: bool = Field(True, description="是否成功")
    component: NodeInfo = Field(..., description="构件信息")
    materials: List[NodeInfo] = Field(default=[], description="使用的材料")
    dimensions: List[NodeInfo] = Field(default=[], description="尺寸信息")
    specifications: List[NodeInfo] = Field(default=[], description="相关规范")
    connected_components: List[NodeInfo] = Field(default=[], description="连接的构件")


class PathResult(BaseModel):
    """路径结果"""
    nodes: List[NodeInfo] = Field(..., description="路径上的节点")
    relationships: List[RelationInfo] = Field(..., description="路径上的关系")
    length: int = Field(..., description="路径长度")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索关键词")
    node_types: Optional[List[NodeType]] = Field(None, description="限定节点类型")
    limit: int = Field(20, ge=1, le=100, description="返回数量限制")


class CreateNodeRequest(BaseModel):
    """创建节点请求"""
    label: NodeType = Field(..., description="节点类型")
    properties: Dict[str, Any] = Field(..., description="节点属性")


class CreateRelationRequest(BaseModel):
    """创建关系请求"""
    from_node_id: str = Field(..., description="起始节点ID")
    to_node_id: str = Field(..., description="目标节点ID")
    rel_type: RelationType = Field(..., description="关系类型")
    properties: Optional[Dict[str, Any]] = Field(default={}, description="关系属性")


class VisualizationData(BaseModel):
    """可视化数据"""
    nodes: List[Dict] = Field(..., description="节点数据")
    edges: List[Dict] = Field(..., description="边数据")
    categories: List[Dict] = Field(default=[], description="节点分类")


# =========================================
# 辅助函数
# =========================================

def get_graph_repo():
    """获取图数据库 Repository"""
    try:
        from repository.graph_repo import GraphRepository
        return GraphRepository()
    except Exception as e:
        logger.error(f"获取 GraphRepository 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="图数据库服务不可用"
        )


# =========================================
# 图谱统计接口
# =========================================

@router.get(
    "/statistics",
    response_model=GraphStatistics,
    summary="图谱统计",
    description="获取知识图谱的整体统计信息"
)
async def get_graph_statistics():
    """
    获取图谱统计信息

    包括：
    - 总节点数
    - 总关系数
    - 各类型节点数量
    - 各类型关系数量
    """
    try:
        graph_repo = get_graph_repo()
        stats = graph_repo.get_graph_statistics()

        return GraphStatistics(
            total_nodes=stats.get("total_nodes", 0),
            total_relationships=stats.get("total_relationships", 0),
            node_labels=stats.get("node_labels", {}),
            relationship_types=stats.get("relationship_types", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图谱统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取图谱统计失败: {str(e)}"
        )


# =========================================
# 文档图谱接口
# =========================================

@router.get(
    "/document/{document_id}",
    response_model=DocumentGraphResponse,
    summary="文档图谱",
    description="获取指定文档的知识图谱"
)
async def get_document_graph(document_id: str):
    """
    获取文档的完整知识图谱

    返回文档下的所有节点和关系
    """
    try:
        graph_repo = get_graph_repo()
        graph_data = graph_repo.get_document_graph(document_id)

        # 转换节点数据
        nodes = []
        for node in graph_data.get("nodes", []):
            if node:
                nodes.append(NodeInfo(
                    id=node.get("id", ""),
                    label=node.get("label", "Unknown"),
                    properties=node.get("properties", {})
                ))

        # 转换关系数据
        relationships = []
        for rel in graph_data.get("rels", []):
            if rel:
                relationships.append(RelationInfo(
                    id=rel.get("id", ""),
                    from_node_id=rel.get("from_node_id", ""),
                    to_node_id=rel.get("to_node_id", ""),
                    rel_type=rel.get("type", ""),
                    properties=rel.get("properties", {})
                ))

        # 统计
        statistics = {
            "nodes": len(nodes),
            "relationships": len(relationships)
        }

        return DocumentGraphResponse(
            success=True,
            document_id=document_id,
            nodes=nodes,
            relationships=relationships,
            statistics=statistics
        )

    except Exception as e:
        logger.error(f"获取文档图谱失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档图谱失败: {str(e)}"
        )


@router.get(
    "/document/{document_id}/statistics",
    summary="文档图谱统计",
    description="获取文档图谱的统计信息"
)
async def get_document_statistics(document_id: str):
    """
    获取文档图谱的统计信息
    """
    try:
        graph_repo = get_graph_repo()
        stats = graph_repo.get_graph_statistics(document_id)

        return {
            "success": True,
            "document_id": document_id,
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"获取文档统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档统计失败: {str(e)}"
        )


# =========================================
# 构件查询接口
# =========================================

@router.get(
    "/components",
    summary="查询构件列表",
    description="查询构件节点列表"
)
async def list_components(
    component_type: Optional[ComponentType] = Query(None, description="构件类型"),
    document_id: Optional[str] = Query(None, description="文档ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    查询构件列表

    支持按类型和文档筛选
    """
    try:
        graph_repo = get_graph_repo()

        # 查询构件
        if component_type:
            components = graph_repo.find_components_by_type(
                component_type.value,
                doc_id=document_id,
                limit=page_size * page
            )
        else:
            # 查询所有构件
            from services.graph.neo4j_client import neo4j_client
            query = "MATCH (c:Component) "
            params = {}

            if document_id:
                query += "WHERE c.doc_id = $doc_id "
                params["doc_id"] = document_id

            query += "RETURN c LIMIT $limit"
            params["limit"] = page_size * page

            components = neo4j_client.execute_query(query, params)

        # 分页
        start = (page - 1) * page_size
        paginated = components[start:start + page_size]

        # 转换格式
        result = []
        for comp in paginated:
            node = comp.get("c", {})
            result.append({
                "id": node.get("id", ""),
                "code": node.get("code", ""),
                "type": node.get("type", ""),
                "properties": dict(node)
            })

        return {
            "success": True,
            "total": len(components),
            "page": page,
            "page_size": page_size,
            "components": result
        }

    except Exception as e:
        logger.error(f"查询构件失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询构件失败: {str(e)}"
        )


@router.get(
    "/component/{component_id}",
    response_model=ComponentDetailResponse,
    summary="构件详情",
    description="获取构件的详细信息及关联"
)
async def get_component_detail(component_id: str):
    """
    获取构件详情

    包括：
    - 构件基本信息
    - 使用的材料
    - 尺寸信息
    - 相关规范
    - 连接的其他构件
    """
    try:
        graph_repo = get_graph_repo()
        data = graph_repo.get_component_with_relations(component_id)

        if not data or not data.get("component"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"构件不存在: {component_id}"
            )

        # 转换数据
        component = data.get("component", {})
        component_info = NodeInfo(
            id=component.get("id", ""),
            label="Component",
            properties=dict(component)
        )

        materials = [
            NodeInfo(id=m.get("id", ""), label="Material", properties=dict(m))
            for m in data.get("materials", []) if m
        ]

        dimensions = [
            NodeInfo(id=d.get("id", ""), label="Dimension", properties=dict(d))
            for d in data.get("dimensions", []) if d
        ]

        specifications = [
            NodeInfo(id=s.get("id", ""), label="Specification", properties=dict(s))
            for s in data.get("specifications", []) if s
        ]

        connected = [
            NodeInfo(id=c.get("id", ""), label="Component", properties=dict(c))
            for c in data.get("connected_components", []) if c
        ]

        return ComponentDetailResponse(
            success=True,
            component=component_info,
            materials=materials,
            dimensions=dimensions,
            specifications=specifications,
            connected_components=connected
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取构件详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取构件详情失败: {str(e)}"
        )


@router.get(
    "/component/code/{code}",
    summary="按编号查询构件",
    description="根据构件编号查询构件"
)
async def get_component_by_code(
    code: str,
    document_id: Optional[str] = Query(None, description="文档ID")
):
    """
    根据构件编号查询

    例如：KL-1, KZ-2
    """
    try:
        graph_repo = get_graph_repo()
        component = graph_repo.find_component_by_code(code, doc_id=document_id)

        if not component:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"构件不存在: {code}"
            )

        return {
            "success": True,
            "component": {
                "id": component.get("id", ""),
                "code": component.get("code", ""),
                "type": component.get("type", ""),
                "properties": dict(component)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询构件失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询构件失败: {str(e)}"
        )


# =========================================
# 材料查询接口
# =========================================

@router.get(
    "/materials",
    summary="查询材料列表",
    description="查询材料节点列表"
)
async def list_materials(
    grade: Optional[str] = Query(None, description="材料等级，如 C30, HRB400"),
    document_id: Optional[str] = Query(None, description="文档ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    查询材料列表

    支持按等级筛选
    """
    try:
        graph_repo = get_graph_repo()

        if grade:
            materials = graph_repo.find_materials_by_grade(grade, limit=page_size * page)
        else:
            from services.graph.neo4j_client import neo4j_client
            query = "MATCH (m:Material) "
            params = {}

            if document_id:
                query += "WHERE m.doc_id = $doc_id "
                params["doc_id"] = document_id

            query += "RETURN m LIMIT $limit"
            params["limit"] = page_size * page

            materials = neo4j_client.execute_query(query, params)

        # 分页
        start = (page - 1) * page_size
        paginated = materials[start:start + page_size]

        # 转换格式
        result = []
        for mat in paginated:
            node = mat.get("m", mat.get("n", {}))
            result.append({
                "id": node.get("id", ""),
                "type": node.get("type", ""),
                "grade": node.get("grade", ""),
                "properties": dict(node)
            })

        return {
            "success": True,
            "total": len(materials),
            "page": page,
            "page_size": page_size,
            "materials": result
        }

    except Exception as e:
        logger.error(f"查询材料失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询材料失败: {str(e)}"
        )


# =========================================
# 规范查询接口
# =========================================

@router.get(
    "/specifications",
    summary="查询规范列表",
    description="查询规范节点列表"
)
async def list_specifications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    查询规范列表
    """
    try:
        from services.graph.neo4j_client import neo4j_client

        query = "MATCH (s:Specification) RETURN s LIMIT $limit"
        params = {"limit": page_size * page}

        specifications = neo4j_client.execute_query(query, params)

        # 分页
        start = (page - 1) * page_size
        paginated = specifications[start:start + page_size]

        # 转换格式
        result = []
        for spec in paginated:
            node = spec.get("s", {})
            result.append({
                "id": node.get("id", ""),
                "code": node.get("code", ""),
                "name": node.get("name", ""),
                "properties": dict(node)
            })

        return {
            "success": True,
            "total": len(specifications),
            "page": page,
            "page_size": page_size,
            "specifications": result
        }

    except Exception as e:
        logger.error(f"查询规范失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询规范失败: {str(e)}"
        )


@router.get(
    "/specification/{spec_code}/documents",
    summary="规范关联文档",
    description="查询引用指定规范的所有文档"
)
async def get_documents_by_specification(spec_code: str):
    """
    查询引用指定规范的文档和构件
    """
    try:
        graph_repo = get_graph_repo()
        results = graph_repo.search_by_specification(spec_code)

        documents = []
        for result in results:
            doc = result.get("document", {})
            components = result.get("components", [])

            documents.append({
                "document": {
                    "id": doc.get("id", ""),
                    "name": doc.get("name", ""),
                    "properties": dict(doc) if doc else {}
                },
                "components_count": len([c for c in components if c])
            })

        return {
            "success": True,
            "spec_code": spec_code,
            "documents": documents,
            "total": len(documents)
        }

    except Exception as e:
        logger.error(f"查询规范关联失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )


# =========================================
# 关系查询接口
# =========================================

@router.get(
    "/relations",
    summary="查询关系",
    description="查询知识图谱中的关系"
)
async def list_relations(
    from_label: Optional[str] = Query(None, description="起始节点类型"),
    to_label: Optional[str] = Query(None, description="目标节点类型"),
    rel_type: Optional[RelationType] = Query(None, description="关系类型"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制")
):
    """
    查询关系列表
    """
    try:
        from services.graph.neo4j_client import neo4j_client

        relations = neo4j_client.find_relationships(
            from_label=from_label,
            to_label=to_label,
            rel_type=rel_type.value if rel_type else None,
            limit=limit
        )

        result = []
        for rel in relations:
            result.append({
                "from_node": dict(rel.get("a", {})) if rel.get("a") else None,
                "relation": dict(rel.get("r", {})) if rel.get("r") else None,
                "to_node": dict(rel.get("b", {})) if rel.get("b") else None
            })

        return {
            "success": True,
            "total": len(result),
            "relations": result
        }

    except Exception as e:
        logger.error(f"查询关系失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询关系失败: {str(e)}"
        )


@router.get(
    "/connected/{node_id}",
    summary="关联构件查询",
    description="查询与指定节点关联的构件"
)
async def get_connected_nodes(
    node_id: str,
    depth: int = Query(2, ge=1, le=5, description="遍历深度")
):
    """
    查询关联构件

    支持多层遍历
    """
    try:
        graph_repo = get_graph_repo()
        related = graph_repo.find_related_components(node_id, depth=depth)

        result = []
        for item in related:
            node = item.get("related", {})
            if node:
                result.append({
                    "id": node.get("id", ""),
                    "code": node.get("code", ""),
                    "type": node.get("type", ""),
                    "properties": dict(node)
                })

        return {
            "success": True,
            "source_node_id": node_id,
            "depth": depth,
            "connected_count": len(result),
            "connected_nodes": result
        }

    except Exception as e:
        logger.error(f"查询关联节点失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询关联节点失败: {str(e)}"
        )


# =========================================
# 搜索接口
# =========================================

@router.post(
    "/search",
    summary="图谱搜索",
    description="在知识图谱中搜索节点"
)
async def search_graph(request: SearchRequest):
    """
    图谱搜索

    支持按关键词搜索节点
    """
    try:
        from services.graph.neo4j_client import neo4j_client

        # 构建搜索查询
        query_parts = []
        params = {"keyword": f".*{request.query}.*", "limit": request.limit}

        if request.node_types:
            for node_type in request.node_types:
                query_parts.append(f"""
                    MATCH (n:{node_type.value})
                    WHERE any(key in keys(n) WHERE toString(n[key]) =~ $keyword)
                    RETURN n, labels(n) as labels
                """)
            query = " UNION ".join(query_parts) + " LIMIT $limit"
        else:
            query = """
                MATCH (n)
                WHERE any(key in keys(n) WHERE toString(n[key]) =~ $keyword)
                RETURN n, labels(n) as labels
                LIMIT $limit
            """

        results = neo4j_client.execute_query(query, params)

        nodes = []
        for item in results:
            node = item.get("n", {})
            labels = item.get("labels", [])
            nodes.append({
                "id": node.get("id", ""),
                "label": labels[0] if labels else "Unknown",
                "properties": dict(node)
            })

        return {
            "success": True,
            "query": request.query,
            "total": len(nodes),
            "nodes": nodes
        }

    except Exception as e:
        logger.error(f"图谱搜索失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )


# =========================================
# 可视化数据接口
# =========================================

@router.get(
    "/visualization/{document_id}",
    response_model=VisualizationData,
    summary="可视化数据",
    description="获取用于图形可视化的数据"
)
async def get_visualization_data(
    document_id: str,
    max_nodes: int = Query(100, ge=10, le=500, description="最大节点数")
):
    """
    获取可视化数据

    返回适用于 ECharts/D3.js 等图形库的数据格式
    """
    try:
        graph_repo = get_graph_repo()
        graph_data = graph_repo.get_document_graph(document_id)

        # 节点分类
        categories = [
            {"name": "Document", "itemStyle": {"color": "#5470c6"}},
            {"name": "Component", "itemStyle": {"color": "#91cc75"}},
            {"name": "Material", "itemStyle": {"color": "#fac858"}},
            {"name": "Specification", "itemStyle": {"color": "#ee6666"}},
            {"name": "Dimension", "itemStyle": {"color": "#73c0de"}},
        ]

        label_to_category = {
            "Document": 0,
            "Component": 1,
            "Material": 2,
            "Specification": 3,
            "Dimension": 4,
        }

        # 转换节点
        nodes = []
        node_ids = set()

        # 添加文档节点
        doc = graph_data.get("document")
        if doc:
            nodes.append({
                "id": doc.get("id", document_id),
                "name": doc.get("name", document_id),
                "category": 0,
                "symbolSize": 40,
                "value": doc.get("id", "")
            })
            node_ids.add(doc.get("id", document_id))

        # 添加其他节点
        for node in graph_data.get("nodes", [])[:max_nodes]:
            if node and node.get("id") not in node_ids:
                label = list(node.labels)[0] if hasattr(node, 'labels') else "Unknown"
                category = label_to_category.get(label, 1)

                nodes.append({
                    "id": node.get("id", ""),
                    "name": node.get("code", node.get("name", node.get("id", "")[:8])),
                    "category": category,
                    "symbolSize": 20,
                    "value": str(node.get("id", ""))
                })
                node_ids.add(node.get("id", ""))

        # 转换边
        edges = []
        for rel in graph_data.get("rels", []):
            if rel:
                source = rel.get("from_node_id", "")
                target = rel.get("to_node_id", "")

                if source in node_ids and target in node_ids:
                    edges.append({
                        "source": source,
                        "target": target,
                        "value": rel.get("type", "")
                    })

        return VisualizationData(
            nodes=nodes,
            edges=edges,
            categories=categories
        )

    except Exception as e:
        logger.error(f"获取可视化数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可视化数据失败: {str(e)}"
        )


# =========================================
# 管理接口
# =========================================

@router.delete(
    "/document/{document_id}",
    summary="删除文档图谱",
    description="删除指定文档的所有图谱数据"
)
async def delete_document_graph(document_id: str):
    """
    删除文档图谱

    会删除文档节点及其所有关联的子节点和关系
    """
    try:
        graph_repo = get_graph_repo()
        result = graph_repo.clear_document_graph(document_id)

        return {
            "success": True,
            "message": "文档图谱删除成功",
            "document_id": document_id,
            "deleted": result
        }

    except Exception as e:
        logger.error(f"删除文档图谱失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除失败: {str(e)}"
        )


@router.post(
    "/node",
    summary="创建节点",
    description="手动创建知识图谱节点"
)
async def create_node(request: CreateNodeRequest):
    """
    创建节点

    用于手动添加知识图谱节点
    """
    try:
        from services.graph.neo4j_client import neo4j_client
        import uuid

        # 添加 ID
        properties = request.properties.copy()
        if "id" not in properties:
            properties["id"] = f"{request.label.value.lower()}_{uuid.uuid4().hex[:8]}"

        result = neo4j_client.create_node([request.label.value], properties)

        return {
            "success": True,
            "message": "节点创建成功",
            "node_id": properties["id"],
            "label": request.label.value,
            "result": result
        }

    except Exception as e:
        logger.error(f"创建节点失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建节点失败: {str(e)}"
        )


@router.post(
    "/relation",
    summary="创建关系",
    description="手动创建知识图谱关系"
)
async def create_relation(request: CreateRelationRequest):
    """
    创建关系

    用于手动添加节点间关系
    """
    try:
        from services.graph.neo4j_client import neo4j_client

        result = neo4j_client.create_relationship(
            from_node_match={"label": "", "props": {"id": request.from_node_id}},
            to_node_match={"label": "", "props": {"id": request.to_node_id}},
            rel_type=request.rel_type.value,
            properties=request.properties
        )

        return {
            "success": True,
            "message": "关系创建成功",
            "relation": {
                "from": request.from_node_id,
                "to": request.to_node_id,
                "type": request.rel_type.value
            },
            "result": result
        }

    except Exception as e:
        logger.error(f"创建关系失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建关系失败: {str(e)}"
        )


# =========================================
# 健康检查
# =========================================

@router.get(
    "/health",
    summary="图数据库健康检查",
    description="检查 Neo4j 连接状态"
)
async def check_graph_health():
    """
    检查图数据库连接
    """
    try:
        from services.graph.neo4j_client import neo4j_client

        is_connected = neo4j_client.ping()

        return {
            "success": True,
            "connected": is_connected,
            "database": "Neo4j",
            "status": "healthy" if is_connected else "disconnected"
        }

    except Exception as e:
        return {
            "success": False,
            "connected": False,
            "database": "Neo4j",
            "status": "error",
            "error": str(e)
        }


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 获取图谱统计
curl "http://localhost:8000/api/v1/graph/statistics"

# 2. 获取文档图谱
curl "http://localhost:8000/api/v1/graph/document/drawing_xxx"

# 3. 查询构件列表
curl "http://localhost:8000/api/v1/graph/components?component_type=beam"

# 4. 获取构件详情
curl "http://localhost:8000/api/v1/graph/component/comp_xxx"

# 5. 按编号查询构件
curl "http://localhost:8000/api/v1/graph/component/code/KL-1"

# 6. 查询材料列表
curl "http://localhost:8000/api/v1/graph/materials?grade=C30"

# 7. 查询规范关联
curl "http://localhost:8000/api/v1/graph/specification/GB50010-2010/documents"

# 8. 查询关系
curl "http://localhost:8000/api/v1/graph/relations?rel_type=USES_MATERIAL"

# 9. 图谱搜索
curl -X POST "http://localhost:8000/api/v1/graph/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "KL-1", "node_types": ["Component"]}'

# 10. 获取可视化数据
curl "http://localhost:8000/api/v1/graph/visualization/drawing_xxx"

# 11. 健康检查
curl "http://localhost:8000/api/v1/graph/health"
"""
