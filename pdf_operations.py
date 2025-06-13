import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import os
import io
import threading

class PDFOperations:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.pdf_document = None
        self.pdf_path = ""
        self.page_thumbnails = []
        self.selected_pages = set()
        self.ui_frame = None
        self.current_operation = "delete_pages"
        
    def show_ui(self, parent_frame):
        """显示PDF操作界面"""
        if self.ui_frame:
            self.ui_frame.destroy()
        
        self.ui_frame = parent_frame
        self.setup_ui()
    
    def hide_ui(self):
        """隐藏PDF操作界面"""
        if hasattr(self, 'main_frame') and self.main_frame:
            for widget in self.main_frame.winfo_children():
                widget.destroy()
    
    def switch_operation(self, operation):
        """切换操作类型"""
        self.current_operation = operation
        if hasattr(self, 'main_frame') and self.main_frame:
            self.setup_ui()
    
    def setup_ui(self):
        """设置PDF操作界面"""
        if not self.ui_frame:
            return
            
        # 清除现有内容
        for widget in self.ui_frame.winfo_children():
            widget.destroy()
        
        # 主框架
        self.main_frame = ttk.Frame(self.ui_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 根据当前操作显示不同的UI
        if self.current_operation == "delete_pages":
            self.setup_delete_pages_ui()
        else:
            # 其他操作的占位符
            placeholder_label = ttk.Label(self.main_frame, 
                                        text=f"功能开发中: {self.current_operation}",
                                        font=("Segoe UI", 14))
            placeholder_label.pack(expand=True)
    
    def setup_delete_pages_ui(self):
        """设置删除页面功能的UI"""
        # 主标题
        title_label = ttk.Label(self.main_frame, text="PDF页面删除", font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(self.main_frame, text="选择PDF文件", padding="15")
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 文件路径显示
        path_frame = ttk.Frame(file_frame)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(path_frame, text="文件路径:").pack(anchor=tk.W, pady=(0, 5))
        self.file_path_var = tk.StringVar()
        path_entry = ttk.Entry(path_frame, textvariable=self.file_path_var, state="readonly")
        path_entry.pack(fill=tk.X, pady=(0, 10))
        
        # 文件选择按钮
        button_frame = ttk.Frame(file_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="选择PDF文件", command=self.browse_pdf_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="加载页面", command=self.load_pdf_pages).pack(side=tk.LEFT, padx=(0, 10))
        
        # 页面预览区域
        preview_frame = ttk.LabelFrame(self.main_frame, text="页面预览 (勾选要删除的页面)", padding="15")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建滚动区域
        canvas_frame = ttk.Frame(preview_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white")
        scrollbar_v = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        scrollbar_h = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar_v.pack(side="right", fill="y")
        scrollbar_h.pack(side="bottom", fill="x")
        
        # 绑定鼠标滚轮事件到canvas和scrollable_frame
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        
        # 绑定鼠标进入事件以获取焦点
        def on_enter(event):
            self.canvas.focus_set()
            # 确保canvas能接收键盘事件
            self.canvas.configure(highlightthickness=0)
        
        self.canvas.bind("<Enter>", on_enter)
        self.scrollable_frame.bind("<Enter>", on_enter)
        
        # 绑定鼠标移动事件，确保在预览区域内时能响应滚轮
        def on_motion(event):
            self.canvas.focus_set()
        
        self.canvas.bind("<Motion>", on_motion)
        
        # 操作按钮区域
        action_frame = ttk.Frame(self.main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(action_frame, text="全选", command=self.select_all_pages).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="全不选", command=self.deselect_all_pages).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="反选", command=self.invert_selection).pack(side=tk.LEFT, padx=(0, 10))
        
        # 删除按钮
        delete_frame = ttk.Frame(self.main_frame)
        delete_frame.pack(fill=tk.X)
        
        ttk.Button(delete_frame, text="删除选中页面", command=self.delete_selected_pages, 
                  style="Convert.TButton").pack(anchor=tk.CENTER)
        
    def browse_pdf_file(self):
        """浏览选择PDF文件"""
        filetypes = [("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        file_path = filedialog.askopenfilename(filetypes=filetypes, title="选择PDF文件")
        
        if file_path:
            self.file_path_var.set(file_path)
            self.pdf_path = file_path
            
    def load_pdf_pages(self):
        """加载PDF页面缩略图"""
        if not self.pdf_path:
            messagebox.showwarning("警告", "请先选择PDF文件")
            return
            
        try:
            # 打开PDF文档
            self.pdf_document = fitz.open(self.pdf_path)
            
            # 清空之前的缩略图
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            self.page_thumbnails = []
            self.selected_pages = set()
            
            # 创建页面缩略图
            self._create_thumbnails()
            
        except Exception as e:
            messagebox.showerror("错误", f"加载PDF文件失败: {str(e)}")
            
    def _create_thumbnails(self):
        """创建页面缩略图"""
        # 在新线程中生成缩略图，避免界面卡顿
        threading.Thread(target=self._generate_thumbnails, daemon=True).start()
        
    def _generate_thumbnails(self):
        """生成缩略图（在后台线程中运行）"""
        try:
            total_pages = len(self.pdf_document)
            
            # 计算每行显示的缩略图数量
            thumbnails_per_row = 4
            thumbnail_size = (150, 200)
            
            for page_num in range(total_pages):
                # 在主线程中更新UI
                self.parent.after(0, self._create_single_thumbnail, page_num, thumbnails_per_row, thumbnail_size)
                
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("错误", f"生成缩略图失败: {str(e)}"))
            
    def _create_single_thumbnail(self, page_num, thumbnails_per_row, thumbnail_size):
        """创建单个页面的缩略图"""
        try:
            page = self.pdf_document[page_num]
            
            # 生成页面图像
            mat = fitz.Matrix(0.5, 0.5)  # 缩放矩阵
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            
            # 转换为PIL图像
            pil_image = Image.open(io.BytesIO(img_data))
            pil_image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            # 转换为Tkinter可用的图像
            tk_image = ImageTk.PhotoImage(pil_image)
            
            # 计算位置
            row = page_num // thumbnails_per_row
            col = page_num % thumbnails_per_row
            
            # 创建页面框架
            page_frame = ttk.Frame(self.scrollable_frame, relief="solid", borderwidth=1)
            page_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # 页面选择复选框
            page_var = tk.BooleanVar()
            checkbox = ttk.Checkbutton(page_frame, text=f"第{page_num + 1}页", variable=page_var,
                                     command=lambda p=page_num, v=page_var: self._on_page_select(p, v))
            checkbox.pack(pady=(5, 0))
            
            # 页面缩略图
            img_label = ttk.Label(page_frame, image=tk_image)
            img_label.pack(pady=5)
            
            # 绑定双击事件
            img_label.bind("<Double-Button-1>", lambda e, p=page_num: self.show_large_image(p))
            
            # 为所有子组件绑定鼠标滚轮事件
            page_frame.bind("<MouseWheel>", self._on_mousewheel)
            checkbox.bind("<MouseWheel>", self._on_mousewheel)
            img_label.bind("<MouseWheel>", self._on_mousewheel)
            
            # 保存引用，防止图像被垃圾回收
            self.page_thumbnails.append({
                'image': tk_image,
                'var': page_var,
                'frame': page_frame
            })
            
        except Exception as e:
            print(f"创建第{page_num + 1}页缩略图失败: {str(e)}")
            
    def _on_page_select(self, page_num, var):
        """页面选择状态改变时的回调"""
        if var.get():
            self.selected_pages.add(page_num)
        else:
            self.selected_pages.discard(page_num)
            
    def select_all_pages(self):
        """全选所有页面"""
        for i, thumbnail in enumerate(self.page_thumbnails):
            thumbnail['var'].set(True)
            self.selected_pages.add(i)
            
    def deselect_all_pages(self):
        """取消选择所有页面"""
        for thumbnail in self.page_thumbnails:
            thumbnail['var'].set(False)
        self.selected_pages.clear()
        
    def invert_selection(self):
        """反选"""
        for i, thumbnail in enumerate(self.page_thumbnails):
            current_state = thumbnail['var'].get()
            thumbnail['var'].set(not current_state)
            if current_state:
                self.selected_pages.discard(i)
            else:
                self.selected_pages.add(i)
                
    def show_large_image(self, page_num):
        """显示页面大图"""
        if not self.pdf_document:
            return
        
        try:
            # 创建新窗口
            large_window = tk.Toplevel(self.parent)
            large_window.title(f"PDF页面预览 - 第{page_num}页 (共{len(self.pdf_document)}页)")
            large_window.geometry("800x950")  # 增加高度以容纳导航按钮
            large_window.resizable(True, True)
            
            # 创建主容器
            main_container = ttk.Frame(large_window)
            main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 创建导航按钮区域
            nav_frame = ttk.Frame(main_container)
            nav_frame.pack(fill=tk.X, pady=(0, 10))
            
            # 当前页面变量
            current_page = tk.IntVar(value=page_num)
            
            # 左切换按钮
            prev_btn = ttk.Button(nav_frame, text="◀ 上一页")
            prev_btn.pack(side=tk.LEFT)
            
            # 页面信息标签
            page_info_label = ttk.Label(nav_frame, text=f"第 {page_num} 页 / 共 {len(self.pdf_document)} 页")
            page_info_label.pack(side=tk.LEFT, expand=True)
            
            # 右切换按钮
            next_btn = ttk.Button(nav_frame, text="下一页 ▶")
            next_btn.pack(side=tk.RIGHT)
            
            # 图像显示区域容器
            image_container = ttk.Frame(main_container)
            image_container.pack(fill=tk.BOTH, expand=True)
            
            # 定义更新图像的函数
            def update_image(new_page_num):
                try:
                    # 获取页面
                    page = self.pdf_document[new_page_num - 1]
                    
                    # 生成高分辨率图像
                    mat = fitz.Matrix(2.0, 2.0)  # 2倍缩放
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("ppm")
                    
                    # 转换为PIL图像
                    pil_image = Image.open(io.BytesIO(img_data))
                    
                    return pil_image, img_data
                except Exception as e:
                    messagebox.showerror("错误", f"加载页面失败：{str(e)}")
                    return None, None
            
            # 初始化图像
            pil_image, img_data = update_image(page_num)
            if pil_image is None:
                return
            
            # 创建滚动区域
            canvas = tk.Canvas(image_container, bg="white")
            scrollbar_v = ttk.Scrollbar(image_container, orient="vertical", command=canvas.yview)
            scrollbar_h = ttk.Scrollbar(image_container, orient="horizontal", command=canvas.xview)
            scrollable_frame = ttk.Frame(canvas)
            
            # 图像标签变量，用于更新图像
            img_label = None
            
            # 定义显示图像的函数
            def display_image(pil_img, img_data_bytes):
                nonlocal img_label
                
                # 获取窗口尺寸（减去边距和滚动条空间）
                window_width = 800 - 60  # 减去左右边距和滚动条
                window_height = 900 - 120  # 减去上下边距、标题栏和导航按钮
                
                # 计算缩放比例以适应窗口宽度
                img_width, img_height = pil_img.size
                scale_factor = min(window_width / img_width, window_height / img_height, 1.0)
                
                # 如果需要缩放，则调整图像大小
                if scale_factor < 1.0:
                    new_width = int(img_width * scale_factor)
                    new_height = int(img_height * scale_factor)
                    pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 转换为Tkinter图像
                tk_image = ImageTk.PhotoImage(pil_img)
                
                # 如果图像标签已存在，更新图像；否则创建新标签
                if img_label is None:
                    img_label = ttk.Label(scrollable_frame, image=tk_image)
                    img_label.pack(padx=10, pady=10)
                else:
                    img_label.configure(image=tk_image)
                
                # 保持图像引用
                img_label.image = tk_image
                
                return img_width, img_height, img_data_bytes
            
            # 显示初始图像
            original_img_width, original_img_height, current_img_data = display_image(pil_image, img_data)
            
            # 定义导航按钮的功能
            def go_to_prev_page():
                current_val = current_page.get()
                if current_val > 1:
                    new_page = current_val - 1
                    current_page.set(new_page)
                    new_pil_image, new_img_data = update_image(new_page)
                    if new_pil_image is not None:
                        display_image(new_pil_image, new_img_data)
                        page_info_label.config(text=f"第 {new_page} 页 / 共 {len(self.pdf_document)} 页")
                        large_window.title(f"PDF页面预览 - 第{new_page}页 (共{len(self.pdf_document)}页)")
                        update_button_states()
            
            def go_to_next_page():
                current_val = current_page.get()
                if current_val < len(self.pdf_document):
                    new_page = current_val + 1
                    current_page.set(new_page)
                    new_pil_image, new_img_data = update_image(new_page)
                    if new_pil_image is not None:
                        display_image(new_pil_image, new_img_data)
                        page_info_label.config(text=f"第 {new_page} 页 / 共 {len(self.pdf_document)} 页")
                        large_window.title(f"PDF页面预览 - 第{new_page}页 (共{len(self.pdf_document)}页)")
                        update_button_states()
            
            def update_button_states():
                current_val = current_page.get()
                prev_btn.config(state="normal" if current_val > 1 else "disabled")
                next_btn.config(state="normal" if current_val < len(self.pdf_document) else "disabled")
            
            # 绑定按钮功能
            prev_btn.config(command=go_to_prev_page)
            next_btn.config(command=go_to_next_page)
            
            # 初始化按钮状态
            update_button_states()
            
            # 绑定键盘快捷键
            def on_key_press(event):
                if event.keysym == "Left":
                    go_to_prev_page()
                elif event.keysym == "Right":
                    go_to_next_page()
            
            large_window.bind("<Key>", on_key_press)
            large_window.focus_set()
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
            
            # 布局滚动条和画布
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar_v.pack(side="right", fill="y")
            scrollbar_h.pack(side="bottom", fill="x")
            
            # 添加窗口大小变化时的动态调整
            def on_window_resize(event):
                if event.widget == large_window:
                    # 重新获取当前页面并重新显示
                    current_val = current_page.get()
                    new_pil_image, new_img_data = update_image(current_val)
                    if new_pil_image is not None:
                        display_image(new_pil_image, new_img_data)
            
            large_window.bind("<Configure>", on_window_resize)
            
            # 绑定鼠标滚轮事件
            def on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            canvas.bind("<MouseWheel>", on_mousewheel)
            
            # 居中显示窗口
            large_window.transient(self.parent)
            large_window.grab_set()
            
        except Exception as e:
            messagebox.showerror("错误", f"显示大图时出错：{str(e)}")
    
    def delete_selected_pages(self):
        """删除选中的页面"""
        if not self.selected_pages:
            messagebox.showwarning("警告", "请先选择要删除的页面")
            return
            
        if not self.pdf_document:
            messagebox.showerror("错误", "没有加载PDF文档")
            return
            
        # 确认删除
        selected_count = len(self.selected_pages)
        total_pages = len(self.pdf_document)
        
        if selected_count >= total_pages:
            messagebox.showerror("错误", "不能删除所有页面")
            return
            
        result = messagebox.askyesno("确认删除", 
                                   f"确定要删除选中的 {selected_count} 个页面吗？\n\n"
                                   f"删除后将保存为新文件。")
        
        if not result:
            return
            
        # 选择保存路径
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf")],
            title="保存删除页面后的PDF文件"
        )
        
        if not save_path:
            return
            
        try:
            # 创建新的PDF文档
            new_doc = fitz.open()
            
            # 复制未选中的页面到新文档
            for page_num in range(len(self.pdf_document)):
                if page_num not in self.selected_pages:
                    new_doc.insert_pdf(self.pdf_document, from_page=page_num, to_page=page_num)
                    
            # 保存新文档
            new_doc.save(save_path)
            new_doc.close()
            
            messagebox.showinfo("成功", f"页面删除完成！\n\n"
                              f"删除了 {selected_count} 个页面\n"
                              f"保存路径: {save_path}")
            
            # 重新加载页面（可选）
            self.pdf_path = save_path
            self.file_path_var.set(save_path)
            self.load_pdf_pages()
            
        except Exception as e:
            messagebox.showerror("错误", f"删除页面失败: {str(e)}")
            
    def _on_mousewheel(self, event):
        """鼠标滚轮事件处理"""
        # 确保canvas有焦点
        self.canvas.focus_set()
        # 滚动canvas
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # 阻止事件继续传播
        return "break"