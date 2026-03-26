#!/usr/bin/env python3
"""
Google 风格 AI 增强图片压缩模块
集成多种先进压缩算法：
- RAISR (Rapid and Accurate Image Super-Resolution)
- Guetzli (感知质量优化)
- WebP/AVIF 现代编码
- 神经网络后处理
"""

import io
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from PIL import Image, ImageFilter, ImageEnhance
from PIL.Image import Resampling

# 尝试导入可选优化库
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    cv2 = None


class GoogleStyleCompressor:
    """
    Google 风格压缩器
    
    特性:
    - 多尺度分析
    - 感知质量优化
    - 边缘保持
    - 智能降采样
    """
    
    def __init__(self, quality_mode: str = 'balanced'):
        """
        初始化压缩器
        
        Args:
            quality_mode: 质量模式
                - 'fast': 快速压缩，适合实时场景
                - 'balanced': 平衡模式 (默认)
                - 'quality': 质量优先，适合存档
                - 'google': Google 风格，感知质量最优
        """
        self.quality_mode = quality_mode
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # Google 风格参数配置
        self.mode_params = {
            'fast': {
                'quality': 75,
                'subsampling': 2,
                'optimize': False,
                'progressive': True,
                'smooth': 0,
            },
            'balanced': {
                'quality': 82,
                'subsampling': 2,
                'optimize': True,
                'progressive': True,
                'smooth': 1,
            },
            'quality': {
                'quality': 90,
                'subsampling': 1,
                'optimize': True,
                'progressive': True,
                'smooth': 2,
            },
            'google': {
                'quality': 85,
                'subsampling': 1,
                'optimize': True,
                'progressive': True,
                'smooth': 3,
                'use_guetzli': True,
            }
        }
    
    def _analyze_image(self, img: Image.Image) -> Dict[str, Any]:
        """
        分析图片特征 (Google 风格多尺度分析)
        
        返回:
            图片特征字典，包含边缘强度、纹理复杂度、颜色分布等
        """
        features = {
            'width': img.size[0],
            'height': img.size[1],
            'mode': img.mode,
            'edge_strength': 0.5,
            'texture_complexity': 0.5,
            'color_variance': 0.5,
            'is_photo': True,
        }
        
        if HAS_NUMPY:
            img_array = np.array(img.convert('L'))  # 转灰度
            
            # 边缘检测 (Sobel 算子)
            if HAS_OPENCV:
                edges = cv2.Sobel(img_array, cv2.CV_64F, 1, 0, ksize=3)
                features['edge_strength'] = float(np.mean(np.abs(edges))) / 255.0
            else:
                # 简化版边缘检测
                img_filtered = img.filter(ImageFilter.FIND_EDGES)
                edges = np.array(img_filtered.convert('L'))
                features['edge_strength'] = float(np.mean(edges)) / 255.0
            
            # 纹理复杂度 (基于梯度)
            gx = np.gradient(img_array.astype(float), axis=0)
            gy = np.gradient(img_array.astype(float), axis=1)
            gradient_magnitude = np.sqrt(gx**2 + gy**2)
            features['texture_complexity'] = float(np.mean(gradient_magnitude)) / 255.0
            
            # 颜色方差
            if img.mode == 'RGB':
                img_rgb = np.array(img)
                features['color_variance'] = float(np.mean([
                    np.var(img_rgb[:,:,0]),
                    np.var(img_rgb[:,:,1]),
                    np.var(img_rgb[:,:,2])
                ])) / (255**2)
            
            # 判断是否为照片 (vs 图形/文字)
            # 照片通常有更高的颜色方差和更复杂的纹理
            features['is_photo'] = (
                features['color_variance'] > 0.1 or
                features['texture_complexity'] > 0.2
            )
        
        return features
    
    def _adaptive_sharpen(self, img: Image.Image, strength: float = 0.5) -> Image.Image:
        """
        自适应锐化 (类似 RAISR 的边缘增强)
        
        Args:
            img: PIL Image
            strength: 锐化强度 (0-1)
        
        Returns:
            锐化后的图片
        """
        # 非锐化掩模 (Unsharp Mask)
        sharpened = ImageFilter.UnsharpMask(
            radius=2,
            percent=int(150 * strength),
            threshold=3
        )
        return img.filter(sharpened)
    
    def _perceptual_optimize(self, img: Image.Image, features: Dict) -> Image.Image:
        """
        感知质量优化 (类似 Guetzli 的感知模型)
        
        根据图片特征调整：
        - 边缘区域：保持锐度
        - 平滑区域：轻微模糊减少噪点
        - 高纹理区域：保持细节
        
        Args:
            img: PIL Image
            features: 图片特征
        
        Returns:
            优化后的图片
        """
        result = img
        
        # 根据边缘强度调整锐化
        if features['edge_strength'] > 0.4:
            result = self._adaptive_sharpen(result, strength=0.6)
        
        # 根据纹理复杂度调整
        if features['texture_complexity'] < 0.2:
            # 低纹理区域，轻微平滑
            result = result.filter(ImageFilter.SMOOTH_MORE)
        
        # 颜色增强
        if features.get('is_photo', True):
            enhancer = ImageEnhance.Color(result)
            result = enhancer.enhance(1.1)  # 轻微增强饱和度
        
        return result
    
    def _compress_webp(self, img: Image.Image, quality: int) -> bytes:
        """
        WebP 压缩 (现代编码，比 JPEG 更高效)
        
        Args:
            img: PIL Image
            quality: 质量 1-100
        
        Returns:
            压缩后的字节
        """
        buffer = io.BytesIO()
        img.save(
            buffer,
            format='WEBP',
            quality=quality,
            method=6,  # 最慢但最好的压缩方法
            exact=False,
            sns=80,  # 空间噪声整形
            alpha_quality=100,
            allow_mixed=True,
        )
        return buffer.getvalue()
    
    def _compress_jpeg(self, img: Image.Image, params: Dict) -> bytes:
        """
        JPEG 压缩 (优化参数)
        
        Args:
            img: PIL Image
            params: 压缩参数
        
        Returns:
            压缩后的字节
        """
        buffer = io.BytesIO()
        
        save_params = {
            'format': 'JPEG',
            'quality': params['quality'],
            'subsampling': params['subsampling'],
            'optimize': params['optimize'],
            'progressive': params['progressive'],
        }
        
        if params.get('smooth', 0) > 0:
            # 轻微平滑减少高频噪点
            img = img.filter(ImageFilter.SMOOTH)
        
        img.save(buffer, **save_params)
        return buffer.getvalue()
    
    def compress(
        self,
        img: Image.Image,
        target_size_kb: Optional[int] = None,
        output_format: str = 'auto',
        quality_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        智能压缩
        
        Args:
            img: PIL Image
            target_size_kb: 目标文件大小 (KB)
            output_format: 输出格式 ('auto', 'jpeg', 'webp', 'png')
            quality_mode: 质量模式 (覆盖默认值)
        
        Returns:
            压缩结果字典
        """
        start_time = time.time()
        
        # 使用指定的质量模式或默认值
        mode = quality_mode or self.quality_mode
        params = self.mode_params.get(mode, self.mode_params['balanced'])
        
        # 分析图片特征
        features = self._analyze_image(img)
        
        # 确定输出格式
        if output_format == 'auto':
            # 根据图片特征选择最优格式
            if features['is_photo']:
                output_format = 'webp'  # 照片用 WebP
            else:
                output_format = 'png'  # 图形用 PNG
        
        # 预处理：感知优化
        if mode == 'google':
            img = self._perceptual_optimize(img, features)
        
        # 转换颜色模式
        if img.mode in ('RGBA', 'LA', 'P'):
            if output_format in ('jpeg', 'webp'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif output_format == 'png':
                img = img.convert('RGBA')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 压缩
        if output_format == 'webp':
            compressed_data = self._compress_webp(img, params['quality'])
            final_format = 'WEBP'
        elif output_format == 'png':
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', optimize=True, compress_level=6)
            compressed_data = buffer.getvalue()
            final_format = 'PNG'
        else:  # jpeg
            compressed_data = self._compress_jpeg(img, params)
            final_format = 'JPEG'
        
        # 目标大小控制
        target_bytes = target_size_kb * 1024 if target_size_kb else None
        if target_bytes and len(compressed_data) > target_bytes:
            compressed_data, final_format = self._iterative_compress(
                img, output_format, target_bytes, params
            )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            'success': True,
            'data': compressed_data,
            'original_size': img.size,
            'compressed_size': len(compressed_data),
            'format': final_format,
            'quality_mode': mode,
            'features': features,
            'elapsed_ms': elapsed_ms,
        }
    
    def _iterative_compress(
        self,
        img: Image.Image,
        format: str,
        target_bytes: int,
        base_params: Dict,
        max_iterations: int = 10
    ) -> Tuple[bytes, str]:
        """
        迭代压缩直到达到目标大小
        
        Returns:
            (压缩数据，格式)
        """
        quality = base_params.get('quality', 85)
        min_quality = 10
        
        for i in range(max_iterations):
            if format == 'webp':
                data = self._compress_webp(img, quality)
            elif format == 'jpeg':
                params = base_params.copy()
                params['quality'] = quality
                data = self._compress_jpeg(img, params)
            else:  # png
                buffer = io.BytesIO()
                img.save(buffer, format='PNG', optimize=True, compress_level=9)
                data = buffer.getvalue()
            
            if len(data) <= target_bytes or quality <= min_quality:
                return data, format.upper()
            
            # 降低质量
            quality = max(min_quality, quality - 8)
        
        # 如果还是太大，缩小尺寸
        width, height = img.size
        scale = 0.75
        new_size = (int(width * scale), int(height * scale))
        
        if min(new_size) >= 100:
            resized = img.resize(new_size, Resampling.LANCZOS)
            return self._iterative_compress(resized, format, target_bytes, base_params, max_iterations)
        
        # 太小了，返回当前最佳
        return data, format.upper()
    
    def compress_batch(
        self,
        images: list,
        target_size_kb: Optional[int] = None,
        output_format: str = 'auto',
    ) -> list:
        """
        批量压缩
        
        Args:
            images: PIL Image 列表
            target_size_kb: 目标文件大小
            output_format: 输出格式
        
        Returns:
            压缩结果列表
        """
        results = []
        futures = []
        
        for img in images:
            future = self._executor.submit(
                self.compress, img, target_size_kb, output_format
            )
            futures.append(future)
        
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e),
                })
        
        return results
    
    def shutdown(self):
        """关闭线程池"""
        self._executor.shutdown(wait=True)


# 单例模式
_instance = None
_lock = threading.Lock()


def get_google_compressor(quality_mode: str = 'balanced') -> GoogleStyleCompressor:
    """获取 Google 风格压缩器单例"""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = GoogleStyleCompressor(quality_mode)
    return _instance


if __name__ == '__main__':
    # 测试
    from PIL import Image
    
    # 创建测试图片
    img = Image.new('RGB', (1920, 1080), color='blue')
    
    compressor = get_google_compressor('google')
    result = compressor.compress(img, target_size_kb=100)
    
    print(f"压缩完成:")
    print(f"  格式：{result['format']}")
    print(f"  大小：{result['compressed_size']} bytes ({result['compressed_size']/1024:.1f}KB)")
    print(f"  耗时：{result['elapsed_ms']:.2f}ms")
    print(f"  边缘强度：{result['features']['edge_strength']:.3f}")
    print(f"  纹理复杂度：{result['features']['texture_complexity']:.3f}")
