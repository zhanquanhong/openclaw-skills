#!/usr/bin/env python3
"""
高性能图片压缩库
支持格式：bmp, gif, heic, jfif, jpeg, jpg, livp, png, ppm, tif, tiff, webp
特点：高并发、低内存占用、可设置目标大小
"""

import io
import os
from pathlib import Path
from typing import Optional, Tuple, BinaryIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 核心图像处理库
from PIL import Image, ImageOps

# Pillow 版本兼容
try:
    from PIL.Image import Resampling
    RESAMPLING_LANCZOS = Resampling.LANCZOS
except ImportError:
    # Pillow < 9.0
    RESAMPLING_LANCZOS = Image.LANCZOS

# HEIC/HEIF 支持
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

# LIVP 支持 (Apple Live Photo)
try:
    import piexif
except ImportError:
    piexif = None


class ImageCompressor:
    """高性能图片压缩器"""
    
    # 支持的格式映射
    SUPPORTED_FORMATS = {
        'bmp': 'BMP',
        'gif': 'GIF',
        'heic': 'HEIF',
        'heif': 'HEIF',
        'jfif': 'JPEG',
        'jpeg': 'JPEG',
        'jpg': 'JPEG',
        'livp': 'JPEG',  # LIVP 本质是 ZIP 包含 JPEG+MOV
        'png': 'PNG',
        'ppm': 'PPM',
        'tif': 'TIFF',
        'tiff': 'TIFF',
        'webp': 'WEBP',
    }
    
    # 格式对应的最优压缩参数
    FORMAT_PARAMS = {
        'JPEG': {'quality': 85, 'optimize': True, 'progressive': True},
        'PNG': {'optimize': True, 'compress_level': 6},
        'WEBP': {'quality': 80, 'method': 6},
        'GIF': {'optimize': True, 'save_all': True},
        'TIFF': {'compression': 'tiff_lzw'},
        'BMP': {},
        'PPM': {},
        'HEIF': {'quality': 80},
    }
    
    def __init__(self, max_workers: int = 4, max_memory_mb: int = 256):
        """
        初始化压缩器
        
        Args:
            max_workers: 最大并发工作线程数
            max_memory_mb: 单个图像处理的最大内存 (MB)
        """
        self.max_workers = max_workers
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
    
    def get_format(self, file_path: str) -> Optional[str]:
        """获取文件格式"""
        ext = Path(file_path).suffix.lower().lstrip('.')
        return self.SUPPORTED_FORMATS.get(ext)
    
    def _open_image(self, source: BinaryIO) -> Image.Image:
        """安全打开图片，限制内存使用"""
        # 读取数据
        data = source.read()
        
        # 检查内存限制
        if len(data) > self.max_memory_bytes:
            raise ValueError(f"图片大小超过限制 ({len(data)} > {self.max_memory_bytes})")
        
        # 打开图片
        img = Image.open(io.BytesIO(data))
        
        # 转换为 RGB (处理 RGBA, P 等模式)
        if img.mode in ('RGBA', 'LA', 'P'):
            # PNG 带透明通道时保留
            if img.format == 'PNG':
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        return img
    
    def _compress_image(
        self,
        img: Image.Image,
        format: str,
        quality: int = 85,
        max_size: Optional[int] = None,
        resize: Optional[Tuple[int, int]] = None,
    ) -> bytes:
        """
        压缩图片
        
        Args:
            img: PIL Image 对象
            format: 输出格式
            quality: 压缩质量 (1-100)
            max_size: 目标文件大小 (字节)，如指定则迭代压缩
            resize: 目标尺寸 (宽，高)
        
        Returns:
            压缩后的字节数据
        """
        # 调整尺寸
        if resize:
            img = img.resize(resize, RESAMPLING_LANCZOS)
        
        # 获取格式参数
        params = self.FORMAT_PARAMS.get(format, {}).copy()
        
        # 根据格式设置质量参数
        if format in ('JPEG', 'WEBP', 'HEIF'):
            params['quality'] = quality
        elif format == 'PNG':
            params['compress_level'] = min(9, max(1, quality // 12))
        
        # 输出到字节流
        output = io.BytesIO()
        
        # 保存参数
        save_kwargs = {**params}
        
        # 特殊格式处理
        if format == 'JPEG':
            save_kwargs['format'] = 'JPEG'
            save_kwargs['subsampling'] = 2
        elif format == 'WEBP':
            save_kwargs['format'] = 'WEBP'
        elif format == 'PNG':
            save_kwargs['format'] = 'PNG'
            if img.mode == 'RGBA':
                save_kwargs['transparency'] = img.getchannel('A')
        elif format == 'GIF':
            save_kwargs['format'] = 'GIF'
            img = img.convert('P', palette=Image.ADAPTIVE, colors=256)
        elif format == 'TIFF':
            save_kwargs['format'] = 'TIFF'
        elif format == 'HEIF':
            if pillow_heif:
                save_kwargs['format'] = 'HEIF'
            else:
                # 降级为 JPEG
                format = 'JPEG'
                save_kwargs = {'format': 'JPEG', 'quality': quality}
        
        # 首次压缩
        img.save(output, **save_kwargs)
        result = output.getvalue()
        
        # 如果有目标大小限制，迭代压缩
        if max_size and len(result) > max_size:
            result = self._iterative_compress(
                img, format, max_size, save_kwargs
            )
        
        return result
    
    def _iterative_compress(
        self,
        img: Image.Image,
        format: str,
        max_size: int,
        base_params: dict,
        max_iterations: int = 10
    ) -> bytes:
        """迭代压缩直到达到目标大小"""
        quality = base_params.get('quality', 85)
        min_quality = 5
        
        for i in range(max_iterations):
            output = io.BytesIO()
            params = base_params.copy()
            params['quality'] = quality
            
            img.save(output, **params)
            result = output.getvalue()
            
            if len(result) <= max_size or quality <= min_quality:
                return result
            
            # 降低质量重试
            quality = max(min_quality, quality - 8)
        
        # 如果还是太大，尝试缩小尺寸
        width, height = img.size
        scale = 0.8
        new_size = (int(width * scale), int(height * scale))
        
        if min(new_size) < 100:
            return result  # 太小了，返回当前最佳
        
        resized = img.resize(new_size, RESAMPLING_LANCZOS)
        return self._iterative_compress(resized, format, max_size, base_params, max_iterations)
    
    def compress_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        quality: int = 85,
        max_size: Optional[int] = None,
        resize: Optional[Tuple[int, int]] = None,
        output_format: Optional[str] = None,
    ) -> dict:
        """
        压缩单个文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径 (None 则返回 bytes)
            quality: 压缩质量 (1-100)
            max_size: 目标文件大小 (字节)
            resize: 目标尺寸 (宽，高)
            output_format: 输出格式 (None 则保持原格式)
        
        Returns:
            压缩结果信息
        """
        import time
        start_time = time.time()
        
        with open(input_path, 'rb') as f:
            original_size = os.path.getsize(input_path)
            img = self._open_image(f)
        
        # 确定输出格式
        if output_format:
            fmt = output_format.upper()
        else:
            fmt = img.format or self.get_format(input_path) or 'JPEG'
        
        # 压缩
        compressed = self._compress_image(img, fmt, quality, max_size, resize)
        
        # 保存或返回
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(compressed)
        
        elapsed = time.time() - start_time
        
        return {
            'success': True,
            'input_path': input_path,
            'output_path': output_path,
            'original_size': original_size,
            'compressed_size': len(compressed),
            'compression_ratio': f"{len(compressed) / original_size * 100:.1f}%",
            'format': fmt,
            'dimensions': img.size,
            'elapsed_ms': round(elapsed * 1000, 2),
        }
    
    def compress_batch(
        self,
        files: list,
        output_dir: Optional[str] = None,
        quality: int = 85,
        max_size: Optional[int] = None,
    ) -> list:
        """
        批量压缩图片
        
        Args:
            files: 输入文件路径列表
            output_dir: 输出目录 (None 则返回 bytes 列表)
            quality: 压缩质量
            max_size: 目标文件大小
        
        Returns:
            压缩结果列表
        """
        results = []
        futures = {}
        
        for input_path in files:
            if output_dir:
                output_path = str(Path(output_dir) / Path(input_path).name)
            else:
                output_path = None
            
            future = self._executor.submit(
                self.compress_file,
                input_path,
                output_path,
                quality,
                max_size,
            )
            futures[future] = input_path
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    'success': False,
                    'input_path': futures[future],
                    'error': str(e),
                })
        
        return results
    
    def compress_bytes(
        self,
        data: bytes,
        filename: str,
        quality: int = 85,
        max_size: Optional[int] = None,
        resize: Optional[Tuple[int, int]] = None,
    ) -> bytes:
        """
        压缩字节数据
        
        Args:
            data: 图片字节数据
            filename: 文件名 (用于检测格式)
            quality: 压缩质量
            max_size: 目标文件大小
            resize: 目标尺寸
        
        Returns:
            压缩后的字节数据
        """
        img = self._open_image(io.BytesIO(data))
        fmt = img.format or self.get_format(filename) or 'JPEG'
        return self._compress_image(img, fmt, quality, max_size, resize)
    
    def shutdown(self):
        """关闭线程池"""
        self._executor.shutdown(wait=True)


# 单例模式
_compressor_instance = None
_compressor_lock = threading.Lock()


def get_compressor(max_workers: int = 4) -> ImageCompressor:
    """获取压缩器单例"""
    global _compressor_instance
    if _compressor_instance is None:
        with _compressor_lock:
            if _compressor_instance is None:
                _compressor_instance = ImageCompressor(max_workers=max_workers)
    return _compressor_instance


if __name__ == '__main__':
    # 测试
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python image_compressor.py <input_file> [output_file] [quality] [max_size_kb]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    quality = int(sys.argv[3]) if len(sys.argv) > 3 else 85
    max_size = int(sys.argv[4]) * 1024 if len(sys.argv) > 4 else None
    
    compressor = get_compressor()
    result = compressor.compress_file(input_file, output_file, quality, max_size)
    print(f"压缩完成：{result}")
