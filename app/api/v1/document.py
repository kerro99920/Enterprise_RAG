"""
========================================
文档管理API接口
========================================

📚 模块说明：
- 文档上传和管理
- 文档检索和查询
- 批量处理

🎯 核心功能：
1. 文档上传
2. 文档列表
3. 文档删除
4. 批量导入

========================================
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import os

from loguru import logger
from core.config import settings

router = APIRouter()


# =========================================
# 请求/响应模型
# =========================================

class DocumentInfo(BaseModel):
    """文档信息"""
    doc_id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    file_size: int = Field(..., description="文件大小(字节)")
    status: str = Field(..., description="处理状态")
    uploaded_at: str = Field(..., description="上传时间")
    processed_at: Optional[str] = Field(None, description="处理完成时间")
    metadata: Optional[Dict] = Field(default={}, description="元数据")


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    success: bool = Field(True, description="是否成功")
    total: int = Field(..., description="文档总数")
    documents: List[DocumentInfo] = Field(..., description="文档列表")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool = Field(True, description="是否成功")
    doc_id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    message: str = Field(..., description="提示信息")


class ProcessStatus(BaseModel):
    """处理状态"""
    doc_id: str = Field(..., description="文档ID")
    status: str = Field(..., description="状态")
    progress: float = Field(..., description="进度(0-100)")
    message: str = Field(..., description="状态消息")


# =========================================
# 文档上传接口
# =========================================

@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="上传文档",
    description="上传单个文档到知识库"
)
async def upload_document(
        file: UploadFile = File(..., description="上传的文件"),
        category: Optional[str] = Query(None, description="文档分类")
):
    """
    上传文档接口

    支持的格式：
    - PDF (.pdf)
    - Word (.docx, .doc)
    - 文本 (.txt, .md)

    处理流程：
    1. 验证文件格式
    2. 保存文件
    3. 异步处理（解析、向量化、存储）
    4. 返回文档ID
    """
    try:
        logger.info(f"收到文件上传: {file.filename}")

        # 验证文件格式
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md'}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件格式: {file_ext}。支持: {allowed_extensions}"
            )

        # 验证文件大小（限制50MB）
        max_size = 50 * 1024 * 1024  # 50MB
        file_size = 0

        # 生成文档ID
        import uuid
        doc_id = str(uuid.uuid4())

        # 保存文件
        upload_dir = settings.DATA_DIR / "raw_docs"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / f"{doc_id}_{file.filename}"

        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):  # 8KB chunks
                file_size += len(chunk)
                if file_size > max_size:
                    os.remove(file_path)  # 删除已保存的部分
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"文件过大，限制{max_size // 1024 // 1024}MB"
                    )
                f.write(chunk)

        logger.info(
            f"文件保存成功: {file.filename} | "
            f"大小: {file_size / 1024:.2f}KB | "
            f"doc_id: {doc_id}"
        )

        # 这里应该触发异步处理任务
        # 例如：使用Celery、Redis Queue等
        # await process_document_async(doc_id, file_path, category)

        return UploadResponse(
            success=True,
            doc_id=doc_id,
            filename=file.filename,
            message="文档上传成功，正在处理中"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )


@router.post(
    "/upload/batch",
    summary="批量上传",
    description="批量上传多个文档"
)
async def upload_documents_batch(
        files: List[UploadFile] = File(..., description="上传的文件列表")
):
    """
    批量上传接口

    返回每个文件的上传结果
    """
    results = []

    for file in files:
        try:
            result = await upload_document(file)
            results.append({
                "filename": file.filename,
                "success": True,
                "doc_id": result.doc_id
            })
        except Exception as e:
            logger.error(f"文件上传失败: {file.filename} | {e}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    success_count = sum(1 for r in results if r["success"])

    return {
        "success": True,
        "total": len(files),
        "success_count": success_count,
        "failed_count": len(files) - success_count,
        "results": results
    }


# =========================================
# 文档查询接口
# =========================================

@router.get(
    "/list",
    response_model=DocumentListResponse,
    summary="文档列表",
    description="获取文档列表"
)
async def list_documents(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量"),
        category: Optional[str] = Query(None, description="文档分类"),
        status: Optional[str] = Query(None, description="处理状态")
):
    """
    文档列表接口

    支持分页和筛选
    """
    try:
        # 这里应该从数据库查询
        # documents = await db.get_documents(
        #     page=page,
        #     page_size=page_size,
        #     category=category,
        #     status=status
        # )

        # 临时示例数据
        documents = [
            DocumentInfo(
                doc_id="doc_001",
                filename="GB50009-2012.pdf",
                file_type="pdf",
                file_size=1024000,
                status="completed",
                uploaded_at="2024-01-10T10:00:00",
                processed_at="2024-01-10T10:05:00",
                metadata={"category": "规范标准"}
            )
        ]

        return DocumentListResponse(
            success=True,
            total=len(documents),
            documents=documents,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文档列表失败"
        )


@router.get(
    "/{doc_id}",
    response_model=DocumentInfo,
    summary="文档详情",
    description="获取单个文档的详细信息"
)
async def get_document(doc_id: str):
    """
    文档详情接口
    """
    try:
        # 这里应该从数据库查询
        # document = await db.get_document(doc_id)

        # if not document:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail="文档不存在"
        #     )

        # 临时示例
        document = DocumentInfo(
            doc_id=doc_id,
            filename="example.pdf",
            file_type="pdf",
            file_size=1024000,
            status="completed",
            uploaded_at="2024-01-10T10:00:00",
            processed_at="2024-01-10T10:05:00"
        )

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文档详情失败"
        )


@router.get(
    "/{doc_id}/status",
    response_model=ProcessStatus,
    summary="处理状态",
    description="查询文档处理状态"
)
async def get_document_status(doc_id: str):
    """
    查询文档处理状态

    状态：
    - pending: 等待处理
    - processing: 处理中
    - completed: 已完成
    - failed: 处理失败
    """
    try:
        # 这里应该查询实际的处理状态
        # status_info = await get_process_status(doc_id)

        # 临时示例
        return ProcessStatus(
            doc_id=doc_id,
            status="completed",
            progress=100.0,
            message="文档处理完成"
        )

    except Exception as e:
        logger.error(f"查询处理状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查询处理状态失败"
        )


# =========================================
# 文档删除接口
# =========================================

@router.delete(
    "/{doc_id}",
    summary="删除文档",
    description="从知识库中删除文档"
)
async def delete_document(doc_id: str):
    """
    删除文档接口

    会删除：
    - 原始文件
    - 向量数据
    - 数据库记录
    """
    try:
        logger.info(f"删除文档: {doc_id}")

        # 这里应该执行删除操作
        # 1. 从向量库删除
        # await vector_db.delete(doc_id)

        # 2. 从数据库删除
        # await db.delete_document(doc_id)

        # 3. 删除原始文件
        # await delete_file(doc_id)

        return {
            "success": True,
            "message": "文档删除成功",
            "doc_id": doc_id
        }

    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除文档失败"
        )


@router.post(
    "/delete/batch",
    summary="批量删除",
    description="批量删除多个文档"
)
async def delete_documents_batch(
        doc_ids: List[str] = Field(..., description="文档ID列表")
):
    """批量删除文档"""
    results = []

    for doc_id in doc_ids:
        try:
            await delete_document(doc_id)
            results.append({
                "doc_id": doc_id,
                "success": True
            })
        except Exception as e:
            results.append({
                "doc_id": doc_id,
                "success": False,
                "error": str(e)
            })

    success_count = sum(1 for r in results if r["success"])

    return {
        "success": True,
        "total": len(doc_ids),
        "success_count": success_count,
        "failed_count": len(doc_ids) - success_count,
        "results": results
    }


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 上传文档
curl -X POST "http://localhost:8000/api/v1/documents/upload" \\
  -F "file=@GB50009-2012.pdf" \\
  -F "category=规范标准"


# 2. 查询文档列表
curl "http://localhost:8000/api/v1/documents/list?page=1&page_size=20"


# 3. 查询文档详情
curl "http://localhost:8000/api/v1/documents/doc_001"


# 4. 查询处理状态
curl "http://localhost:8000/api/v1/documents/doc_001/status"


# 5. 删除文档
curl -X DELETE "http://localhost:8000/api/v1/documents/doc_001"


# 6. Python客户端上传
import requests

with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/documents/upload',
        files={'file': f},
        data={'category': '技术文档'}
    )

result = response.json()
print(f"文档ID: {result['doc_id']}")
"""