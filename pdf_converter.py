import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import fitz  # PyMuPDF
from PIL import Image
import docx
from docx import Document
from pdf2docx import parse
import io
import time
import tempfile
import re
from pdf_to_ppt_converter import PDFToPPTConverterV2
from word_to_ppt_converter import WordToPPTConverter
from utils import get_resource_path
# OCR 功能已移除

class PDFConverter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PDF格式转换工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设置应用图标
        try:
            from PIL import Image, ImageTk
            
            # 尝试多个可能的图标路径
            icon_paths = [
                get_resource_path("icon.ico"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"),
                "icon.ico"
            ]
            
            icon_set = False
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    print(f"找到图标文件: {icon_path}")
                    try:
                        # 方法1: 使用iconbitmap
                        self.root.iconbitmap(icon_path)
                        print(f"使用iconbitmap设置图标成功: {icon_path}")
                        
                        # 方法2: 使用PIL加载图标并设置为PhotoImage
                        try:
                            icon_image = Image.open(icon_path)
                            # 调整图标大小为32x32
                            icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                            icon_photo = ImageTk.PhotoImage(icon_image)
                            self.root.iconphoto(True, icon_photo)
                            # 保存引用防止被垃圾回收
                            self.icon_photo = icon_photo
                            print("使用PIL方法设置图标成功")
                        except Exception as pil_error:
                            print(f"PIL方法设置图标失败: {pil_error}")
                        
                        icon_set = True
                        break
                    except Exception as icon_error:
                        print(f"设置图标失败 {icon_path}: {icon_error}")
                        continue
            
            if not icon_set:
                print("未找到可用的图标文件")
                
        except Exception as e:
            print(f"设置图标时出错: {e}")
        
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="选择PDF文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(file_frame, text="浏览文件", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览文件夹", command=self.browse_folder).grid(row=0, column=3, padx=5, pady=5)
        
        # 转换选项区域
        options_frame = ttk.LabelFrame(main_frame, text="转换选项", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        # 转换模式选择
        ttk.Label(options_frame, text="转换模式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.mode_var = tk.StringVar(value="document")
        ttk.Radiobutton(options_frame, text="文档模式", variable=self.mode_var, value="document").grid(row=0, column=1, padx=5, pady=5)
        ttk.Radiobutton(options_frame, text="图片模式", variable=self.mode_var, value="image").grid(row=0, column=2, padx=5, pady=5)
        
        # 输出格式选择
        ttk.Label(options_frame, text="输出格式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.format_var = tk.StringVar(value="docx")
        self.document_formats_frame = ttk.Frame(options_frame)
        self.document_formats_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=5)
        
        self.image_formats_frame = ttk.Frame(options_frame)
        self.image_formats_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=5)
        self.image_formats_frame.grid_remove()  # 默认隐藏
        
        # 文档格式选项
        ttk.Radiobutton(self.document_formats_frame, text="Word (DOCX)", variable=self.format_var, value="docx").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.document_formats_frame, text="PowerPoint (PPTX)", variable=self.format_var, value="pptx").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.document_formats_frame, text="PPT via Word (PPTX)", variable=self.format_var, value="pptx_via_word").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.document_formats_frame, text="文本 (TXT)", variable=self.format_var, value="txt").pack(side=tk.LEFT, padx=5)
        
        # 图片格式选项
        ttk.Radiobutton(self.image_formats_frame, text="PNG", variable=self.format_var, value="png").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.image_formats_frame, text="JPG", variable=self.format_var, value="jpg").pack(side=tk.LEFT, padx=5)
        
        # 绑定模式变更事件
        self.mode_var.trace_add("write", self.update_format_options)
        self.format_var.trace_add("write", self.update_format_options)
        

        # 输出目录选择
        ttk.Label(options_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.output_dir_var = tk.StringVar()
        ttk.Entry(options_frame, textvariable=self.output_dir_var, width=50).grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        
        ttk.Button(options_frame, text="浏览", command=self.browse_output_dir).grid(row=2, column=3, padx=5, pady=5)
        
        # PPT转换选项（仅文档模式下的PPTX格式）
        self.ppt_options_frame = ttk.Frame(options_frame)
        self.ppt_options_frame.grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=5)
        self.ppt_options_frame.grid_remove()  # 默认隐藏
        
        self.ppt_mode_var = tk.StringVar(value="image")  # 保留变量以兼容现有代码
        
        # DPI设置（图片转换固定使用200 DPI以保证质量）
        self.dpi_var = tk.StringVar(value="200")  # 保留变量以兼容现有代码，固定使用200 DPI
        
        # 转换按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="开始转换", command=self.start_conversion, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="转换进度", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # 用于跟踪是否上一条日志是进度信息
        self.last_log_was_progress = False
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(anchor=tk.W, pady=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # 设置样式
        self.setup_styles()
        
    def setup_styles(self):
        style = ttk.Style()
        
        # 尝试设置主题
        try:
            style.theme_use("clam")
        except:
            pass
        
        # 创建强调按钮样式
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        
    def update_format_options(self, *args):
        mode = self.mode_var.get()
        output_format = self.format_var.get()
        
        if mode == "document":
            self.image_formats_frame.grid_remove()
            self.document_formats_frame.grid()
            
            # 显示或隐藏PPT转换说明
            if output_format == "pptx":
                self.ppt_options_frame.grid()
            else:
                self.ppt_options_frame.grid_remove()
                
            if not output_format or output_format in ["png", "jpg"]:
                self.format_var.set("docx")
        else:  # image mode
            self.document_formats_frame.grid_remove()
            self.image_formats_frame.grid()
            self.ppt_options_frame.grid_remove()
            
            if not output_format or output_format in ["docx", "pptx", "txt"]:
                self.format_var.set("png")
    
    def browse_file(self):
        filetypes = [("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        file_path = filedialog.askopenfilename(filetypes=filetypes, title="选择PDF文件")
        
        if file_path:
            self.file_path_var.set(file_path)
            # 默认设置输出目录为文件所在目录
            if not self.output_dir_var.get():
                self.output_dir_var.set(os.path.dirname(file_path))
    
    def browse_folder(self):
        folder_path = filedialog.askdirectory(title="选择包含PDF文件的文件夹")
        
        if folder_path:
            self.file_path_var.set(folder_path)
            # 默认设置输出目录为选择的文件夹
            if not self.output_dir_var.get():
                self.output_dir_var.set(folder_path)
    
    def browse_output_dir(self):
        output_dir = filedialog.askdirectory(title="选择输出目录")
        
        if output_dir:
            self.output_dir_var.set(output_dir)
    
    def log(self, message, update_last_line=False):
        """记录日志信息
        Args:
            message: 日志消息
            update_last_line: 是否更新最后一行（用于进度显示）
        """
        if update_last_line:
            # 只有当上一条日志也是进度信息时才删除上一行
            if self.last_log_was_progress:
                try:
                    # 删除最后一行
                    self.log_text.delete("end-2l", "end-1l")
                except:
                    pass  # 如果删除失败就忽略
            self.log_text.insert(tk.END, f"{message}\n")
            self.last_log_was_progress = True
        else:
            self.log_text.insert(tk.END, f"{message}\n")
            self.last_log_was_progress = False
        self.log_text.see(tk.END)
        self.root.update_idletasks()  # 立即更新UI
    
    def log_progress(self, current, total, message=""):
        """显示进度信息（同行更新）"""
        progress_msg = f"当前处理进度: {current}/{total}"
        if message:
            progress_msg += f" - {message}"
        self.log(progress_msg, update_last_line=True)
    
    def log_step(self, step_name, details=""):
        """显示处理步骤"""
        step_msg = f"📋 {step_name}"
        if details:
            step_msg += f": {details}"
        self.log(step_msg)
    
    def log_error(self, error_msg, full_error=None):
        """显示错误信息"""
        self.log(f"❌ 错误: {error_msg}")
        if full_error:
            self.log(f"详细错误信息: {str(full_error)}")
    
    def log_success(self, message):
        """显示成功信息"""
        self.log(f"✅ {message}")
    
    def log_fallback(self, message):
        """显示备选方案信息"""
        self.log(f"🔄 备选方案: {message}")
    
    def start_conversion(self):
        # 获取输入路径
        input_path = self.file_path_var.get()
        if not input_path:
            messagebox.showerror("错误", "请选择PDF文件或文件夹")
            return
        
        # 获取输出目录
        output_dir = self.output_dir_var.get()
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录: {str(e)}")
                return
        
        # 获取转换选项
        mode = self.mode_var.get()
        output_format = self.format_var.get()
        dpi = self.dpi_var.get() if mode == "image" else None
        
        # 在新线程中执行转换，避免UI冻结
        threading.Thread(target=self.conversion_thread, args=(input_path, output_dir, mode, output_format, dpi), daemon=True).start()
    
    def conversion_thread(self, input_path, output_dir, mode, output_format, dpi):
        try:
            self.status_var.set("正在准备转换...")
            self.progress_var.set(0)
            
            # 确定要处理的文件列表
            pdf_files = []
            if os.path.isfile(input_path) and input_path.lower().endswith('.pdf'):
                pdf_files = [input_path]
            elif os.path.isdir(input_path):
                for file in os.listdir(input_path):
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(input_path, file))
            
            if not pdf_files:
                self.status_var.set("未找到PDF文件")
                messagebox.showinfo("信息", "未找到PDF文件")
                return
            
            total_files = len(pdf_files)
            self.log(f"找到 {total_files} 个PDF文件待转换")
            
            # 开始转换
            successful = 0
            failed = 0
            
            for i, pdf_file in enumerate(pdf_files):
                file_name = os.path.basename(pdf_file)
                self.status_var.set(f"正在转换 {file_name} ({i+1}/{total_files})")
                # 文件级别进度显示已精简
                
                try:
                    if mode == "document":
                        if output_format == "docx":
                            self.convert_to_docx(pdf_file, output_dir)
                        elif output_format == "pptx":
                            self.convert_to_pptx(pdf_file, output_dir)
                        elif output_format == "pptx_via_word":
                            self.convert_to_pptx_via_word(pdf_file, output_dir)
                        elif output_format == "txt":
                            self.convert_to_txt(pdf_file, output_dir)
                    else:  # image mode
                        self.convert_to_image(pdf_file, output_dir, output_format, dpi)
                    
                    successful += 1
                    # 单文件转换成功日志已精简
                except Exception as e:
                    failed += 1
                    self.log_error(f"转换失败: {file_name}", e)
                
                # 更新进度
                progress = (i + 1) / total_files * 100
                self.progress_var.set(progress)
            
            # 完成
            self.status_var.set(f"转换完成: {successful}成功, {failed}失败")
            self.log_success(f"批量转换完成 - 成功: {successful}, 失败: {failed}")
            messagebox.showinfo("完成", f"转换完成\n成功: {successful}\n失败: {failed}")
            
        except Exception as e:
            self.status_var.set(f"转换过程中发生错误: {str(e)}")
            self.log(f"错误: {str(e)}")
            messagebox.showerror("错误", f"转换过程中发生错误: {str(e)}")
    
    def convert_to_docx(self, pdf_path, output_dir):
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        # 确保路径使用正确的分隔符
        output_path = os.path.normpath(os.path.join(output_dir, f"{base_name}.docx"))
        
        self.log("开始转换PDF到DOCX")
        
        try:
            # 首先检查和预处理PDF文件
            self.log_step("步骤1", "检查PDF文件完整性")
            if not self._check_pdf_integrity(pdf_path):
                self.log("PDF文件检查失败，尝试修复...")
                repaired_path = self._repair_pdf_for_conversion(pdf_path)
                if repaired_path:
                    pdf_path = repaired_path
                    self.log_success(f"PDF修复成功，使用修复后的文件: {repaired_path}")
                else:
                    self.log("PDF修复失败，继续使用原文件")
            
            # 使用pdf2docx库进行转换，保持原始格式和布局
            self.log_step("步骤2", "使用pdf2docx转换")
            self.log("转换参数: multi_processing=False, cpu_count=1")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 获取页面总数用于进度显示
            try:
                import fitz
                doc = fitz.open(pdf_path)
                total_pages = len(doc)
                doc.close()
                self.log(f"PDF总页数: {total_pages}")
            except:
                total_pages = 0
            
            # 添加更详细的参数配置来处理问题PDF
            # 由于pdf2docx不支持进度回调，我们使用线程来模拟进度显示
            import threading
            import time
            
            conversion_complete = threading.Event()
            
            def progress_updater():
                """在转换过程中模拟进度更新"""
                if total_pages > 0:
                    # 模拟进度更新，每秒更新一次
                    progress_step = max(1, total_pages // 20)  # 分20步显示
                    current_progress = 0
                    
                    while not conversion_complete.is_set() and current_progress < total_pages:
                        time.sleep(1)  # 每秒更新一次
                        current_progress = min(current_progress + progress_step, total_pages)
                        if not conversion_complete.is_set():
                            self.log_progress(current_progress, total_pages, f"转换页面 {current_progress}")
            
            # 启动进度更新线程
            if total_pages > 0:
                progress_thread = threading.Thread(target=progress_updater, daemon=True)
                progress_thread.start()
            
            try:
                parse(pdf_path, output_path, 
                      start=0, end=None,  # 转换所有页面
                      pages=None,         # 不指定特定页面
                      password=None,      # 无密码
                      multi_processing=False,  # 禁用多进程避免某些错误
                      cpu_count=1)        # 使用单核处理
            finally:
                # 标记转换完成，停止进度更新
                conversion_complete.set()
                if total_pages > 0:
                    # 显示最终进度
                    self.log_progress(total_pages, total_pages, "转换完成")
            
            # 验证文件是否成功创建
            if os.path.exists(output_path):
                self.log_success(f"转换成功: {base_name}.pdf -> {base_name}.docx")
                self.log(f"输出文件大小: {os.path.getsize(output_path)} 字节")
            else:
                raise FileNotFoundError(f"转换完成但输出文件未找到: {output_path}")
            
        except Exception as e:
            error_msg = str(e)
            self.log_error(f"pdf2docx转换失败", e)
            
            # 检查是否是已知的bandwriter错误
            if "Invalid bandwriter header dimensions" in error_msg or "bandwriter" in error_msg:
                self.log("检测到bandwriter错误，这通常是由于PDF中包含无效尺寸的图像导致")
                self.log_fallback("使用高级修复方法")
                
                # 尝试使用PyMuPDF修复PDF
                if self._fix_bandwriter_error(pdf_path, output_path):
                    self.log_success(f"bandwriter错误修复成功: {base_name}.pdf -> {base_name}.docx")
                    return
                
                # 如果修复失败，尝试逐页转换
                self.log_fallback("尝试逐页转换来跳过问题页面")
                if self._try_page_by_page_conversion(pdf_path, output_path):
                    self.log_success(f"页面范围转换成功: {base_name}.pdf -> {base_name}.docx")
                    return
            
            # 如果pdf2docx转换失败，回退到原来的方法
            self.log_step("步骤3", "使用备用方法转换")
            self._convert_to_docx_fallback(pdf_path, output_dir)
    
    def _check_pdf_integrity(self, pdf_path):
        """检查PDF文件的完整性，特别是查找可能导致bandwriter错误的问题"""
        try:
            self.log(f"检查PDF文件: {pdf_path}")
            doc = fitz.open(pdf_path)
            
            page_count = len(doc)
            self.log(f"PDF页数: {page_count}")
            
            problematic_pages = []
            zero_dimension_images = []
            
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                
                # 检查页面中的图像
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    try:
                        # 获取图像信息
                        xref = img[0]
                        
                        # 直接从文档获取图像信息，避免创建Pixmap
                        img_dict = doc.extract_image(xref)
                        width = img_dict.get('width', 0)
                        height = img_dict.get('height', 0)
                        
                        # 检查图像尺寸
                        if width == 0 or height == 0:
                            self.log(f"发现零尺寸图像: 页面 {page_num + 1}, 图像 {img_index + 1}, 尺寸: {width}x{height}")
                            zero_dimension_images.append((page_num, img_index, xref))
                            if page_num not in problematic_pages:
                                problematic_pages.append(page_num)
                        
                    except Exception as e:
                        self.log(f"检查图像时出错: 页面 {page_num + 1}, 图像 {img_index + 1} - {str(e)}")
                        if page_num not in problematic_pages:
                            problematic_pages.append(page_num)
            
            doc.close()
            
            if problematic_pages:
                self.log(f"发现问题页面: {problematic_pages}")
                self.log(f"发现 {len(zero_dimension_images)} 个零尺寸图像")
                return False
            else:
                self.log("PDF文件检查通过")
                return True
                
        except Exception as e:
            self.log(f"PDF完整性检查失败: {str(e)}")
            return False
    
    def _repair_pdf_for_conversion(self, pdf_path):
        """修复PDF文件以便转换，专门处理零尺寸图像问题"""
        try:
            self.log("尝试修复PDF文件，移除零尺寸图像...")
            
            # 创建临时文件
            temp_dir = tempfile.mkdtemp()
            temp_pdf_path = os.path.join(temp_dir, "repaired_bandwriter_fix.pdf")
            
            # 打开原PDF
            doc = fitz.open(pdf_path)
            
            # 创建新的PDF文档
            new_doc = fitz.open()
            
            removed_images_count = 0
            
            # 逐页复制，移除零尺寸图像
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    rect = page.rect
                    
                    # 创建新页面
                    new_page = new_doc.new_page(width=rect.width, height=rect.height)
                    
                    # 首先复制页面的基本内容（不包括图像）
                    # 获取页面的显示列表，但排除图像
                    page_dict = page.get_text("dict")
                    
                    # 重新插入文本内容
                    for block in page_dict.get("blocks", []):
                        if "lines" in block:  # 文本块
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    text = span.get("text", "")
                                    if text.strip():
                                        bbox = span["bbox"]
                                        font_size = span.get("size", 12)
                                        try:
                                            new_page.insert_text(
                                                (bbox[0], bbox[1]), 
                                                text, 
                                                fontsize=font_size
                                            )
                                        except:
                                            pass  # 忽略插入失败的文本
                    
                    # 处理图像，只保留有效尺寸的图像
                    image_list = page.get_images()
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            
                            # 检查图像尺寸
                            img_dict = doc.extract_image(xref)
                            width = img_dict.get('width', 0)
                            height = img_dict.get('height', 0)
                            
                            if width > 0 and height > 0:
                                # 图像尺寸正常，保留
                                try:
                                    pix = fitz.Pixmap(doc, xref)
                                    img_rects = page.get_image_rects(xref)
                                    if img_rects:
                                        for img_rect in img_rects:
                                            new_page.insert_image(img_rect, pixmap=pix)
                                    pix = None
                                except:
                                    pass  # 如果插入失败，跳过这个图像
                            else:
                                # 零尺寸图像，跳过
                                removed_images_count += 1
                                self.log(f"移除零尺寸图像: 页面 {page_num + 1}, 图像 {img_index + 1}, 尺寸: {width}x{height}")
                        
                        except Exception as e:
                            self.log(f"处理图像时出错: 页面 {page_num + 1}, 图像 {img_index + 1} - {str(e)}")
                            continue
                    
                except Exception as e:
                    self.log(f"处理页面时出错 {page_num + 1}: {str(e)}")
                    # 即使出错也要创建一个空页面，保持页面数量
                    try:
                        new_doc.new_page()
                    except:
                        pass
            
            # 保存修复后的PDF
            new_doc.save(temp_pdf_path, garbage=4, deflate=True)
            new_doc.close()
            doc.close()
            
            self.log(f"PDF修复完成: 移除了 {removed_images_count} 个零尺寸图像")
            self.log(f"修复后的文件: {temp_pdf_path}")
            return temp_pdf_path
            
        except Exception as e:
            self.log(f"PDF修复失败: {str(e)}")
            return None
    
    def _fix_bandwriter_error(self, pdf_path, output_path):
        """专门修复bandwriter错误"""
        try:
            import fitz
            from docx import Document
            
            self.log("使用PyMuPDF直接提取内容来避免bandwriter错误...")
            
            # 打开PDF
            doc = fitz.open(pdf_path)
            
            # 创建Word文档
            word_doc = Document()
            
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    
                    # 添加页面标题
                    if page_num > 0:
                        word_doc.add_page_break()
                    
                    word_doc.add_heading(f'页面 {page_num + 1}', level=2)
                    
                    # 提取文本
                    text = page.get_text()
                    if text.strip():
                        # 按段落分割文本
                        paragraphs = text.split('\n\n')
                        for para in paragraphs:
                            if para.strip():
                                word_doc.add_paragraph(para.strip())
                    
                    # 提取表格
                    try:
                        tables = page.find_tables()
                        for table in tables:
                            word_table = word_doc.add_table(rows=len(table.extract()), cols=len(table.extract()[0]))
                            for i, row in enumerate(table.extract()):
                                for j, cell in enumerate(row):
                                    word_table.cell(i, j).text = str(cell) if cell else ''
                    except:
                        self.log(f"页面 {page_num+1} 表格提取失败")
                    
                    self.log(f"页面 {page_num+1} 内容提取完成")
                    
                except Exception as page_error:
                    self.log(f"页面 {page_num+1} 处理失败: {str(page_error)}")
            
            # 保存文档
            word_doc.save(output_path)
            doc.close()
            
            self.log("bandwriter错误修复方法完成")
            return True
            
        except Exception as e:
            self.log(f"bandwriter错误修复失败: {str(e)}")
            return False
    
    def _try_page_by_page_conversion(self, pdf_path, output_path):
        """尝试逐页转换PDF，跳过有问题的页面"""
        try:
            import fitz  # PyMuPDF
            from docx import Document
            
            self.log("开始逐页转换...")
            
            # 打开PDF文件
            pdf_doc = fitz.open(pdf_path)
            total_pages = len(pdf_doc)
            self.log(f"总页数: {total_pages}")
            
            # 创建新的Word文档
            doc = Document()
            
            successful_pages = 0
            
            for page_num in range(total_pages):
                try:
                    self.log_progress(page_num + 1, total_pages, f"处理页面 {page_num + 1}")
                    
                    # 尝试转换单页
                    temp_pdf_path = pdf_path.replace('.pdf', f'_temp_page_{page_num}.pdf')
                    temp_docx_path = output_path.replace('.docx', f'_temp_page_{page_num}.docx')
                    
                    # 创建单页PDF
                    single_page_doc = fitz.open()
                    single_page_doc.insert_pdf(pdf_doc, from_page=page_num, to_page=page_num)
                    single_page_doc.save(temp_pdf_path)
                    single_page_doc.close()
                    
                    # 尝试转换单页
                    parse(temp_pdf_path, temp_docx_path, 
                          multi_processing=False, cpu_count=1)
                    
                    # 如果成功，将内容添加到主文档
                    temp_doc = Document(temp_docx_path)
                    for paragraph in temp_doc.paragraphs:
                        doc.add_paragraph(paragraph.text)
                    
                    successful_pages += 1
                    self.log(f"✓ 页面 {page_num + 1} 转换成功")
                    
                    # 清理临时文件
                    os.remove(temp_pdf_path)
                    os.remove(temp_docx_path)
                    
                except Exception as page_error:
                    self.log(f"✗ 页面 {page_num + 1} 转换失败: {str(page_error)}")
                    # 使用备用方法提取该页文本
                    try:
                        page = pdf_doc[page_num]
                        text = page.get_text()
                        if text.strip():
                            doc.add_paragraph(f"[页面 {page_num + 1} - 文本提取]")
                            doc.add_paragraph(text)
                            successful_pages += 1
                            self.log(f"✓ 页面 {page_num + 1} 文本提取成功")
                    except:
                        self.log(f"✗ 页面 {page_num + 1} 文本提取也失败")
                    
                    # 清理可能存在的临时文件
                    temp_pdf_path = pdf_path.replace('.pdf', f'_temp_page_{page_num}.pdf')
                    temp_docx_path = output_path.replace('.docx', f'_temp_page_{page_num}.docx')
                    if os.path.exists(temp_pdf_path):
                        os.remove(temp_pdf_path)
                    if os.path.exists(temp_docx_path):
                        os.remove(temp_docx_path)
            
            # 保存最终文档
            if successful_pages > 0:
                doc.save(output_path)
                self.log(f"✓ 页面转换完成: {successful_pages}/{total_pages} 页成功")
                pdf_doc.close()
                return True
            else:
                self.log("✗ 所有页面转换都失败")
                pdf_doc.close()
                return False
                
        except Exception as e:
            self.log(f"✗ 页面转换过程出错: {str(e)}")
            return False

    def _convert_to_docx_fallback(self, pdf_path, output_dir):
        """备用的PDF转DOCX方法，使用原来的实现"""
        try:
            # 获取文件名（不含扩展名）
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            # 确保路径使用正确的分隔符
            output_path = os.path.normpath(os.path.join(output_dir, f"{base_name}.docx"))
            
            self.log(f"使用备用方法转换: {base_name}.pdf")
        
            # 创建一个新的Word文档
            doc = Document()
            
            # 打开PDF文件
            pdf_document = fitz.open(pdf_path)
            
            # 遍历每一页
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text = page.get_text("text")
                
                # 清理文本中的XML不兼容字符
                cleaned_text = self._clean_text_for_xml(text)
                
                # 添加页码标题
                doc.add_heading(f"Page {page_num + 1}", level=1)
                
                # 添加文本内容（只有在有内容时才添加）
                if cleaned_text.strip():
                    doc.add_paragraph(cleaned_text)
                else:
                    doc.add_paragraph("[此页无可提取的文本内容]")
                
                # 添加分页符（除了最后一页）
                if page_num < len(pdf_document) - 1:
                    doc.add_page_break()
            
            # 保存Word文档
            doc.save(output_path)
            pdf_document.close()
            self.log(f"✓ 备用方法转换成功: {base_name}.pdf -> {base_name}.docx")
            
        except Exception as e:
            self.log(f"✗ 备用方法转换失败: {base_name}.pdf - {str(e)}")
            raise e
    
    def _clean_text_for_xml(self, text):
        """清理文本中的XML不兼容字符"""
        if not text:
            return ""
        
        # 移除NULL字节和控制字符（保留换行符、制表符和回车符）
        # XML 1.0 允许的字符范围：
        # #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
        valid_chars = []
        for char in text:
            code = ord(char)
            if (code == 0x09 or  # Tab
                code == 0x0A or  # Line feed
                code == 0x0D or  # Carriage return
                (0x20 <= code <= 0xD7FF) or  # Basic multilingual plane
                (0xE000 <= code <= 0xFFFD) or  # Private use area
                (0x10000 <= code <= 0x10FFFF)):  # Supplementary planes
                valid_chars.append(char)
            else:
                # 替换无效字符为空格
                valid_chars.append(' ')
        
        cleaned_text = ''.join(valid_chars)
        
        # 移除多余的空白字符
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        return cleaned_text.strip()
    
    def convert_to_txt(self, pdf_path, output_dir):
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        # 确保路径使用正确的分隔符
        output_path = os.path.normpath(os.path.join(output_dir, f"{base_name}.txt"))
        
        self.log_step("文本转换", f"开始转换 {base_name}.pdf")
        
        # 打开PDF文件
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        self.log(f"PDF总页数: {total_pages}")
        
        # 创建文本文件
        with open(output_path, 'w', encoding='utf-8') as txt_file:
            # 遍历每一页
            for page_num in range(total_pages):
                self.log_progress(page_num + 1, total_pages, f"提取页面 {page_num + 1} 文本")
                
                page = pdf_document.load_page(page_num)
                text = page.get_text("text")
                
                # 写入页码标题
                txt_file.write(f"===== Page {page_num + 1} =====\n\n")
                
                # 写入文本内容
                txt_file.write(text)
                txt_file.write("\n\n")
        
        pdf_document.close()
        self.log_success(f"文本转换完成: {base_name}.txt")
    
    def convert_to_pptx(self, pdf_path, output_dir):
        """将PDF转换为PowerPoint演示文稿"""
        try:
            # 获取文件名（不含扩展名）
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}.pptx")
            
            self.log_step("PPT转换", f"开始转换 {base_name}.pdf")
            
            # 使用图片转换方案
            converter = PDFToPPTConverterV2()
            self.log("使用图片转换方案，完美保留PDF原始视觉效果")
            
            # 执行转换（不使用模板）
            result_path = converter.convert_pdf_to_ppt(pdf_path, output_path, None)
            
            self.log_success(f"转换完成: {base_name}.pdf -> {base_name}.pptx")
            self.log(f"输出文件: {result_path}")
            
        except Exception as e:
            self.log_error(f"PPT转换失败", e)
            raise e
    
    def convert_to_pptx_via_word(self, pdf_path, output_dir):
        """通过Word中转将PDF转换为PPT"""
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.pptx")
        
        try:
            self.log_step("PDF→Word→PPT转换", f"开始转换 {base_name}.pdf")
            
            # 步骤1: 先将PDF转换为Word
            self.log_step("步骤1", "将PDF转换为Word文档")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_word_path = os.path.join(temp_dir, f"{base_name}_temp.docx")
                
                # 使用现有的PDF转Word方法
                try:
                    from pdf2docx import parse
                    self.log("开始使用pdf2docx转换为Word")
                    
                    # 获取页面总数用于进度显示
                    try:
                        import fitz
                        doc = fitz.open(pdf_path)
                        total_pages = len(doc)
                        doc.close()
                        self.log(f"PDF总页数: {total_pages}")
                    except:
                        total_pages = 0
                    
                    # 添加更详细的参数配置来处理问题PDF
                    parse(pdf_path, temp_word_path,
                          start=0, end=None,
                          pages=None,
                          password=None,
                          multi_processing=False,
                          cpu_count=1)
                    
                    self.log_success("使用pdf2docx成功转换为Word")
                except Exception as e:
                    error_msg = str(e)
                    self.log_error(f"pdf2docx转换失败", e)
                    
                    # 检查是否是已知的bandwriter错误
                    if "Invalid bandwriter header dimensions" in error_msg or "bandwriter" in error_msg:
                        self.log_fallback("检测到bandwriter错误，尝试逐页转换")
                        if self._try_page_by_page_conversion(pdf_path, temp_word_path):
                            self.log_success("页面范围转换成功")
                        else:
                            self.log_fallback("页面范围转换失败，使用备用方法")
                            self._convert_to_docx_fallback_for_ppt(pdf_path, temp_word_path)
                    else:
                        self.log_fallback("使用备用方法")
                        self._convert_to_docx_fallback_for_ppt(pdf_path, temp_word_path)
                
                # 步骤2: 将Word转换为PPT
                self.log_step("步骤2", "将Word文档转换为PPT")
                word_to_ppt_converter = WordToPPTConverter()
                
                # 执行Word到PPT的转换（不使用模板）
                result_path = word_to_ppt_converter.convert_word_to_ppt(temp_word_path, output_path, None)
                
                self.log_success(f"转换完成: {base_name}.pdf -> {base_name}.pptx (通过Word中转)")
                self.log(f"输出文件: {result_path}")
                
        except Exception as e:
            self.log_error(f"PDF→Word→PPT转换失败", e)
            raise e
    
    def _convert_to_docx_fallback_for_ppt(self, pdf_path, output_path):
        """为PPT转换专用的备用PDF转DOCX方法"""
        from docx import Document
        import fitz
        
        self.log_fallback("使用备用方法提取PDF文本")
        
        # 创建一个新的Word文档
        doc = Document()
        
        # 打开PDF文件
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        self.log(f"PDF总页数: {total_pages}")
        
        # 遍历每一页
        for page_num in range(total_pages):
            self.log_progress(page_num + 1, total_pages, f"提取页面 {page_num + 1} 文本")
            
            page = pdf_document.load_page(page_num)
            text = page.get_text("text")
            
            # 如果页面有文本内容，添加到文档
            if text.strip():
                # 添加页面内容，不添加页码标题（为PPT转换优化）
                paragraphs = text.split('\n')
                for para in paragraphs:
                    if para.strip():
                        doc.add_paragraph(para.strip())
                
                # 页面之间添加分隔
                if page_num < total_pages - 1:
                    doc.add_page_break()
        
        pdf_document.close()
        
        # 保存Word文档
        doc.save(output_path)
        self.log_success(f"备用方法转换完成: {total_pages} 页文本已提取")
    
    def convert_to_image(self, pdf_path, output_dir, image_format, dpi):
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        self.log_step("图像转换", f"开始转换 {base_name}.pdf 为 {image_format.upper()} (DPI: {dpi})")
        
        # 打开PDF文件
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        self.log(f"PDF总页数: {total_pages}")
        
        # 计算缩放因子
        zoom = dpi / 72  # PDF使用72 DPI作为基准
        self.log(f"缩放因子: {zoom:.2f}")
        
        # 遍历每一页
        for page_num in range(total_pages):
            self.log_progress(page_num + 1, total_pages, f"渲染页面 {page_num + 1}")
            
            try:
                page = pdf_document.load_page(page_num)
                
                # 渲染页面为像素图
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                
                # 将像素图转换为PIL图像
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # 保存图像
                output_path = os.path.join(output_dir, f"{base_name}_page{page_num + 1}.{image_format}")
                
                if image_format.lower() == "jpg":
                    img.save(output_path, "JPEG", quality=95)
                else:  # png
                    img.save(output_path, "PNG")
                    
            except Exception as e:
                self.log_error(f"页面 {page_num + 1} 转换失败", e)
        
        pdf_document.close()
        self.log_success(f"图像转换完成: {total_pages} 页已转换为 {image_format.upper()}")
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PDFConverter()
    app.run()