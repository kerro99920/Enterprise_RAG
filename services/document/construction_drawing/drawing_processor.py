"""
========================================
施工图处理编排器
========================================

📚 模块说明：
- 编排施工图的完整处理流程
- 管理解析、提取、存储等步骤
- 支持异步处理和进度回调

🎯 处理流程：
1. PDF 解析 -> 提取文本、表格
2. 实体提取 -> 识别构件、材料、规范
3. 关系提取 -> 建立实体间关系
4. 图谱存储 -> 同步到 Neo4j
5. 状态更新 -> 记录处理结果

========================================
"""
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from pathlib import Path
import uuid
import asyncio

from services.document.construction_drawing.drawing_parser import ConstructionDrawingParser
from services.document.construction_drawing.entity_extractor import EntityExtractor
from services.document.construction_drawing.relation_extractor import RelationExtractor
from repository.graph_repo import GraphRepository
from core.logger import logger


class ProcessingResult:
    """处理结果"""

    def __init__(self):
        self.success: bool = False
        self.document_id: str = ""
        self.file_path: str = ""
        self.drawing_info: Dict = {}
        self.entities_count: int = 0
        self.relations_count: int = 0
        self.neo4j_synced: bool = False
        self.error_message: Optional[str] = None
        self.processing_time_ms: int = 0
        self.steps: List[Dict] = []

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "document_id": self.document_id,
            "file_path": self.file_path,
            "drawing_info": self.drawing_info,
            "entities_count": self.entities_count,
            "relations_count": self.relations_count,
            "neo4j_synced": self.neo4j_synced,
            "error_message": self.error_message,
            "processing_time_ms": self.processing_time_ms,
            "steps": self.steps,
        }


