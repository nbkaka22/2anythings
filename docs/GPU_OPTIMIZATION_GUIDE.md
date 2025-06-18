# GPU加速优化指南

本指南详细说明了如何为2anythings转换器启用GPU加速，以显著提升转换性能。

## 系统要求

### 硬件要求
- NVIDIA GPU（支持CUDA 11.0+）
- 至少4GB显存（推荐8GB+）
- 足够的系统内存（推荐16GB+）

### 软件要求
- NVIDIA CUDA驱动程序
- 支持CUDA的PyTorch版本
- 相关AI库的GPU版本

## GPU支持状态

### ✅ 已支持GPU加速的转换器

#### 1. PDF高清化转换器 (pdf_upscale)
- **Real-ESRGAN**: 自动检测GPU，支持CUDA加速
- **Waifu2x**: 配置为优先使用GPU (gpuid=0)
- **性能提升**: GPU模式下速度提升5-10倍

#### 2. PDF转DOCX OCR转换器 (pdf_to_docx_ocr)
- **EasyOCR**: 新增GPU支持，自动检测并优先使用GPU
- **性能提升**: GPU模式下OCR识别速度提升2-3倍

### ⚪ 无需GPU加速的转换器

#### 3. PDF转PPT转换器 (pdf_to_ppt)
- 主要进行格式转换，无AI计算需求
- 性能瓶颈在I/O操作，GPU加速效果有限

#### 4. PDF转DOCX转换器 (pdf_to_docx)
- 使用pdf2docx库进行格式转换
- 无AI计算需求，GPU加速不适用

#### 5. Word转PPT转换器 (word_to_ppt)
- 纯文档格式转换
- 无AI计算需求，GPU加速不适用

## GPU配置详情

### PDF高清化转换器

```python
# Real-ESRGAN GPU配置
upscaler = RealESRGANer(
    scale=scale,
    model_path=model_path,
    model=model,
    tile=400,
    tile_pad=10,
    pre_pad=0,
    half=True if torch.cuda.is_available() else False  # 自动GPU检测
)

# Waifu2x GPU配置
waifu2x = Waifu2x(
    gpuid=0,  # 使用GPU 0，-1为CPU模式
    tta_mode=False,
    num_threads=1,
    noise=1,
    scale=2,
    tilesize=0,
    model="models-cunet"
)
```

### PDF转DOCX OCR转换器

```python
# EasyOCR GPU配置（新增）
def _check_gpu_support(self) -> bool:
    """检查GPU支持情况"""
    try:
        import torch
        if torch.cuda.is_available():
            return True
        return False
    except ImportError:
        return False

# 自动GPU检测和回退
gpu_available = self._check_gpu_support()
self._ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=gpu_available)
```

## 性能对比

### PDF高清化转换器
| 处理模式 | 单张图片处理时间 | 内存使用 | 适用场景 |
|---------|----------------|----------|----------|
| CPU模式 | 10-30秒 | 2-4GB | 小批量处理 |
| GPU模式 | 1-3秒 | 4-8GB | 大批量处理 |

### PDF转DOCX OCR转换器
| 处理模式 | 单页OCR时间 | 内存使用 | 准确率 |
|---------|-------------|----------|--------|
| CPU模式 | 3-8秒 | 1-2GB | 95%+ |
| GPU模式 | 1-3秒 | 2-4GB | 95%+ |

## 安装GPU支持

### 1. 安装CUDA驱动
```bash
# 检查NVIDIA驱动
nvidia-smi

# 下载并安装CUDA Toolkit
# 访问: https://developer.nvidia.com/cuda-downloads
```

### 2. 安装支持CUDA的PyTorch
```bash
# 卸载CPU版本PyTorch
pip uninstall torch torchvision torchaudio

# 安装GPU版本PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 3. 验证GPU支持
```python
import torch
print(f"CUDA可用: {torch.cuda.is_available()}")
print(f"GPU数量: {torch.cuda.device_count()}")
print(f"当前GPU: {torch.cuda.get_device_name(0)}")
```

## 使用建议

### 最佳实践
1. **批量处理**: GPU加速在批量处理时效果最明显
2. **内存管理**: 确保GPU内存足够，避免OOM错误
3. **温度监控**: 长时间GPU使用时注意散热
4. **电源管理**: 高性能GPU需要足够的电源供应

### 故障排除

#### GPU不可用
```bash
# 检查CUDA安装
nvcc --version

# 检查PyTorch CUDA支持
python -c "import torch; print(torch.cuda.is_available())"

# 检查GPU内存
nvidia-smi
```

#### 内存不足
- 减少批处理大小
- 降低图像分辨率
- 使用CPU模式作为备选

#### 性能不佳
- 检查GPU利用率
- 确认使用了正确的CUDA版本
- 更新GPU驱动程序

## 监控和调试

### GPU使用监控
```bash
# 实时监控GPU使用情况
watch -n 1 nvidia-smi

# 查看GPU进程
nvidia-smi pmon
```

### 性能分析
```python
# 在代码中添加性能监控
import time
import torch

start_time = time.time()
# 执行GPU操作
end_time = time.time()

print(f"处理时间: {end_time - start_time:.2f}秒")
print(f"GPU内存使用: {torch.cuda.memory_allocated() / 1024**2:.1f}MB")
```

## 未来优化计划

### 短期目标
- [ ] 为所有AI相关转换器添加GPU支持检测
- [ ] 实现动态GPU内存管理
- [ ] 添加GPU性能监控界面

### 长期目标
- [ ] 支持多GPU并行处理
- [ ] 实现GPU集群分布式处理
- [ ] 添加AMD GPU支持（ROCm）

## 总结

通过启用GPU加速，2anythings转换器的性能可以得到显著提升：

- **PDF高清化**: 处理速度提升5-10倍
- **OCR识别**: 处理速度提升2-3倍
- **整体体验**: 大幅减少等待时间

建议用户根据自己的硬件配置和使用需求，选择合适的GPU加速方案。对于大批量文档处理，GPU加速是必不可少的性能优化手段。