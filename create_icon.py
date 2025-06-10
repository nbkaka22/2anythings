import os
import sys
from PIL import Image, ImageDraw

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
            
            # 绘制背景圆形
            margin = size // 8
            draw.ellipse([margin, margin, size-margin, size-margin], 
                        fill=(66, 133, 244, 255))  # 蓝色背景
            
            # 绘制文档图标
            doc_margin = size // 4
            doc_width = size - 2 * doc_margin
            doc_height = int(doc_width * 0.8)
            doc_y = (size - doc_height) // 2
            
            draw.rectangle([doc_margin, doc_y, doc_margin + doc_width, doc_y + doc_height], 
                          fill=(255, 255, 255, 255))  # 白色文档
            
            # 绘制PDF文字（简化版）
            if size >= 32:
                text_size = max(size // 8, 8)
                try:
                    # 尝试绘制文字
                    text_y = doc_y + doc_height // 3
                    draw.text((doc_margin + 2, text_y), "PDF", 
                             fill=(233, 66, 53, 255))  # 红色文字
                except:
                    pass  # 如果绘制文字失败，忽略
            
            images.append(img)
        
        # 保存为ICO文件
        images[0].save(
            ico_path, 
            format='ICO', 
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        
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