class DrawingProcessor:
    """
    施工图处理编排器

    🔧 功能：
    - 编排完整的施工图处理流程
    - 支持进度回调
    - 错误处理和恢复
    - 结果存储
    """

    def __init__(
        self,
        enable_ocr: bool = True,
        use_llm: bool = True,
        sync_to_neo4j: bool = True
    ):
        """
        初始化处理器

        参数：
            enable_ocr: 是否启用 OCR
            use_llm: 是否使用 LLM 增强
            sync_to_neo4j: 是否同步到 Neo4j
        """
        self.enable_ocr = enable_ocr
        self.use_llm = use_llm
        self.sync_to_neo4j = sync_to_neo4j

        # 初始化组件
        self.parser = ConstructionDrawingParser(enable_ocr=enable_ocr)
        self.entity_extractor = EntityExtractor(use_llm=use_llm)
        self.relation_extractor = RelationExtractor()
        self.graph_repo = GraphRepository() if sync_to_neo4j else None

    async def process(
        self,
        file_path: str,
        document_id: str = None,
        project_id: str = None,
        progress_callback: Callable[[float, str], None] = None
    ) -> ProcessingResult:
        """
        处理施工图

        参数：
            file_path: PDF 文件路径
            document_id: 文档 ID（可选，自动生成）
            project_id: 项目 ID（可选）
            progress_callback: 进度回调函数

        返回：
            ProcessingResult: 处理结果
        """
        result = ProcessingResult()
        result.file_path = file_path
        result.document_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"

        start_time = datetime.now()

        try:
            # 步骤 1: PDF 解析
            self._update_progress(progress_callback, 10, "解析 PDF 文件...")
            parsed_drawing = await self._step_parse(file_path, result)

            # 步骤 2: 实体提取
            self._update_progress(progress_callback, 30, "提取实体...")
            entities = await self._step_extract_entities(
                parsed_drawing, result.document_id, result
            )

            # 步骤 3: 关系提取
            self._update_progress(progress_callback, 50, "提取关系...")
            relations = await self._step_extract_relations(
                entities, parsed_drawing, result.document_id, result
            )

            # 步骤 4: 同步到 Neo4j
            if self.sync_to_neo4j and self.graph_repo:
                self._update_progress(progress_callback, 70, "同步到知识图谱...")
                await self._step_sync_to_neo4j(
                    result.document_id,
                    parsed_drawing,
                    entities,
                    relations,
                    project_id,
                    result
                )

            # 完成
            self._update_progress(progress_callback, 100, "处理完成")
            result.success = True

        except Exception as e:
            logger.error(f"施工图处理失败: {str(e)}")
            result.success = False
            result.error_message = str(e)
            result.steps.append({
                "step": "error",
                "status": "failed",
                "message": str(e),
            })

        # 计算处理时间
        end_time = datetime.now()
        result.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return result

    async def _step_parse(
        self,
        file_path: str,
        result: ProcessingResult
    ) -> Dict[str, Any]:
        """步骤1: PDF 解析"""
        step_start = datetime.now()

        try:
            # 同步调用解析器（可以改为异步）
            parsed = self.parser.parse(file_path)

            # 提取图纸信息
            drawing_info = parsed.get("drawing_info")
            if drawing_info:
                result.drawing_info = {
                    "drawing_number": drawing_info.drawing_number,
                    "drawing_name": drawing_info.drawing_name,
                    "scale": drawing_info.scale,
                    "project_name": drawing_info.project_name,
                }

            step_duration = int((datetime.now() - step_start).total_seconds() * 1000)
            result.steps.append({
                "step": "parse",
                "status": "success",
                "duration_ms": step_duration,
                "total_pages": parsed.get("total_pages", 0),
                "is_scanned": parsed.get("is_scanned", False),
            })

            return parsed

        except Exception as e:
            result.steps.append({
                "step": "parse",
                "status": "failed",
                "error": str(e),
            })
            raise

    async def _step_extract_entities(
        self,
        parsed_drawing: Dict[str, Any],
        document_id: str,
        result: ProcessingResult
    ) -> Dict[str, List]:
        """步骤2: 实体提取"""
        step_start = datetime.now()

        try:
            entities = self.entity_extractor.extract_entities(
                parsed_drawing, document_id
            )

            # 从表格中提取实体
            tables = parsed_drawing.get("tables", [])
            if tables:
                table_entities = self.entity_extractor.extract_from_tables(
                    tables, document_id
                )
                # 合并实体
                for key in entities:
                    if key in table_entities:
                        entities[key].extend(table_entities[key])

            # 统计
            total_entities = sum(len(v) for v in entities.values())
            result.entities_count = total_entities

            step_duration = int((datetime.now() - step_start).total_seconds() * 1000)
            result.steps.append({
                "step": "extract_entities",
                "status": "success",
                "duration_ms": step_duration,
                "components": len(entities.get("components", [])),
                "materials": len(entities.get("materials", [])),
                "dimensions": len(entities.get("dimensions", [])),
                "specifications": len(entities.get("specifications", [])),
            })

            return entities

        except Exception as e:
            result.steps.append({
                "step": "extract_entities",
                "status": "failed",
                "error": str(e),
            })
            raise

    async def _step_extract_relations(
        self,
        entities: Dict[str, List],
        parsed_drawing: Dict[str, Any],
        document_id: str,
        result: ProcessingResult
    ) -> List:
        """步骤3: 关系提取"""
        step_start = datetime.now()

        try:
            relations = self.relation_extractor.extract_relations(
                entities, parsed_drawing, document_id
            )

            # 提取构件连接关系
            connected_relations = self.relation_extractor.extract_connected_relations(
                entities.get("components", []),
                parsed_drawing
            )
            relations.extend(connected_relations)

            result.relations_count = len(relations)

            step_duration = int((datetime.now() - step_start).total_seconds() * 1000)
            result.steps.append({
                "step": "extract_relations",
                "status": "success",
                "duration_ms": step_duration,
                "relations_count": len(relations),
            })

            return relations

        except Exception as e:
            result.steps.append({
                "step": "extract_relations",
                "status": "failed",
                "error": str(e),
            })
            raise

    async def _step_sync_to_neo4j(
        self,
        document_id: str,
        parsed_drawing: Dict[str, Any],
        entities: Dict[str, List],
        relations: List,
        project_id: str,
        result: ProcessingResult
    ):
        """步骤4: 同步到 Neo4j"""
        step_start = datetime.now()

        try:
            # 创建文档节点
            drawing_info = parsed_drawing.get("drawing_info")
            doc_name = Path(parsed_drawing.get("file_path", "")).name

            self.graph_repo.create_document_node(
                doc_id=document_id,
                name=doc_name,
                doc_type="construction_drawing",
                project_id=project_id,
                properties={
                    "drawing_number": drawing_info.drawing_number if drawing_info else "",
                    "scale": drawing_info.scale if drawing_info else "",
                    "total_pages": parsed_drawing.get("total_pages", 0),
                }
            )

            # 创建实体节点
            nodes_created = 0

            # 构件
            for comp in entities.get("components", []):
                self.graph_repo.create_component(
                    component_id=comp.id,
                    code=comp.code,
                    component_type=comp.properties.get("component_type", "other"),
                    doc_id=document_id,
                    properties=comp.properties
                )
                nodes_created += 1

            # 材料
            for mat in entities.get("materials", []):
                self.graph_repo.create_material(
                    material_id=mat.id,
                    material_type=mat.properties.get("material_type", "other"),
                    grade=mat.properties.get("grade", ""),
                    doc_id=document_id,
                    properties=mat.properties
                )
                nodes_created += 1

            # 规范
            for spec in entities.get("specifications", []):
                self.graph_repo.create_specification(
                    spec_id=spec.id,
                    code=spec.spec_code,
                    properties=spec.properties
                )
                nodes_created += 1

            # 创建关系
            relations_created = 0
            for rel in relations:
                try:
                    # 根据关系类型创建
                    rel_type = rel.rel_type.value if hasattr(rel.rel_type, 'value') else rel.rel_type

                    if rel_type == "USES_MATERIAL":
                        self.graph_repo.create_uses_material_relation(
                            rel.from_node_id,
                            rel.to_node_id,
                            rel.properties
                        )
                    elif rel_type == "HAS_DIMENSION":
                        self.graph_repo.create_has_dimension_relation(
                            rel.from_node_id,
                            rel.to_node_id
                        )
                    elif rel_type == "REFERS_TO":
                        self.graph_repo.create_refers_to_relation(
                            document_id,
                            rel.to_node_id
                        )
                    elif rel_type == "CONNECTED_TO":
                        self.graph_repo.create_connected_to_relation(
                            rel.from_node_id,
                            rel.to_node_id,
                            rel.properties
                        )

                    relations_created += 1
                except Exception as e:
                    logger.warning(f"创建关系失败: {e}")

            result.neo4j_synced = True

            step_duration = int((datetime.now() - step_start).total_seconds() * 1000)
            result.steps.append({
                "step": "sync_neo4j",
                "status": "success",
                "duration_ms": step_duration,
                "nodes_created": nodes_created,
                "relations_created": relations_created,
            })

        except Exception as e:
            result.neo4j_synced = False
            result.steps.append({
                "step": "sync_neo4j",
                "status": "failed",
                "error": str(e),
            })
            # Neo4j 同步失败不阻断整体流程
            logger.warning(f"Neo4j 同步失败: {e}")

    def _update_progress(
        self,
        callback: Optional[Callable],
        progress: float,
        message: str
    ):
        """更新进度"""
        if callback:
            try:
                callback(progress, message)
            except Exception as e:
                logger.warning(f"进度回调失败: {e}")

    def process_sync(
        self,
        file_path: str,
        document_id: str = None,
        project_id: str = None
    ) -> ProcessingResult:
        """
        同步处理（非异步）

        参数同 process()
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.process(file_path, document_id, project_id)
            )
        finally:
            loop.close()
