import os
import json
import tkinter as tk
from tkinter import ttk, colorchooser, font, filedialog, messagebox
import sys

class UICustomizer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PDF转换工具 - UI自定义器")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 尝试设置应用图标
        try:
            import os
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            elif os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 默认主题设置
        self.default_theme = {
            "theme_name": "默认主题",
            "window_title": "PDF格式转换工具",
            "window_size": "800x600",
            "background_color": "#f0f0f0",
            "foreground_color": "#333333",
            "accent_color": "#4285f4",
            "button_background": "#4285f4",
            "button_foreground": "#ffffff",
            "font_family": "Segoe UI",
            "font_size": 10,
            "progress_bar_color": "#34a853",
            "header_color": "#4285f4",
            "border_color": "#cccccc",
            "success_color": "#34a853",
            "error_color": "#ea4335",
            "warning_color": "#fbbc05",
            "info_color": "#4285f4",
            "logo_path": ""
        }
        
        # 当前主题设置
        self.current_theme = self.default_theme.copy()
        
        # 加载已保存的主题（如果存在）
        self.themes_file = "ui_themes.json"
        self.saved_themes = []
        self.load_themes()
        
        self.setup_ui()
    
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左右分栏
        left_frame = ttk.Frame(main_frame, padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(main_frame, padding="5")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 左侧：主题设置
        settings_frame = ttk.LabelFrame(left_frame, text="主题设置", padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建滚动画布
        canvas = tk.Canvas(settings_frame)
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 主题名称
        ttk.Label(scrollable_frame, text="主题名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.theme_name_var = tk.StringVar(value=self.current_theme["theme_name"])
        ttk.Entry(scrollable_frame, textvariable=self.theme_name_var, width=30).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 窗口标题
        ttk.Label(scrollable_frame, text="窗口标题:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.window_title_var = tk.StringVar(value=self.current_theme["window_title"])
        ttk.Entry(scrollable_frame, textvariable=self.window_title_var, width=30).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 窗口大小
        ttk.Label(scrollable_frame, text="窗口大小:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.window_size_var = tk.StringVar(value=self.current_theme["window_size"])
        ttk.Entry(scrollable_frame, textvariable=self.window_size_var, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 颜色选择器
        color_settings = [
            ("背景颜色", "background_color"),
            ("前景颜色", "foreground_color"),
            ("强调颜色", "accent_color"),
            ("按钮背景", "button_background"),
            ("按钮前景", "button_foreground"),
            ("进度条颜色", "progress_bar_color"),
            ("标题颜色", "header_color"),
            ("边框颜色", "border_color"),
            ("成功颜色", "success_color"),
            ("错误颜色", "error_color"),
            ("警告颜色", "warning_color"),
            ("信息颜色", "info_color")
        ]
        
        self.color_vars = {}
        for i, (label, key) in enumerate(color_settings):
            ttk.Label(scrollable_frame, text=f"{label}:").grid(row=i+3, column=0, sticky=tk.W, pady=5)
            
            color_frame = ttk.Frame(scrollable_frame)
            color_frame.grid(row=i+3, column=1, sticky=tk.W, pady=5)
            
            self.color_vars[key] = tk.StringVar(value=self.current_theme[key])
            color_entry = ttk.Entry(color_frame, textvariable=self.color_vars[key], width=10)
            color_entry.pack(side=tk.LEFT, padx=5)
            
            color_button = ttk.Button(
                color_frame, 
                text="选择", 
                command=lambda k=key: self.choose_color(k)
            )
            color_button.pack(side=tk.LEFT, padx=5)
            
            # 颜色预览
            preview = tk.Frame(color_frame, width=20, height=20, bg=self.current_theme[key])
            preview.pack(side=tk.LEFT, padx=5)
            setattr(self, f"{key}_preview", preview)
        
        # 字体设置
        row = len(color_settings) + 3
        ttk.Label(scrollable_frame, text="字体:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        font_frame = ttk.Frame(scrollable_frame)
        font_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        
        # 字体家族
        self.font_family_var = tk.StringVar(value=self.current_theme["font_family"])
        font_families = sorted(font.families())
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_family_var, values=font_families, width=15)
        font_combo.pack(side=tk.LEFT, padx=5)
        
        # 字体大小
        ttk.Label(font_frame, text="大小:").pack(side=tk.LEFT, padx=5)
        self.font_size_var = tk.IntVar(value=self.current_theme["font_size"])
        ttk.Spinbox(font_frame, from_=8, to=16, textvariable=self.font_size_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # 自定义Logo
        row += 1
        ttk.Label(scrollable_frame, text="自定义Logo:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        logo_frame = ttk.Frame(scrollable_frame)
        logo_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        
        self.logo_path_var = tk.StringVar(value=self.current_theme["logo_path"])
        ttk.Entry(logo_frame, textvariable=self.logo_path_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(logo_frame, text="浏览", command=self.browse_logo).pack(side=tk.LEFT, padx=5)
        
        # 右侧：预览和主题管理
        preview_frame = ttk.LabelFrame(right_frame, text="预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建预览画布
        self.preview_canvas = tk.Canvas(preview_frame, bg=self.current_theme["background_color"])
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 主题管理
        themes_frame = ttk.LabelFrame(right_frame, text="主题管理", padding="10")
        themes_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 已保存主题列表
        ttk.Label(themes_frame, text="已保存主题:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.themes_listbox = tk.Listbox(themes_frame, height=5, width=30)
        self.themes_listbox.grid(row=0, column=1, rowspan=3, padx=5, pady=5)
        self.update_themes_list()
        
        # 主题管理按钮
        buttons_frame = ttk.Frame(themes_frame)
        buttons_frame.grid(row=0, column=2, rowspan=3, padx=5, pady=5)
        
        ttk.Button(buttons_frame, text="加载主题", command=self.load_selected_theme).pack(fill=tk.X, pady=2)
        ttk.Button(buttons_frame, text="保存当前主题", command=self.save_current_theme).pack(fill=tk.X, pady=2)
        ttk.Button(buttons_frame, text="删除主题", command=self.delete_selected_theme).pack(fill=tk.X, pady=2)
        ttk.Button(buttons_frame, text="重置为默认", command=self.reset_to_default).pack(fill=tk.X, pady=2)
        
        # 应用按钮
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(action_frame, text="预览", command=self.update_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="应用到PDF转换工具", command=self.apply_theme).pack(side=tk.RIGHT, padx=5)
        
        # 初始化预览
        self.update_preview()
    
    def choose_color(self, key):
        current_color = self.color_vars[key].get()
        color = colorchooser.askcolor(initial=current_color)[1]
        if color:
            self.color_vars[key].set(color)
            getattr(self, f"{key}_preview").config(bg=color)
    
    def browse_logo(self):
        filetypes = [
            ("图片文件", "*.png;*.jpg;*.jpeg;*.gif;*.ico;*.svg"),
            ("所有文件", "*.*")
        ]
        logo_path = filedialog.askopenfilename(filetypes=filetypes, title="选择Logo图片")
        if logo_path:
            self.logo_path_var.set(logo_path)
    
    def update_preview(self):
        # 更新当前主题设置
        self.update_current_theme()
        
        # 清除预览画布
        self.preview_canvas.delete("all")
        self.preview_canvas.config(bg=self.current_theme["background_color"])
        
        # 绘制预览UI
        width = self.preview_canvas.winfo_width()
        height = self.preview_canvas.winfo_height()
        
        # 如果画布尚未渲染，使用默认尺寸
        if width <= 1:
            width = 400
        if height <= 1:
            height = 300
        
        # 绘制标题栏
        self.preview_canvas.create_rectangle(
            0, 0, width, 30, 
            fill=self.current_theme["header_color"], 
            outline=self.current_theme["border_color"]
        )
        
        self.preview_canvas.create_text(
            10, 15, 
            text=self.current_theme["window_title"], 
            fill=self.current_theme["button_foreground"],
            anchor="w",
            font=(self.current_theme["font_family"], self.current_theme["font_size"], "bold")
        )
        
        # 绘制文件选择区域
        self.preview_canvas.create_rectangle(
            10, 40, width-10, 90, 
            fill=self.current_theme["background_color"], 
            outline=self.current_theme["border_color"]
        )
        
        self.preview_canvas.create_text(
            20, 50, 
            text="文件选择", 
            fill=self.current_theme["foreground_color"],
            anchor="w",
            font=(self.current_theme["font_family"], self.current_theme["font_size"])
        )
        
        # 绘制输入框
        self.preview_canvas.create_rectangle(
            100, 65, width-100, 85, 
            fill="white", 
            outline=self.current_theme["border_color"]
        )
        
        # 绘制按钮
        self.draw_button(width-90, 65, width-20, 85, "浏览文件")
        
        # 绘制转换选项区域
        self.preview_canvas.create_rectangle(
            10, 100, width-10, 180, 
            fill=self.current_theme["background_color"], 
            outline=self.current_theme["border_color"]
        )
        
        self.preview_canvas.create_text(
            20, 110, 
            text="转换选项", 
            fill=self.current_theme["foreground_color"],
            anchor="w",
            font=(self.current_theme["font_family"], self.current_theme["font_size"])
        )
        
        # 绘制单选按钮
        self.draw_radio(30, 130, "文档模式")
        self.draw_radio(150, 130, "图片模式")
        
        # 绘制输出格式
        self.preview_canvas.create_text(
            20, 150, 
            text="输出格式:", 
            fill=self.current_theme["foreground_color"],
            anchor="w",
            font=(self.current_theme["font_family"], self.current_theme["font_size"])
        )
        
        self.draw_radio(100, 150, "Word (DOCX)")
        self.draw_radio(220, 150, "文本 (TXT)")
        
        # 绘制进度区域
        self.preview_canvas.create_rectangle(
            10, 190, width-10, 240, 
            fill=self.current_theme["background_color"], 
            outline=self.current_theme["border_color"]
        )
        
        self.preview_canvas.create_text(
            20, 200, 
            text="转换进度", 
            fill=self.current_theme["foreground_color"],
            anchor="w",
            font=(self.current_theme["font_family"], self.current_theme["font_size"])
        )
        
        # 绘制进度条
        self.preview_canvas.create_rectangle(
            20, 220, width-20, 230, 
            fill="white", 
            outline=self.current_theme["border_color"]
        )
        
        # 绘制进度
        progress_width = (width-40) * 0.7  # 70%进度
        self.preview_canvas.create_rectangle(
            20, 220, 20 + progress_width, 230, 
            fill=self.current_theme["progress_bar_color"], 
            outline=""
        )
        
        # 绘制开始转换按钮
        self.draw_button(width-110, height-40, width-20, height-10, "开始转换")
        
        # 如果有自定义Logo，显示Logo
        if self.current_theme["logo_path"] and os.path.exists(self.current_theme["logo_path"]):
            try:
                logo_img = tk.PhotoImage(file=self.current_theme["logo_path"])
                # 调整大小
                logo_img = logo_img.subsample(max(1, logo_img.width() // 50))
                self.preview_canvas.logo_img = logo_img  # 保持引用
                self.preview_canvas.create_image(width-50, 15, image=logo_img)
            except Exception as e:
                print(f"加载Logo出错: {str(e)}")
    
    def draw_button(self, x1, y1, x2, y2, text):
        self.preview_canvas.create_rectangle(
            x1, y1, x2, y2, 
            fill=self.current_theme["button_background"], 
            outline=self.current_theme["border_color"]
        )
        
        text_x = (x1 + x2) // 2
        text_y = (y1 + y2) // 2
        
        self.preview_canvas.create_text(
            text_x, text_y, 
            text=text, 
            fill=self.current_theme["button_foreground"],
            font=(self.current_theme["font_family"], self.current_theme["font_size"])
        )
    
    def draw_radio(self, x, y, text):
        radius = 6
        self.preview_canvas.create_oval(
            x-radius, y-radius, x+radius, y+radius, 
            outline=self.current_theme["foreground_color"],
            fill="white"
        )
        
        self.preview_canvas.create_text(
            x+15, y, 
            text=text, 
            fill=self.current_theme["foreground_color"],
            anchor="w",
            font=(self.current_theme["font_family"], self.current_theme["font_size"])
        )
    
    def update_current_theme(self):
        self.current_theme["theme_name"] = self.theme_name_var.get()
        self.current_theme["window_title"] = self.window_title_var.get()
        self.current_theme["window_size"] = self.window_size_var.get()
        
        for key, var in self.color_vars.items():
            self.current_theme[key] = var.get()
        
        self.current_theme["font_family"] = self.font_family_var.get()
        self.current_theme["font_size"] = self.font_size_var.get()
        self.current_theme["logo_path"] = self.logo_path_var.get()
    
    def load_themes(self):
        if os.path.exists(self.themes_file):
            try:
                with open(self.themes_file, 'r', encoding='utf-8') as f:
                    self.saved_themes = json.load(f)
            except Exception as e:
                print(f"加载主题文件出错: {str(e)}")
                self.saved_themes = []
    
    def save_themes(self):
        try:
            with open(self.themes_file, 'w', encoding='utf-8') as f:
                json.dump(self.saved_themes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存主题文件出错: {str(e)}")
            messagebox.showerror("错误", f"保存主题文件出错: {str(e)}")
    
    def update_themes_list(self):
        self.themes_listbox.delete(0, tk.END)
        for theme in self.saved_themes:
            self.themes_listbox.insert(tk.END, theme["theme_name"])
    
    def load_selected_theme(self):
        selection = self.themes_listbox.curselection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个主题")
            return
        
        index = selection[0]
        self.current_theme = self.saved_themes[index].copy()
        
        # 更新UI
        self.theme_name_var.set(self.current_theme["theme_name"])
        self.window_title_var.set(self.current_theme["window_title"])
        self.window_size_var.set(self.current_theme["window_size"])
        
        for key, var in self.color_vars.items():
            var.set(self.current_theme[key])
            getattr(self, f"{key}_preview").config(bg=self.current_theme[key])
        
        self.font_family_var.set(self.current_theme["font_family"])
        self.font_size_var.set(self.current_theme["font_size"])
        self.logo_path_var.set(self.current_theme["logo_path"])
        
        self.update_preview()
        messagebox.showinfo("成功", f"已加载主题: {self.current_theme['theme_name']}")
    
    def save_current_theme(self):
        self.update_current_theme()
        
        # 检查主题名称
        theme_name = self.current_theme["theme_name"]
        if not theme_name:
            messagebox.showerror("错误", "请输入主题名称")
            return
        
        # 检查是否已存在同名主题
        for i, theme in enumerate(self.saved_themes):
            if theme["theme_name"] == theme_name:
                # 询问是否覆盖
                if messagebox.askyesno("确认", f"已存在名为 '{theme_name}' 的主题，是否覆盖?"):
                    self.saved_themes[i] = self.current_theme.copy()
                    self.save_themes()
                    self.update_themes_list()
                    messagebox.showinfo("成功", f"已更新主题: {theme_name}")
                return
        
        # 添加新主题
        self.saved_themes.append(self.current_theme.copy())
        self.save_themes()
        self.update_themes_list()
        messagebox.showinfo("成功", f"已保存主题: {theme_name}")
    
    def delete_selected_theme(self):
        selection = self.themes_listbox.curselection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个主题")
            return
        
        index = selection[0]
        theme_name = self.saved_themes[index]["theme_name"]
        
        if messagebox.askyesno("确认", f"确定要删除主题 '{theme_name}' 吗?"):
            del self.saved_themes[index]
            self.save_themes()
            self.update_themes_list()
            messagebox.showinfo("成功", f"已删除主题: {theme_name}")
    
    def reset_to_default(self):
        if messagebox.askyesno("确认", "确定要重置为默认主题吗?"):
            self.current_theme = self.default_theme.copy()
            
            # 更新UI
            self.theme_name_var.set(self.current_theme["theme_name"])
            self.window_title_var.set(self.current_theme["window_title"])
            self.window_size_var.set(self.current_theme["window_size"])
            
            for key, var in self.color_vars.items():
                var.set(self.current_theme[key])
                getattr(self, f"{key}_preview").config(bg=self.current_theme[key])
            
            self.font_family_var.set(self.current_theme["font_family"])
            self.font_size_var.set(self.current_theme["font_size"])
            self.logo_path_var.set(self.current_theme["logo_path"])
            
            self.update_preview()
            messagebox.showinfo("成功", "已重置为默认主题")
    
    def apply_theme(self):
        self.update_current_theme()
        
        # 生成主题配置文件
        theme_config_file = "ui_theme_config.py"
        
        try:
            with open(theme_config_file, 'w', encoding='utf-8') as f:
                f.write("# PDF转换工具 - UI主题配置文件\n")
                f.write("# 由UI自定义器生成，请勿手动修改\n\n")
                
                f.write("# 主题信息\n")
                f.write(f"THEME_NAME = \"{self.current_theme['theme_name']}\"\n")
                f.write(f"WINDOW_TITLE = \"{self.current_theme['window_title']}\"\n")
                f.write(f"WINDOW_SIZE = \"{self.current_theme['window_size']}\"\n\n")
                
                f.write("# 颜色设置\n")
                for key in [
                    "background_color", "foreground_color", "accent_color",
                    "button_background", "button_foreground", "progress_bar_color",
                    "header_color", "border_color", "success_color",
                    "error_color", "warning_color", "info_color"
                ]:
                    f.write(f"{key.upper()} = \"{self.current_theme[key]}\"\n")
                
                f.write("\n# 字体设置\n")
                f.write(f"FONT_FAMILY = \"{self.current_theme['font_family']}\"\n")
                f.write(f"FONT_SIZE = {self.current_theme['font_size']}\n\n")
                
                f.write("# 自定义Logo\n")
                f.write(f"LOGO_PATH = \"{self.current_theme['logo_path']}\"\n")
            
            # 生成主题应用器文件
            theme_applier_file = "apply_theme.py"
            
            with open(theme_applier_file, 'w', encoding='utf-8') as f:
                f.write("# PDF转换工具 - 主题应用器\n")
                f.write("# 由UI自定义器生成，用于应用自定义主题\n\n")
                
                f.write("import os\n")
                f.write("import sys\n")
                f.write("import tkinter as tk\n")
                f.write("from tkinter import ttk, messagebox\n\n")
                
                f.write("def apply_theme(root):\n")
                f.write("    \"\"\"应用自定义主题到tkinter窗口\"\"\"\n")
                f.write("    try:\n")
                f.write("        # 导入主题配置\n")
                f.write("        sys.path.append(os.path.dirname(os.path.abspath(__file__)))\n")
                f.write("        import ui_theme_config as theme\n\n")
                
                f.write("        # 应用窗口标题和大小\n")
                f.write("        root.title(theme.WINDOW_TITLE)\n")
                f.write("        root.geometry(theme.WINDOW_SIZE)\n\n")
                
                f.write("        # 创建自定义样式\n")
                f.write("        style = ttk.Style()\n\n")
                
                f.write("        # 尝试设置主题\n")
                f.write("        try:\n")
                f.write("            style.theme_use(\"clam\")\n")
                f.write("        except:\n")
                f.write("            pass\n\n")
                
                f.write("        # 配置颜色\n")
                f.write("        style.configure(\".\", \n")
                f.write("            background=theme.BACKGROUND_COLOR,\n")
                f.write("            foreground=theme.FOREGROUND_COLOR,\n")
                f.write("            font=(theme.FONT_FAMILY, theme.FONT_SIZE)\n")
                f.write("        )\n\n")
                
                f.write("        # 配置Frame样式\n")
                f.write("        style.configure(\"TFrame\", background=theme.BACKGROUND_COLOR)\n\n")
                
                f.write("        # 配置Label样式\n")
                f.write("        style.configure(\"TLabel\",\n")
                f.write("            background=theme.BACKGROUND_COLOR,\n")
                f.write("            foreground=theme.FOREGROUND_COLOR,\n")
                f.write("            font=(theme.FONT_FAMILY, theme.FONT_SIZE)\n")
                f.write("        )\n\n")
                
                f.write("        # 配置Button样式\n")
                f.write("        style.configure(\"TButton\",\n")
                f.write("            background=theme.BUTTON_BACKGROUND,\n")
                f.write("            foreground=theme.BUTTON_FOREGROUND,\n")
                f.write("            font=(theme.FONT_FAMILY, theme.FONT_SIZE)\n")
                f.write("        )\n\n")
                
                f.write("        # 配置强调按钮样式\n")
                f.write("        style.configure(\"Accent.TButton\",\n")
                f.write("            background=theme.ACCENT_COLOR,\n")
                f.write("            foreground=theme.BUTTON_FOREGROUND,\n")
                f.write("            font=(theme.FONT_FAMILY, theme.FONT_SIZE, \"bold\")\n")
                f.write("        )\n\n")
                
                f.write("        # 配置Entry样式\n")
                f.write("        style.configure(\"TEntry\",\n")
                f.write("            fieldbackground=\"white\",\n")
                f.write("            foreground=theme.FOREGROUND_COLOR,\n")
                f.write("            bordercolor=theme.BORDER_COLOR\n")
                f.write("        )\n\n")
                
                f.write("        # 配置Progressbar样式\n")
                f.write("        style.configure(\"Horizontal.TProgressbar\",\n")
                f.write("            background=theme.PROGRESS_BAR_COLOR,\n")
                f.write("            troughcolor=\"white\",\n")
                f.write("            bordercolor=theme.BORDER_COLOR\n")
                f.write("        )\n\n")
                
                f.write("        # 配置LabelFrame样式\n")
                f.write("        style.configure(\"TLabelframe\",\n")
                f.write("            background=theme.BACKGROUND_COLOR,\n")
                f.write("            foreground=theme.FOREGROUND_COLOR,\n")
                f.write("            bordercolor=theme.BORDER_COLOR\n")
                f.write("        )\n\n")
                
                f.write("        style.configure(\"TLabelframe.Label\",\n")
                f.write("            background=theme.BACKGROUND_COLOR,\n")
                f.write("            foreground=theme.HEADER_COLOR,\n")
                f.write("            font=(theme.FONT_FAMILY, theme.FONT_SIZE, \"bold\")\n")
                f.write("        )\n\n")
                
                f.write("        # 配置Combobox样式\n")
                f.write("        style.configure(\"TCombobox\",\n")
                f.write("            background=\"white\",\n")
                f.write("            foreground=theme.FOREGROUND_COLOR\n")
                f.write("        )\n\n")
                
                f.write("        # 配置Radiobutton样式\n")
                f.write("        style.configure(\"TRadiobutton\",\n")
                f.write("            background=theme.BACKGROUND_COLOR,\n")
                f.write("            foreground=theme.FOREGROUND_COLOR,\n")
                f.write("            font=(theme.FONT_FAMILY, theme.FONT_SIZE)\n")
                f.write("        )\n\n")
                
                f.write("        # 配置Checkbutton样式\n")
                f.write("        style.configure(\"TCheckbutton\",\n")
                f.write("            background=theme.BACKGROUND_COLOR,\n")
                f.write("            foreground=theme.FOREGROUND_COLOR,\n")
                f.write("            font=(theme.FONT_FAMILY, theme.FONT_SIZE)\n")
                f.write("        )\n\n")
                
                f.write("        # 设置自定义Logo\n")
                f.write("        if theme.LOGO_PATH and os.path.exists(theme.LOGO_PATH):\n")
                f.write("            try:\n")
                f.write("                root.iconphoto(True, tk.PhotoImage(file=theme.LOGO_PATH))\n")
                f.write("            except Exception as e:\n")
                f.write("                print(f\"加载Logo出错: {str(e)}\")\n")
                
                f.write("        return True\n")
                f.write("    except Exception as e:\n")
                f.write("        print(f\"应用主题出错: {str(e)}\")\n")
                f.write("        return False\n\n")
                
                f.write("if __name__ == \"__main__\":\n")
                f.write("    # 测试主题\n")
                f.write("    root = tk.Tk()\n")
                f.write("    success = apply_theme(root)\n")
                f.write("    if success:\n")
                f.write("        label = ttk.Label(root, text=\"主题应用成功！\")\n")
                f.write("        label.pack(padx=20, pady=20)\n")
                f.write("        button = ttk.Button(root, text=\"确定\", command=root.destroy)\n")
                f.write("        button.pack(pady=10)\n")
                f.write("        root.mainloop()\n")
                f.write("    else:\n")
                f.write("        messagebox.showerror(\"错误\", \"应用主题失败\")\n")
            
            # 创建修改后的PDF转换工具文件
            modified_converter_file = "pdf_converter_themed.py"
            
            with open("pdf_converter.py", 'r', encoding='utf-8') as src, \
                 open(modified_converter_file, 'w', encoding='utf-8') as dst:
                
                # 读取原始文件内容
                content = src.read()
                
                # 在import部分后添加主题导入
                import_section = "import threading\nimport fitz  # PyMuPDF\nfrom PIL import Image\nimport docx\nimport io\nimport time"
                theme_import = "import threading\nimport fitz  # PyMuPDF\nfrom PIL import Image\nimport docx\nimport io\nimport time\n\n# 导入主题应用器\ntry:\n    from apply_theme import apply_theme\nexcept ImportError:\n    def apply_theme(root):\n        return False"
                
                content = content.replace(import_section, theme_import)
                
                # 在setup_ui方法前添加主题应用
                setup_ui_section = "    def setup_ui(self):"
                theme_setup = "    def setup_ui(self):\n        # 应用自定义主题\n        theme_applied = apply_theme(self.root)\n        if theme_applied:\n            self.log(\"已应用自定义主题\")\n"
                
                content = content.replace(setup_ui_section, theme_setup)
                
                # 写入修改后的内容
                dst.write(content)
            
            messagebox.showinfo("成功", f"已生成主题配置文件: {theme_config_file}\n已生成主题应用器: {theme_applier_file}\n已生成主题版PDF转换工具: {modified_converter_file}\n\n请使用 {modified_converter_file} 来运行带自定义主题的PDF转换工具。")
            
        except Exception as e:
            messagebox.showerror("错误", f"应用主题失败: {str(e)}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = UICustomizer()
    app.run()