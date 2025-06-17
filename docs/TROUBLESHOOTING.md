# 故障排除指南

## 常见问题及解决方案

### 1. 依赖相关问题

#### 问题：缺少依赖包

**错误信息：**
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案：**
1. 运行自动安装脚本：
   ```bash
   python scripts/setup.py
   ```

2. 手动安装缺失的包：
   ```bash
   pip install package_name
   ```

3. 安装所有依赖：
   ```bash
   pip install -r requirements.txt
   ```

#### 问题：版本冲突

**错误信息：**
```
VersionConflict: package_name x.x.x is installed but package_name>=y.y.y is required
```

**解决方案：**
1. 升级包到所需版本：
   ```bash
   pip install --upgrade package_name>=y.y.y
   ```

2. 使用虚拟环境避免冲突：
   ```bash
   python -m venv pdf_converter_env
   source pdf_converter_env/bin/activate  # Linux/Mac
   pdf_converter_env\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

### 2. 插件相关问题

#### 问题：插件加载失败

**错误信息：**
```
[ERROR] 加载插件失败: attempted relative import with no known parent package
```

**解决方案：**
1. 检查插件文件中的导入语句，确保使用绝对导入：
   ```python
   # 错误的相对导入
   from .converter_interface import ConverterInterface
   
   # 正确的绝对导入
   from converters.converter_interface import ConverterInterface
   ```

2. 确保插件文件名以 `_converter.py` 结尾

3. 验证插件类正确继承了 `ConverterInterface`

#### 问题：插件目录不存在

**错误信息：**
```
[WARNING] 插件目录不存在: path/to/directory
```

**解决方案：**
1. 检查插件管理器配置
2. 确保 `converters` 目录存在
3. 验证路径配置正确

### 3. 转换相关问题

#### 问题：PDF 文件无法打开

**错误信息：**
```
[ERROR] PDF文件验证失败: cannot open file
```

**解决方案：**
1. 检查文件是否存在
2. 验证文件是否为有效的 PDF 格式
3. 确保文件没有被其他程序占用
4. 检查文件权限

#### 问题：输出文件创建失败

**错误信息：**
```
[ERROR] 无法创建输出文件: Permission denied
```

**解决方案：**
1. 检查输出目录是否存在
2. 验证对输出目录的写权限
3. 确保输出文件没有被其他程序占用
4. 尝试使用不同的输出路径

#### 问题：转换质量差

**可能原因：**
- DPI 设置过低
- 源文件质量问题
- 转换参数不当

**解决方案：**
1. 提高 DPI 设置：
   ```python
   converter.convert(input_path, output_path, dpi=300)
   ```

2. 调整图像格式：
   ```python
   converter.convert(input_path, output_path, image_format='png')
   ```

3. 启用文本提取：
   ```python
   converter.convert(input_path, output_path, include_text=True)
   ```

### 4. GUI 相关问题

#### 问题：界面无法启动

**错误信息：**
```
TclError: no display name and no $DISPLAY environment variable
```

**解决方案：**
1. 在 Linux 服务器上，确保 X11 转发已启用
2. 安装图形界面支持
3. 使用命令行模式（如果可用）

#### 问题：图标显示异常

**解决方案：**
1. 检查 `assets/icon.ico` 文件是否存在
2. 验证图标文件格式
3. 确保 PIL 库正确安装

### 5. 性能相关问题

#### 问题：转换速度慢

**优化建议：**
1. 降低 DPI 设置（如果质量要求不高）
2. 使用 JPEG 格式而非 PNG（文件更小）
3. 分批处理大文件
4. 增加系统内存

#### 问题：内存使用过高

**解决方案：**
1. 及时清理临时文件
2. 分页处理大文档
3. 优化图像压缩设置
4. 监控内存使用情况

### 6. 日志和调试

#### 启用详细日志

在代码中添加：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 查看日志文件

日志通常输出到控制台，可以重定向到文件：
```bash
python pdf_converter.py > converter.log 2>&1
```

#### 调试模式

在开发环境中启用调试：
```python
logger.setLevel(logging.DEBUG)
```

### 7. 系统兼容性

#### Windows 特定问题

1. **路径分隔符问题：**
   使用 `os.path.join()` 或 `pathlib.Path`

2. **编码问题：**
   确保文件以 UTF-8 编码保存

3. **权限问题：**
   以管理员身份运行（如果需要）

#### Linux/Mac 特定问题

1. **依赖安装：**
   ```bash
   sudo apt-get install python3-tk  # Ubuntu/Debian
   brew install python-tk           # macOS
   ```

2. **权限问题：**
   ```bash
   chmod +x install_dependencies.sh
   ```

### 8. 获取帮助

如果以上解决方案都无法解决问题：

1. **检查日志：** 查看详细的错误信息
2. **搜索文档：** 查阅 API 文档和开发指南
3. **提交问题：** 在项目仓库中创建 Issue
4. **社区支持：** 寻求社区帮助

### 9. 预防措施

1. **定期更新依赖：**
   ```bash
   pip list --outdated
   pip install --upgrade package_name
   ```

2. **备份重要文件：**
   在转换前备份原始文件

3. **测试新功能：**
   在小文件上测试新的转换器或参数

4. **监控系统资源：**
   确保有足够的磁盘空间和内存

### 10. 联系支持

如果遇到无法解决的问题，请提供以下信息：

- 操作系统和版本
- Python 版本
- 完整的错误信息
- 重现步骤
- 相关的日志输出
- 输入文件的特征（大小、格式等）