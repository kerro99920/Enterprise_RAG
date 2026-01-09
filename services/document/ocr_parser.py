"""
========================================
OCR 光学字符识别解析器
========================================

📚 模块说明：
- 使用PaddleOCR识别图片和扫描PDF中的文字
- 支持中英文混合识别
- 提取表格结构

🎯 核心功能：
1. 图片文字识别
2. PDF扫描件文字识别
3. 表格结构识别
4. 置信度评估

========================================
"""
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from PIL import Image
import pdf2image

from core.logger import logger, log_execution
from core.config import settings


class OCRParser:
    """
    OCR解析器

    🎯 职责：
    - 识别图片中的文字
    - 识别扫描PDF中的文字
    - 提取表格结构
    - 评估识别质量

    💡 使用PaddleOCR：
    - 开源免费
    - 支持中文
    - 识别准确率高
    """

    def __init__(self):
        """
        初始化OCR解析器

        ⚠️ 首次使用会下载模型，需要一些时间
        """
        self.ocr = None
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self._init_ocr()

    def _init_ocr(self):
        """初始化PaddleOCR"""
        try:
            if not settings.OCR_ENABLED:
                logger.warning("OCR功能未启用")
                return

            from paddleocr import PaddleOCR

            # 初始化OCR
            # use_angle_cls=True: 支持旋转文字识别
            # lang: 语言选择（ch表示中文，en表示英文）
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=settings.OCR_LANGUAGE,
                show_log=False  # 不显示详细日志
            )

            logger.info(f"OCR初始化成功，语言: {settings.OCR_LANGUAGE}")

        except Exception as e:
            logger.error(f"OCR初始化失败: {str(e)}")
            logger.warning("OCR功能将不可用")
            self.ocr = None

    @log_execution("OCR识别图片")
    def parse_image(self, image_path: str) -> Dict[str, Any]:
        """
        识别图片中的文字

        参数：
            image_path: 图片路径

        返回：
            Dict: OCR结果
            {
                "text": str,                # 识别的全部文本
                "lines": List[Dict],        # 每行文本的详细信息
                "confidence": float,        # 平均置信度
                "char_count": int,          # 字符数
            }
        """
        try:
            if not self.ocr:
                raise RuntimeError("OCR未初始化")

            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片不存在: {image_path}")

            logger.info(f"开始OCR识别: {image_path}")

            # 执行OCR
            result = self.ocr.ocr(image_path, cls=True)

            if not result or not result[0]:
                logger.warning("OCR未识别到文字")
                return {
                    "text": "",
                    "lines": [],
                    "confidence": 0.0,
                    "char_count": 0
                }

            # 解析OCR结果
            lines_data = []
            all_text = []
            confidences = []

            for line in result[0]:
                # line格式: [bbox, (text, confidence)]
                bbox = line[0]  # 边界框坐标
                text = line[1][0]  # 识别的文本
                confidence = line[1][1]  # 置信度

                lines_data.append({
                    "text": text,
                    "confidence": confidence,
                    "bbox": bbox
                })

                all_text.append(text)
                confidences.append(confidence)

            # 合并文本
            full_text = "\n".join(all_text)

            # 计算平均置信度
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            result_data = {
                "text": full_text,
                "lines": lines_data,
                "confidence": avg_confidence,
                "char_count": len(full_text),
                "line_count": len(lines_data)
            }

            logger.info(
                f"OCR识别完成: {image_path} | "
                f"行数: {len(lines_data)} | "
                f"字符数: {len(full_text)} | "
                f"置信度: {avg_confidence:.2%}"
            )

            return result_data

        except Exception as e:
            logger.error(f"OCR识别失败: {image_path} | 错误: {str(e)}")
            raise

    @log_execution("OCR识别PDF")
    def parse_pdf(
            self,
            pdf_path: str,
            dpi: int = 200
    ) -> Dict[str, Any]:
        """
        识别PDF扫描件中的文字

        参数：
            pdf_path: PDF文件路径
            dpi: 转换为图片的分辨率（越高越清晰但越慢）

        返回：
            Dict: OCR结果
            {
                "text": str,                # 全文本
                "pages": List[Dict],        # 每页的OCR结果
                "total_pages": int,         # 总页数
                "avg_confidence": float,    # 平均置信度
            }

        💡 处理流程：
        1. 将PDF转换为图片
        2. 对每页图片进行OCR
        3. 合并所有结果
        """
        try:
            if not self.ocr:
                raise RuntimeError("OCR未初始化")

            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF不存在: {pdf_path}")

            logger.info(f"开始OCR识别PDF: {pdf_path}")

            # 将PDF转换为图片
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=dpi,
                fmt='jpeg'
            )

            logger.info(f"PDF转换为图片完成，共 {len(images)} 页")

            # 对每页进行OCR
            pages_data = []
            all_text = []
            all_confidences = []

            for page_num, image in enumerate(images, start=1):
                logger.info(f"识别第 {page_num}/{len(images)} 页...")

                # 将PIL Image转换为numpy数组
                img_array = np.array(image)

                # 执行OCR
                result = self.ocr.ocr(img_array, cls=True)

                if not result or not result[0]:
                    # 该页没有识别到文字
                    pages_data.append({
                        "page_num": page_num,
                        "text": "",
                        "confidence": 0.0,
                        "lines": []
                    })
                    continue

                # 解析该页的OCR结果
                page_lines = []
                page_text = []
                page_confidences = []

                for line in result[0]:
                    text = line[1][0]
                    confidence = line[1][1]

                    page_lines.append({
                        "text": text,
                        "confidence": confidence
                    })

                    page_text.append(text)
                    page_confidences.append(confidence)

                # 该页的文本和置信度
                page_full_text = "\n".join(page_text)
                page_avg_confidence = (
                    sum(page_confidences) / len(page_confidences)
                    if page_confidences else 0.0
                )

                pages_data.append({
                    "page_num": page_num,
                    "text": page_full_text,
                    "confidence": page_avg_confidence,
                    "lines": page_lines,
                    "char_count": len(page_full_text)
                })

                all_text.append(page_full_text)
                all_confidences.extend(page_confidences)

            # 合并所有页面
            full_text = "\n\n".join(all_text)
            avg_confidence = (
                sum(all_confidences) / len(all_confidences)
                if all_confidences else 0.0
            )

            result_data = {
                "text": full_text,
                "pages": pages_data,
                "total_pages": len(images),
                "avg_confidence": avg_confidence,
                "char_count": len(full_text)
            }

            logger.info(
                f"PDF OCR识别完成: {pdf_path} | "
                f"页数: {len(images)} | "
                f"字符数: {len(full_text)} | "
                f"平均置信度: {avg_confidence:.2%}"
            )

            return result_data

        except Exception as e:
            logger.error(f"PDF OCR识别失败: {pdf_path} | 错误: {str(e)}")
            raise

    def is_good_quality(self, confidence: float, threshold: float = 0.8) -> bool:
        """
        判断OCR识别质量是否良好

        参数：
            confidence: 置信度
            threshold: 阈值（默认0.8）

        返回：
            bool: True表示质量良好
        """
        return confidence >= threshold

    def clean_ocr_text(self, text: str) -> str:
        """
        清理OCR识别的文本

        参数：
            text: OCR识别的原始文本

        返回：
            str: 清理后的文本

        💡 清理操作：
        - 去除多余空格
        - 修正常见的OCR错误
        - 统一标点符号
        """
        if not text:
            return ""

        try:
            # 去除首尾空格
            text = text.strip()

            # 替换多个连续空格为一个
            import re
            text = re.sub(r'\s+', ' ', text)

            # 修正常见的OCR错误（可根据实际情况扩展）
            # 例如：数字0和字母O的混淆
            # text = text.replace('O', '0')  # 慎用，需要根据上下文

            return text

        except Exception as e:
            logger.warning(f"清理OCR文本失败: {str(e)}")
            return text


# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 识别图片
from services.document.ocr_parser import OCRParser

parser = OCRParser()

# 识别单张图片
result = parser.parse_image("scan_page_1.jpg")

print(f"识别文本:\n{result['text']}")
print(f"置信度: {result['confidence']:.2%}")
print(f"字符数: {result['char_count']}")

# 检查质量
if parser.is_good_quality(result['confidence']):
    print("识别质量良好")
else:
    print("识别质量较差，可能需要人工校对")


# 2. 识别扫描PDF
result = parser.parse_pdf("scanned_document.pdf", dpi=300)

print(f"总页数: {result['total_pages']}")
print(f"平均置信度: {result['avg_confidence']:.2%}")

# 查看每页的识别结果
for page in result['pages']:
    print(f"\n第{page['page_num']}页:")
    print(f"  字符数: {page['char_count']}")
    print(f"  置信度: {page['confidence']:.2%}")
    print(f"  文本预览: {page['text'][:100]}...")


# 3. 清理OCR文本
cleaned_text = parser.clean_ocr_text(result['text'])
print(cleaned_text)
"""