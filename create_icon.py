import os
import sys
from PIL import Image, ImageDraw
import struct

def create_simple_ico(ico_path, sizes=[16, 32, 48, 64, 128, 256]):
    """
    创建一个简单的PDF转换工具图标
    
    参数:
        ico_path: 输出的ICO文件路径
        sizes: 图标尺寸列表
    """
    try:
        # 创建不同尺寸的图像
        images = []
        for size in sizes:
            # 创建新图像
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # 绘制现代化的背景渐变圆形
            margin = max(2, size // 10)
            # 创建渐变效果的背景
            for i in range(margin, max(margin + 1, size - margin)):
                if i < size - i:  # 确保坐标有效
                    alpha = int(255 * (1 - (i - margin) / max(1, size - 2 * margin) * 0.3))
                    color = (45, 85, 255, alpha)  # 深蓝到浅蓝的渐变
                    draw.ellipse([i, i, size-i, size-i], fill=color)
            
            # 绘制主背景圆形
            draw.ellipse([margin, margin, size-margin, size-margin], 
                        fill=(52, 120, 246, 255))  # 现代蓝色背景
            
            # 绘制阴影效果
            shadow_offset = max(1, size // 32)
            draw.ellipse([margin + shadow_offset, margin + shadow_offset, 
                         size-margin + shadow_offset, size-margin + shadow_offset], 
                        fill=(0, 0, 0, 30))  # 半透明阴影
            
            # 重新绘制主圆形（覆盖阴影）
            draw.ellipse([margin, margin, size-margin, size-margin], 
                        fill=(52, 120, 246, 255))
            
            # 绘制更精美的文档图标
            doc_margin = max(4, int(size // 3.5))
            doc_width = max(8, size - 2 * doc_margin)
            doc_height = max(10, int(doc_width * 1.2))  # 更高的文档比例
            doc_y = max(doc_margin, (size - doc_height) // 2 + size // 20)  # 稍微向下偏移
            
            # 确保文档不会超出边界
            if doc_y + doc_height > size - doc_margin:
                doc_height = size - doc_margin - doc_y
            if doc_height < 8:
                doc_height = 8
            
            # 文档阴影
            shadow_offset = max(1, size // 40)
            draw.rectangle([doc_margin + shadow_offset, doc_y + shadow_offset, 
                           doc_margin + doc_width + shadow_offset, doc_y + doc_height + shadow_offset], 
                          fill=(0, 0, 0, 40))  # 文档阴影
            
            # 主文档背景
            draw.rectangle([doc_margin, doc_y, doc_margin + doc_width, doc_y + doc_height], 
                          fill=(255, 255, 255, 255))  # 白色文档
            
            # 文档边框
            border_width = max(1, size // 64)
            draw.rectangle([doc_margin, doc_y, doc_margin + doc_width, doc_y + doc_height], 
                          outline=(220, 220, 220, 255), width=border_width)
            
            # 绘制文档折角效果
            corner_size = max(3, size // 16)
            corner_x = doc_margin + doc_width - corner_size
            corner_y = doc_y
            # 折角三角形
            draw.polygon([(corner_x, corner_y), 
                         (doc_margin + doc_width, corner_y), 
                         (doc_margin + doc_width, corner_y + corner_size)], 
                        fill=(240, 240, 240, 255))
            draw.line([(corner_x, corner_y), (doc_margin + doc_width, corner_y + corner_size)], 
                     fill=(200, 200, 200, 255), width=1)
            
            # 绘制文档内容线条
            if size >= 24:
                line_spacing = max(2, size // 20)
                line_start_y = doc_y + doc_height // 4
                line_margin = doc_margin + size // 20
                line_width = doc_width - size // 10
                
                for i in range(3):
                    y = line_start_y + i * line_spacing
                    if y < doc_y + doc_height - line_spacing:
                        draw.rectangle([line_margin, y, line_margin + line_width * (0.8 if i == 2 else 1), 
                                       y + 1], fill=(180, 180, 180, 255))
            
            # 绘制更美观的PDF文字
            if size >= 24:
                try:
                    # 计算文字位置和大小
                    text_size = max(6, size // 6)
                    text = "PDF"
                    
                    # 使用更好的字体渲染（如果可能）
                    try:
                        from PIL import ImageFont
                        # 尝试使用系统字体
                        font = ImageFont.truetype("arial.ttf", text_size)
                    except:
                        font = None
                    
                    # 计算文字位置（居中在文档底部）
                    if font:
                        bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                    else:
                        text_width = len(text) * text_size * 0.6
                        text_height = text_size
                    
                    text_x = doc_margin + (doc_width - text_width) // 2
                    text_y = doc_y + doc_height - text_height - size // 15
                    
                    # 文字阴影
                    shadow_offset = max(1, size // 80)
                    draw.text((text_x + shadow_offset, text_y + shadow_offset), text, 
                             fill=(0, 0, 0, 60), font=font)
                    
                    # 主文字（使用渐变红色）
                    draw.text((text_x, text_y), text, 
                             fill=(220, 38, 38, 255), font=font)  # 现代红色
                except Exception as e:
                    # 如果字体加载失败，使用简单文字
                    text_y = doc_y + doc_height * 0.7
                    draw.text((doc_margin + 2, text_y), "PDF", 
                             fill=(220, 38, 38, 255))
            
            images.append(img)
        
        # 手动创建ICO文件
        with open(ico_path, 'wb') as f:
            # ICO文件头
            f.write(struct.pack('<HHH', 0, 1, len(images)))  # 保留字段, 类型(1=ICO), 图像数量
            
            # 计算数据偏移
            offset = 6 + len(images) * 16  # 头部 + 目录条目
            
            # 写入目录条目
            for img in images:
                width = img.width if img.width < 256 else 0
                height = img.height if img.height < 256 else 0
                
                # 将图像转换为PNG格式的字节数据
                import io
                png_data = io.BytesIO()
                img.save(png_data, format='PNG')
                png_bytes = png_data.getvalue()
                
                # 写入目录条目
                f.write(struct.pack('<BBBBHHII', 
                    width, height, 0, 0,  # 宽度, 高度, 颜色数, 保留
                    1, 32,  # 颜色平面, 位深度
                    len(png_bytes),  # 数据大小
                    offset  # 数据偏移
                ))
                offset += len(png_bytes)
            
            # 写入图像数据
            for img in images:
                png_data = io.BytesIO()
                img.save(png_data, format='PNG')
                f.write(png_data.getvalue())
        
        # 验证文件是否为ICO格式
        with open(ico_path, 'rb') as f:
            header = f.read(6)
            if len(header) >= 6 and header[:2] == b'\x00\x00' and header[2:4] == b'\x01\x00':
                print(f"验证: 文件是有效的ICO格式")
            else:
                print(f"警告: 生成的文件可能不是有效的ICO格式")
        
        print(f"成功创建图标: {ico_path}")
        return True
    
    except Exception as e:
        print(f"创建图标时出错: {str(e)}")
        return False

def main():
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 设置ICO文件路径
    ico_path = os.path.join(script_dir, "icon.ico")
    
    # 创建图标
    success = create_simple_ico(ico_path)
    
    if success:
        print("图标创建成功！")
    else:
        print("图标创建失败。")
        sys.exit(1)

if __name__ == "__main__":
    main()