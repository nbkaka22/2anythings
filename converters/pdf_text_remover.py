import fitz  # PyMuPDF
import logging
from typing import List, Tuple, Optional
import tempfile
import os
from PIL import Image
import io
from converters.pdf_to_docx_ocr_converter import PDFToDocxOCRConverter
from converters.ocr_parameter_adapter import OCRParameterAdapter
from converters.cache_manager import cache_manager

logger = logging.getLogger(__name__)

class PDFTextRemover:
    """PDF文本删除器
    
    使用OCR识别PDF中的文本，然后删除指定的文本内容，保持原文件结构
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._temp_files = []
        self.ocr_converter = PDFToDocxOCRConverter()
        
    def remove_text_from_pdf(self, input_path: str, output_path: str, target_text: str, 
                            case_sensitive: bool = False, whole_word: bool = False) -> bool:
        """从PDF中删除指定文本
        
        Args:
            input_path: 输入PDF文件路径
            output_path: 输出PDF文件路径
            target_text: 要删除的目标文本
            case_sensitive: 是否区分大小写
            whole_word: 是否只匹配完整单词
            
        Returns:
            bool: 是否成功删除文本
        """
        try:
            logger.info(f"开始从PDF中删除文本: {target_text}")
            
            # 打开PDF文档
            pdf_doc = fitz.open(input_path)
            total_pages = pdf_doc.page_count
            
            # 创建新的PDF文档
            new_doc = fitz.open()
            
            removed_count = 0
            
            for page_num in range(total_pages):
                logger.info(f"处理第 {page_num + 1}/{total_pages} 页")
                
                page = pdf_doc[page_num]
                
                # 方法1：尝试直接文本删除（适用于可选择文本的PDF）
                text_removed = self._remove_text_direct(page, target_text, case_sensitive, whole_word)
                
                if text_removed > 0:
                    removed_count += text_removed
                    logger.info(f"第 {page_num + 1} 页直接删除了 {text_removed} 处文本")
                else:
                    # 方法2：OCR识别后删除（适用于扫描版PDF）
                    ocr_removed = self._remove_text_with_ocr(page, target_text, case_sensitive, whole_word)
                    if ocr_removed > 0:
                        removed_count += ocr_removed
                        logger.info(f"第 {page_num + 1} 页通过OCR删除了 {ocr_removed} 处文本")
                
                # 将处理后的页面添加到新文档
                new_doc.insert_pdf(pdf_doc, from_page=page_num, to_page=page_num)
            
            # 保存新文档
            new_doc.save(output_path)
            new_doc.close()
            pdf_doc.close()
            
            logger.info(f"文本删除完成，共删除 {removed_count} 处文本，保存到: {output_path}")
            return removed_count > 0
            
        except Exception as e:
            logger.error(f"删除文本失败: {e}")
            return False
        finally:
            self.cleanup()
    
    def _remove_text_direct(self, page, target_text: str, case_sensitive: bool, whole_word: bool) -> int:
        """直接从PDF页面删除文本（适用于可选择文本）"""
        try:
            removed_count = 0
            
            # 获取页面文本块
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            
                            # 检查是否包含目标文本
                            if self._text_matches(text, target_text, case_sensitive, whole_word):
                                # 获取文本位置
                                bbox = span["bbox"]
                                
                                # 用白色矩形覆盖文本
                                rect = fitz.Rect(bbox)
                                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                
                                removed_count += 1
                                logger.debug(f"删除文本: {text} at {bbox}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"直接删除文本失败: {e}")
            return 0
    
    def _remove_text_with_ocr(self, page, target_text: str, case_sensitive: bool, whole_word: bool) -> int:
        """使用OCR识别后删除文本（适用于扫描版PDF）"""
        try:
            removed_count = 0
            
            # 将页面转换为图像
            mat = fitz.Matrix(2.0, 2.0)  # 高分辨率
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # 保存临时图像文件
            temp_img_path = tempfile.mktemp(suffix='.png')
            self._temp_files.append(temp_img_path)
            
            with open(temp_img_path, 'wb') as f:
                f.write(img_data)
            
            # 使用OCR识别文本和位置
            text_results = self._ocr_extract_with_positions(temp_img_path)
            
            # 查找匹配的文本并删除
            for text_info in text_results:
                text = text_info['text']
                bbox = text_info['bbox']
                
                if self._text_matches(text, target_text, case_sensitive, whole_word):
                    # 将OCR坐标转换为PDF坐标
                    pdf_rect = self._convert_ocr_to_pdf_coords(bbox, pix.width, pix.height, page.rect)
                    
                    # 用白色矩形覆盖文本
                    page.draw_rect(pdf_rect, color=(1, 1, 1), fill=(1, 1, 1))
                    
                    removed_count += 1
                    logger.debug(f"OCR删除文本: {text} at {bbox}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"OCR删除文本失败: {e}")
            return 0
    
    def _ocr_extract_with_positions(self, image_path: str) -> List[dict]:
        """使用OCR提取文本和位置信息"""
        try:
            results = []
            
            # 使用PaddleOCR
            if self.ocr_converter._paddle_ocr:
                ocr_results = self.ocr_converter._paddle_ocr.ocr(image_path, cls=True)
                
                if ocr_results and ocr_results[0]:
                    for line in ocr_results[0]:
                        if line:
                            bbox = line[0]  # 边界框坐标
                            text_info = line[1]  # (文本, 置信度)
                            text = text_info[0]
                            confidence = text_info[1]
                            
                            if confidence > 0.5:  # 置信度阈值
                                results.append({
                                    'text': text,
                                    'bbox': bbox,
                                    'confidence': confidence
                                })
            
            # 如果PaddleOCR失败，尝试EasyOCR
            elif self.ocr_converter._easy_ocr_reader:
                ocr_results = self.ocr_converter._easy_ocr_reader.readtext(image_path)
                
                for result in ocr_results:
                    bbox = result[0]
                    text = result[1]
                    confidence = result[2]
                    
                    if confidence > 0.5:
                        results.append({
                            'text': text,
                            'bbox': bbox,
                            'confidence': confidence
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"OCR文本提取失败: {e}")
            return []
    
    def _text_matches(self, text: str, target: str, case_sensitive: bool, whole_word: bool) -> bool:
        """检查文本是否匹配目标文本"""
        if not case_sensitive:
            text = text.lower()
            target = target.lower()
        
        if whole_word:
            import re
            pattern = r'\b' + re.escape(target) + r'\b'
            return bool(re.search(pattern, text))
        else:
            return target in text
    
    def _convert_ocr_to_pdf_coords(self, ocr_bbox, img_width: int, img_height: int, page_rect) -> fitz.Rect:
        """将OCR坐标转换为PDF坐标"""
        try:
            # OCR边界框通常是四个点的坐标
            if isinstance(ocr_bbox[0], (list, tuple)):
                # PaddleOCR格式：[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                x_coords = [point[0] for point in ocr_bbox]
                y_coords = [point[1] for point in ocr_bbox]
                
                x1, x2 = min(x_coords), max(x_coords)
                y1, y2 = min(y_coords), max(y_coords)
            else:
                # EasyOCR格式：(x1, y1, x2, y2)
                x1, y1, x2, y2 = ocr_bbox
            
            # 转换为PDF坐标系
            pdf_x1 = (x1 / img_width) * page_rect.width + page_rect.x0
            pdf_y1 = (y1 / img_height) * page_rect.height + page_rect.y0
            pdf_x2 = (x2 / img_width) * page_rect.width + page_rect.x0
            pdf_y2 = (y2 / img_height) * page_rect.height + page_rect.y0
            
            return fitz.Rect(pdf_x1, pdf_y1, pdf_x2, pdf_y2)
            
        except Exception as e:
            logger.error(f"坐标转换失败: {e}")
            return fitz.Rect(0, 0, 0, 0)
    
    def find_text_in_pdf(self, input_path: str, target_text: str, 
                         case_sensitive: bool = False) -> List[dict]:
        """在PDF中查找指定文本的位置
        
        Returns:
            List[dict]: 包含页码和位置信息的列表
        """
        try:
            results = []
            pdf_doc = fitz.open(input_path)
            
            for page_num in range(pdf_doc.page_count):
                page = pdf_doc[page_num]
                
                # 直接文本搜索
                search_text = target_text if case_sensitive else target_text.lower()
                text_instances = page.search_for(search_text)
                
                for rect in text_instances:
                    results.append({
                        'page': page_num + 1,
                        'bbox': list(rect),
                        'method': 'direct'
                    })
                
                # 如果直接搜索没有结果，尝试OCR
                if not text_instances:
                    ocr_results = self._find_text_with_ocr(page, target_text, case_sensitive)
                    results.extend(ocr_results)
            
            pdf_doc.close()
            return results
            
        except Exception as e:
            logger.error(f"查找文本失败: {e}")
            return []
    
    def _find_text_with_ocr(self, page, target_text: str, case_sensitive: bool) -> List[dict]:
        """使用OCR在页面中查找文本"""
        try:
            results = []
            
            # 转换页面为图像
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            temp_img_path = tempfile.mktemp(suffix='.png')
            self._temp_files.append(temp_img_path)
            
            with open(temp_img_path, 'wb') as f:
                f.write(img_data)
            
            # OCR识别
            text_results = self._ocr_extract_with_positions(temp_img_path)
            
            for text_info in text_results:
                text = text_info['text']
                bbox = text_info['bbox']
                
                if self._text_matches(text, target_text, case_sensitive, False):
                    pdf_rect = self._convert_ocr_to_pdf_coords(bbox, pix.width, pix.height, page.rect)
                    
                    results.append({
                        'page': page.number + 1,
                        'bbox': list(pdf_rect),
                        'method': 'ocr',
                        'text': text,
                        'confidence': text_info['confidence']
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"OCR查找文本失败: {e}")
            return []
    
    def cleanup(self):
        """清理临时文件"""
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {temp_file}, {e}")
        self._temp_files.clear()
    
    def __del__(self):
        """析构函数，确保清理临时文件"""
        self.cleanup()