# -*- coding: utf-8 -*-
"""
转换器模块初始化文件

导入所有可用的转换器，确保它们能被插件管理器发现
"""

# 导入所有转换器
from .pdf_to_docx_converter import PDFToDocxConverter, PDF_TO_DOCX_METADATA
from .pdf_to_docx_ocr_converter import PDFToDocxOCRConverter, PDF_TO_DOCX_OCR_METADATA
from .pdf_to_ppt_converter import PDFToPPTConverter, PDF_TO_PPT_METADATA
from .word_to_ppt_converter import WordToPPTConverter, WORD_TO_PPT_METADATA

# 导出所有转换器和元数据
__all__ = [
    'PDFToDocxConverter',
    'PDF_TO_DOCX_METADATA',
    'PDFToDocxOCRConverter',
    'PDF_TO_DOCX_OCR_METADATA',
    'PDFToPPTConverter', 
    'PDF_TO_PPT_METADATA',
    'WordToPPTConverter',
    'WORD_TO_PPT_METADATA'
]