import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import fitz  # PyMuPDF
from PIL import Image
import docx
import io
import time

class PDFConverter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PDF格式转换工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 设置应用图标
        try:
            import os
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            elif os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass  # 如果图标不存在，忽略错误
        
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
        ttk.Radiobutton(self.document_formats_frame, text="文本 (TXT)", variable=self.format_var, value="txt").pack(side=tk.LEFT, padx=5)
        
        # 图片格式选项
        ttk.Radiobutton(self.image_formats_frame, text="PNG", variable=self.format_var, value="png").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.image_formats_frame, text="JPG", variable=self.format_var, value="jpg").pack(side=tk.LEFT, padx=5)
        
        # 绑定模式变更事件
        self.mode_var.trace_add("write", self.update_format_options)
        
        # 输出目录选择
        ttk.Label(options_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.output_dir_var = tk.StringVar()
        ttk.Entry(options_frame, textvariable=self.output_dir_var, width=50).grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        
        ttk.Button(options_frame, text="浏览", command=self.browse_output_dir).grid(row=2, column=3, padx=5, pady=5)
        
        # DPI设置（仅图片模式）
        self.dpi_frame = ttk.Frame(options_frame)
        self.dpi_frame.grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=5)
        self.dpi_frame.grid_remove()  # 默认隐藏
        
        ttk.Label(self.dpi_frame, text="DPI设置:").pack(side=tk.LEFT, padx=5)
        
        self.dpi_var = tk.IntVar(value=300)
        ttk.Spinbox(self.dpi_frame, from_=72, to=600, increment=1, textvariable=self.dpi_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # 转换按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="开始转换", command=self.start_conversion, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="转换进度", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
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
        
        if mode == "document":
            self.image_formats_frame.grid_remove()
            self.document_formats_frame.grid()
            self.dpi_frame.grid_remove()
            self.format_var.set("docx")
        else:  # image mode
            self.document_formats_frame.grid_remove()
            self.image_formats_frame.grid()
            self.dpi_frame.grid()
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
    
    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
    
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
                self.log(f"开始转换: {file_name}")
                
                try:
                    if mode == "document":
                        if output_format == "docx":
                            self.convert_to_docx(pdf_file, output_dir)
                        elif output_format == "txt":
                            self.convert_to_txt(pdf_file, output_dir)
                    else:  # image mode
                        self.convert_to_image(pdf_file, output_dir, output_format, dpi)
                    
                    successful += 1
                    self.log(f"成功转换: {file_name}")
                except Exception as e:
                    failed += 1
                    self.log(f"转换失败: {file_name} - {str(e)}")
                
                # 更新进度
                progress = (i + 1) / total_files * 100
                self.progress_var.set(progress)
            
            # 完成
            self.status_var.set(f"转换完成: {successful}成功, {failed}失败")
            messagebox.showinfo("完成", f"转换完成\n成功: {successful}\n失败: {failed}")
            
        except Exception as e:
            self.status_var.set(f"转换过程中发生错误: {str(e)}")
            self.log(f"错误: {str(e)}")
            messagebox.showerror("错误", f"转换过程中发生错误: {str(e)}")
    
    def convert_to_docx(self, pdf_path, output_dir):
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.docx")
        
        # 创建一个新的Word文档
        doc = Document()
        
        # 打开PDF文件
        pdf_document = fitz.open(pdf_path)
        
        # 遍历每一页
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text = page.get_text("text")
            
            # 添加页码标题
            doc.add_heading(f"Page {page_num + 1}", level=1)
            
            # 添加文本内容
            doc.add_paragraph(text)
            
            # 添加分页符（除了最后一页）
            if page_num < len(pdf_document) - 1:
                doc.add_page_break()
        
        # 保存Word文档
        doc.save(output_path)
        pdf_document.close()
        self.log(f"成功转换: {base_name}.pdf -> {base_name}.docx")
    
    def convert_to_txt(self, pdf_path, output_dir):
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.txt")
        
        # 打开PDF文件
        pdf_document = fitz.open(pdf_path)
        
        # 创建文本文件
        with open(output_path, 'w', encoding='utf-8') as txt_file:
            # 遍历每一页
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text = page.get_text("text")
                
                # 写入页码标题
                txt_file.write(f"===== Page {page_num + 1} =====\n\n")
                
                # 写入文本内容
                txt_file.write(text)
                txt_file.write("\n\n")
        
        pdf_document.close()
    
    def convert_to_image(self, pdf_path, output_dir, image_format, dpi):
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # 打开PDF文件
        pdf_document = fitz.open(pdf_path)
        
        # 计算缩放因子
        zoom = dpi / 72  # PDF使用72 DPI作为基准
        
        # 遍历每一页
        for page_num in range(len(pdf_document)):
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
        
        pdf_document.close()
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PDFConverter()
    app.run()