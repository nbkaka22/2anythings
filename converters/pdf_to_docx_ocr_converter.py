# -*- coding: utf-8 -*-
"""
PDF转DOCX OCR转换器

使用PyMuPDF + EasyOCR + pdfplumber组合实现扫描版PDF的文本和图片提取
"""

import os
import fitz  # PyMuPDF
import easyocr
import pdfplumber
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image
import io
import tempfile
import logging
from typing import Dict, Any, List, Tuple
import numpy as np

# 导入基类
from converters.converter_interface import ConverterInterface, ConverterMetadata

logger = logging.getLogger('pdf_converter')

class PDFToDocxOCRConverter(ConverterInterface):
    """PDF转DOCX OCR转换器
    
    使用PyMuPDF + EasyOCR + pdfplumber组合处理扫描版PDF
    """
    
    def __init__(self):
        self._temp_files = []
        self._ocr_reader = None
        
    def _get_ocr_reader(self):
        """获取OCR识别器实例（延迟初始化）"""
        if self._ocr_reader is None:
            try:
                # 初始化EasyOCR，支持中英文
                self._ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
                logger.info("EasyOCR初始化成功")
            except Exception as e:
                logger.error(f"EasyOCR初始化失败: {e}")
                raise
        return self._ocr_reader
    
    @property
    def name(self) -> str:
        return "pdf_to_docx_ocr"
    
    @property
    def description(self) -> str:
        return "使用OCR技术将扫描版PDF转换为Word文档，支持文本识别和图片提取"
    
    @property
    def supported_input_formats(self) -> List[str]:
        return ["pdf"]
    
    @property
    def supported_output_formats(self) -> List[str]:
        return ["docx"]
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def validate_input(self, input_path: str) -> bool:
        """验证PDF文件是否有效"""
        try:
            if not os.path.exists(input_path):
                logger.error(f"文件不存在: {input_path}")
                return False
            
            if not input_path.lower().endswith('.pdf'):
                logger.error(f"文件格式不正确，需要PDF文件: {input_path}")
                return False
            
            # 尝试打开PDF文件
            doc = fitz.open(input_path)
            if doc.page_count == 0:
                logger.error(f"PDF文件为空: {input_path}")
                doc.close()
                return False
            
            doc.close()
            return True
            
        except Exception as e:
            logger.error(f"PDF文件验证失败: {e}")
            return False
    
    def _detect_pdf_type(self, pdf_path: str) -> str:
        """检测PDF类型：文本型或扫描型"""
        try:
            # 使用pdfplumber检测文本内容
            with pdfplumber.open(pdf_path) as pdf:
                text_pages = 0
                total_pages = len(pdf.pages)
                
                # 检查前几页是否有文本
                check_pages = min(3, total_pages)
                for i in range(check_pages):
                    page = pdf.pages[i]
                    text = page.extract_text()
                    if text and text.strip():
                        text_pages += 1
                
                # 如果超过一半的检查页面有文本，认为是文本型PDF
                if text_pages >= check_pages * 0.5:
                    return "text"
                else:
                    return "scanned"
                    
        except Exception as e:
            logger.warning(f"PDF类型检测失败: {e}，默认为扫描型")
            return "scanned"
    
    def _extract_images_from_page(self, pdf_doc, page_num: int) -> List[Tuple[Image.Image, Dict]]:
        """从PDF页面提取图片"""
        images = []
        try:
            page = pdf_doc[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = pdf_doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # 转换为PIL图像
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    
                    # 获取图像在页面中的位置信息
                    image_info = {
                        'index': img_index,
                        'ext': image_ext,
                        'width': base_image["width"],
                        'height': base_image["height"]
                    }
                    
                    images.append((pil_image, image_info))
                    
                except Exception as e:
                    logger.warning(f"提取第{page_num+1}页第{img_index+1}个图像失败: {e}")
                    
        except Exception as e:
            logger.error(f"提取第{page_num+1}页图像失败: {e}")
            
        return images
    
    def _convert_page_to_image(self, pdf_doc, page_num: int, dpi: int = 300) -> Image.Image:
        """将PDF页面转换为高分辨率图像"""
        try:
            page = pdf_doc[page_num]
            # 设置缩放比例以获得指定DPI
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            # 渲染页面为图像
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # 转换为PIL图像
            pil_image = Image.open(io.BytesIO(img_data))
            return pil_image
            
        except Exception as e:
            logger.error(f"页面转图像失败: {e}")
            raise
    
    def _ocr_image(self, image: Image.Image) -> List[Dict]:
        """对图像进行OCR识别"""
        try:
            # 转换PIL图像为numpy数组
            img_array = np.array(image)
            
            # 使用EasyOCR进行文字识别
            ocr_reader = self._get_ocr_reader()
            results = ocr_reader.readtext(img_array)
            
            # 处理OCR结果
            ocr_data = []
            for (bbox, text, confidence) in results:
                if confidence > 0.5:  # 只保留置信度较高的结果
                    ocr_data.append({
                        'bbox': bbox,
                        'text': text,
                        'confidence': confidence
                    })
            
            return ocr_data
            
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return []
    
    def _analyze_layout(self, ocr_data: List[Dict], image_width: int, image_height: int) -> List[Dict]:
        """分析文本布局，重构段落结构"""
        if not ocr_data:
            return []
        
        # 按Y坐标排序（从上到下）
        sorted_data = sorted(ocr_data, key=lambda x: min([point[1] for point in x['bbox']]))
        
        # 分组为行
        lines = []
        current_line = []
        current_y = None
        y_threshold = image_height * 0.02  # Y坐标阈值
        
        for item in sorted_data:
            bbox = item['bbox']
            y_center = sum([point[1] for point in bbox]) / 4
            
            if current_y is None or abs(y_center - current_y) <= y_threshold:
                current_line.append(item)
                current_y = y_center if current_y is None else (current_y + y_center) / 2
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [item]
                current_y = y_center
        
        if current_line:
            lines.append(current_line)
        
        # 每行内按X坐标排序（从左到右）
        for line in lines:
            line.sort(key=lambda x: min([point[0] for point in x['bbox']]))
        
        # 合并为段落
        paragraphs = []
        for line in lines:
            line_text = ' '.join([item['text'] for item in line])
            if line_text.strip():
                paragraphs.append({
                    'text': line_text.strip(),
                    'y_position': min([point[1] for point in line[0]['bbox']])
                })
        
        return paragraphs
    
    def convert(self, input_path: str, output_path: str, **kwargs) -> bool:
        """执行PDF到DOCX的OCR转换"""
        try:
            logger.info(f"开始OCR转换: {input_path} -> {output_path}")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 检测PDF类型
            pdf_type = self._detect_pdf_type(input_path)
            logger.info(f"PDF类型: {pdf_type}")
            
            # 打开PDF文档
            pdf_doc = fitz.open(input_path)
            total_pages = pdf_doc.page_count
            
            # 创建Word文档
            word_doc = Document()
            
            # 处理每一页
            for page_num in range(total_pages):
                logger.info(f"处理第{page_num + 1}/{total_pages}页")
                
                if page_num > 0:
                    word_doc.add_page_break()
                
                # 添加页面标题
                title_para = word_doc.add_paragraph(f"第{page_num + 1}页")
                title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                title_run = title_para.runs[0]
                title_run.font.size = Pt(14)
                title_run.bold = True
                
                if pdf_type == "scanned":
                    # 扫描版PDF：使用OCR处理
                    try:
                        # 将页面转换为图像
                        page_image = self._convert_page_to_image(pdf_doc, page_num)
                        
                        # OCR识别
                        ocr_data = self._ocr_image(page_image)
                        
                        if ocr_data:
                            # 分析布局并重构段落
                            paragraphs = self._analyze_layout(ocr_data, page_image.width, page_image.height)
                            
                            # 添加识别的文本
                            for para_data in paragraphs:
                                para = word_doc.add_paragraph(para_data['text'])
                                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        else:
                            word_doc.add_paragraph("[未识别到文本内容]")
                        
                        # 提取并添加图片
                        images = self._extract_images_from_page(pdf_doc, page_num)
                        for img, img_info in images:
                            try:
                                # 保存图片到临时文件
                                temp_img_path = tempfile.mktemp(suffix=f".{img_info['ext']}")
                                self._temp_files.append(temp_img_path)
                                img.save(temp_img_path)
                                
                                # 添加到Word文档
                                word_doc.add_paragraph()  # 空行
                                para = word_doc.add_paragraph()
                                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                run = para.runs[0] if para.runs else para.add_run()
                                
                                # 计算合适的图片尺寸
                                max_width = Inches(6)
                                if img.width > img.height:
                                    width = max_width
                                    height = max_width * img.height / img.width
                                else:
                                    height = max_width
                                    width = max_width * img.width / img.height
                                
                                run.add_picture(temp_img_path, width=width, height=height)
                                
                            except Exception as e:
                                logger.warning(f"添加图片失败: {e}")
                                word_doc.add_paragraph(f"[图片添加失败: {e}]")
                    
                    except Exception as e:
                        logger.error(f"OCR处理第{page_num + 1}页失败: {e}")
                        word_doc.add_paragraph(f"[OCR处理失败: {e}]")
                
                else:
                    # 文本型PDF：直接提取文本
                    try:
                        page = pdf_doc[page_num]
                        text = page.get_text()
                        
                        if text.strip():
                            # 按段落分割文本
                            paragraphs = text.split('\n\n')
                            for paragraph in paragraphs:
                                if paragraph.strip():
                                    word_doc.add_paragraph(paragraph.strip())
                        else:
                            word_doc.add_paragraph("[未检测到文本内容]")
                            
                        # 提取图片
                        images = self._extract_images_from_page(pdf_doc, page_num)
                        for img, img_info in images:
                            try:
                                temp_img_path = tempfile.mktemp(suffix=f".{img_info['ext']}")
                                self._temp_files.append(temp_img_path)
                                img.save(temp_img_path)
                                
                                word_doc.add_paragraph()
                                para = word_doc.add_paragraph()
                                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                run = para.runs[0] if para.runs else para.add_run()
                                
                                max_width = Inches(6)
                                if img.width > img.height:
                                    width = max_width
                                    height = max_width * img.height / img.width
                                else:
                                    height = max_width
                                    width = max_width * img.width / img.height
                                
                                run.add_picture(temp_img_path, width=width, height=height)
                                
                            except Exception as e:
                                logger.warning(f"添加图片失败: {e}")
                    
                    except Exception as e:
                        logger.error(f"文本提取第{page_num + 1}页失败: {e}")
                        word_doc.add_paragraph(f"[文本提取失败: {e}]")
            
            pdf_doc.close()
            
            # 保存Word文档
            word_doc.save(output_path)
            
            # 验证输出文件
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"OCR转换成功: {output_path}")
                return True
            else:
                logger.error("转换完成但输出文件无效")
                return False
                
        except Exception as e:
            logger.error(f"OCR转换失败: {e}")
            return False
    
    def get_default_options(self) -> Dict[str, Any]:
        """获取默认转换选项"""
        return {
            'dpi': 300,
            'confidence_threshold': 0.5,
            'extract_images': True,
            'preserve_layout': True
        }
    
    def cleanup(self):
        """清理临时文件"""
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {temp_file}, {e}")
        
        self._temp_files.clear()

# 转换器元数据
PDF_TO_DOCX_OCR_METADATA = ConverterMetadata(
    name="pdf_to_docx_ocr",
    description="使用OCR技术将扫描版PDF转换为Word文档，支持文本识别和图片提取",
    version="1.0.0",
    author="PDF Converter Team",
    supported_input_formats=["pdf"],
    supported_output_formats=["docx"],
    dependencies=["PyMuPDF", "EasyOCR", "pdfplumber", "python-docx", "Pillow"],
    priority=5
)