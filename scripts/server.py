#!/usr/bin/env python3
"""
图片压缩 API 服务
高性能、高并发、低内存占用
支持 Java 后端直接调用
"""

import os
import sys
import io
import uuid
import tempfile
import asyncio
from pathlib import Path
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor
import logging

# FastAPI 和相关组件
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# 导入压缩器
from image_compressor import get_compressor, ImageCompressor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Image Compressor API",
    description="高性能图片压缩服务，支持多种格式和目标大小控制",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件 (允许 Java 后端调用)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 线程池 (用于 CPU 密集型压缩任务)
executor = ThreadPoolExecutor(max_workers=8)

# 压缩器实例
compressor: Optional[ImageCompressor] = None


# ============ 数据模型 ============

class CompressRequest(BaseModel):
    """压缩请求参数"""
    quality: int = Field(default=85, ge=1, le=100, description="压缩质量 (1-100)")
    max_size_kb: Optional[int] = Field(default=None, ge=1, description="目标文件大小 (KB)")
    max_width: Optional[int] = Field(default=None, ge=1, description="最大宽度")
    max_height: Optional[int] = Field(default=None, ge=1, description="最大高度")
    output_format: Optional[str] = Field(default=None, description="输出格式 (JPEG, PNG, WEBP 等)")
    keep_metadata: bool = Field(default=False, description="保留元数据")


class CompressResponse(BaseModel):
    """压缩响应"""
    success: bool
    file_id: Optional[str] = None
    original_size: Optional[int] = None
    compressed_size: Optional[int] = None
    compression_ratio: Optional[str] = None
    format: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None


class BatchCompressRequest(BaseModel):
    """批量压缩请求"""
    quality: int = Field(default=85, ge=1, le=100)
    max_size_kb: Optional[int] = Field(default=None, ge=1)
    output_format: Optional[str] = Field(default=None)


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    supported_formats: List[str]
    max_workers: int


class UrlCompressRequest(BaseModel):
    """URL 压缩请求"""
    url: str = Field(..., description="图片 URL 地址")
    quality: int = Field(default=85, ge=1, le=100, description="压缩质量 (1-100)")
    max_size_kb: Optional[int] = Field(default=None, ge=1, description="目标文件大小 (KB)")
    max_width: Optional[int] = Field(default=None, ge=1, description="最大宽度")
    max_height: Optional[int] = Field(default=None, ge=1, description="最大高度")
    output_format: Optional[str] = Field(default=None, description="输出格式")


class Base64CompressRequest(BaseModel):
    """Base64 压缩请求"""
    image_base64: str = Field(..., description="图片 Base64 数据 (可带或不带 data:image/jpeg;base64, 前缀)")
    filename: str = Field(default="image.jpg", description="文件名 (用于推断格式)")
    quality: int = Field(default=85, ge=1, le=100, description="压缩质量 (1-100)")
    max_size_kb: Optional[int] = Field(default=None, ge=1, description="目标文件大小 (KB)")
    max_width: Optional[int] = Field(default=None, ge=1, description="最大宽度")
    max_height: Optional[int] = Field(default=None, ge=1, description="最大高度")
    output_format: Optional[str] = Field(default=None, description="输出格式")


# ============ 工具函数 ============

def run_compressor_sync(
    data: bytes,
    filename: str,
    quality: int,
    max_size: Optional[int],
    resize: Optional[tuple],
    output_format: Optional[str],
) -> dict:
    """在线程池中运行压缩任务"""
    import time
    start_time = time.time()
    
    try:
        result = compressor.compress_bytes(
            data=data,
            filename=filename,
            quality=quality,
            max_size=max_size,
            resize=resize,
        )
        
        elapsed = (time.time() - start_time) * 1000
        
        return {
            'success': True,
            'data': result,
            'original_size': len(data),
            'compressed_size': len(result),
            'elapsed_ms': elapsed,
        }
    except Exception as e:
        logger.error(f"Compression error: {e}")
        return {
            'success': False,
            'error': str(e),
            'elapsed_ms': (time.time() - start_time) * 1000,
        }


# ============ API 端点 ============

@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "service": "Image Compressor API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        supported_formats=list(ImageCompressor.SUPPORTED_FORMATS.keys()),
        max_workers=compressor.max_workers if compressor else 0,
    )


@app.post("/compress", tags=["Compression"])
async def compress_image(
    file: UploadFile = File(..., description="要压缩的图片文件"),
    quality: int = Form(default=85, ge=1, le=100, description="压缩质量 (1-100)"),
    max_size_kb: Optional[int] = Form(default=None, ge=1, description="目标文件大小 (KB)"),
    max_width: Optional[int] = Form(default=None, ge=1, description="最大宽度"),
    max_height: Optional[int] = Form(default=None, ge=1, description="最大高度"),
    output_format: Optional[str] = Form(default=None, description="输出格式"),
):
    """
    压缩单张图片
    
    - **file**: 图片文件
    - **quality**: 压缩质量 1-100
    - **max_size_kb**: 目标文件大小 (KB)，会自动迭代压缩直到达到
    - **max_width/max_height**: 最大尺寸限制
    - **output_format**: 输出格式 (可选，默认保持原格式)
    """
    # 验证文件格式
    ext = Path(file.filename).suffix.lower().lstrip('.')
    if ext not in ImageCompressor.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式：{ext}. 支持的格式：{list(ImageCompressor.SUPPORTED_FORMATS.keys())}"
        )
    
    # 读取文件
    try:
        data = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败：{e}")
    
    # 准备参数
    max_size = max_size_kb * 1024 if max_size_kb else None
    resize = None
    if max_width or max_height:
        resize = (max_width or 99999, max_height or 99999)
    
    # 在线程池中执行压缩
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        run_compressor_sync,
        data,
        file.filename,
        quality,
        max_size,
        resize,
        output_format,
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error', '压缩失败'))
    
    # 确定输出格式和 content-type
    out_format = output_format.upper() if output_format else ext.upper()
    content_types = {
        'JPEG': 'image/jpeg',
        'JPG': 'image/jpeg',
        'PNG': 'image/png',
        'WEBP': 'image/webp',
        'GIF': 'image/gif',
        'TIFF': 'image/tiff',
        'BMP': 'image/bmp',
        'HEIF': 'image/heif',
    }
    content_type = content_types.get(out_format, 'application/octet-stream')
    
    # 生成输出文件名
    output_filename = f"compressed_{Path(file.filename).stem}.{out_format.lower()}"
    
    return Response(
        content=result['data'],
        media_type=content_type,
        headers={
            'Content-Disposition': f'attachment; filename="{output_filename}"',
            'X-Original-Size': str(result['original_size']),
            'X-Compressed-Size': str(result['compressed_size']),
            'X-Compression-Ratio': f"{result['compressed_size'] / result['original_size'] * 100:.1f}%",
            'X-Elapsed-Ms': str(round(result['elapsed_ms'], 2)),
        }
    )


@app.post("/compress/json", response_model=CompressResponse, tags=["Compression"])
async def compress_image_json(
    file: UploadFile = File(...),
    quality: int = Form(default=85),
    max_size_kb: int = Form(default=None),
    max_width: int = Form(default=None),
    max_height: int = Form(default=None),
    output_format: str = Form(default=None),
):
    # 构建请求对象
    request_obj = CompressRequest(
        quality=quality,
        max_size_kb=max_size_kb,
        max_width=max_width,
        max_height=max_height,
        output_format=output_format,
    )
    """
    压缩图片 (JSON 参数模式)
    
    适合需要复杂参数的场景，使用 JSON 格式传递参数
    """
    ext = Path(file.filename).suffix.lower().lstrip('.')
    if ext not in ImageCompressor.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式：{ext}"
        )
    
    data = await file.read()
    max_size = request_obj.max_size_kb * 1024 if request_obj.max_size_kb else None
    
    resize = None
    if request_obj.max_width or request_obj.max_height:
        resize = (request_obj.max_width or 99999, request_obj.max_height or 99999)
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        run_compressor_sync,
        data,
        file.filename,
        request_obj.quality,
        max_size,
        resize,
        request_obj.output_format,
    )
    
    if not result['success']:
        return CompressResponse(
            success=False,
            error=result.get('error', '压缩失败'),
            elapsed_ms=result.get('elapsed_ms'),
        )
    
    # 获取图片尺寸
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    width, height = img.size
    
    return CompressResponse(
        success=True,
        file_id=str(uuid.uuid4()),
        original_size=result['original_size'],
        compressed_size=result['compressed_size'],
        compression_ratio=f"{result['compressed_size'] / result['original_size'] * 100:.1f}%",
        format=request_obj.output_format or ext.upper(),
        width=width,
        height=height,
        elapsed_ms=result['elapsed_ms'],
    )


@app.post("/compress/batch", tags=["Compression"])
async def compress_batch(
    files: List[UploadFile] = File(..., description="图片文件列表"),
    quality: int = Form(default=85, ge=1, le=100),
    max_size_kb: Optional[int] = Form(default=None, ge=1),
    output_format: Optional[str] = Form(default=None),
):
    """
    批量压缩多张图片
    
    返回压缩后的文件包 (ZIP) 和统计信息
    """
    import zipfile
    
    results = []
    compressed_files = []
    
    for file in files:
        ext = Path(file.filename).suffix.lower().lstrip('.')
        if ext not in ImageCompressor.SUPPORTED_FORMATS:
            results.append({
                'filename': file.filename,
                'success': False,
                'error': f'不支持的格式：{ext}',
            })
            continue
        
        data = await file.read()
        max_size = max_size_kb * 1024 if max_size_kb else None
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            run_compressor_sync,
            data,
            file.filename,
            quality,
            max_size,
            None,
            output_format,
        )
        
        if result['success']:
            out_ext = output_format.lower() if output_format else ext
            out_filename = f"compressed_{Path(file.filename).stem}.{out_ext}"
            compressed_files.append((out_filename, result['data']))
            results.append({
                'filename': file.filename,
                'success': True,
                'original_size': result['original_size'],
                'compressed_size': result['compressed_size'],
                'ratio': f"{result['compressed_size'] / result['original_size'] * 100:.1f}%",
            })
        else:
            results.append({
                'filename': file.filename,
                'success': False,
                'error': result.get('error'),
            })
    
    # 创建 ZIP 文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, data in compressed_files:
            zf.writestr(filename, data)
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type='application/zip',
        headers={
            'Content-Disposition': 'attachment; filename="compressed_images.zip"',
            'X-Results': str(results),
        }
    )


@app.post("/compress/url", response_model=CompressResponse, tags=["Compression"])
async def compress_from_url(
    url: str = Form(..., description="图片 URL"),
    quality: int = Form(default=85, ge=1, le=100),
    max_size_kb: Optional[int] = Form(default=None, ge=1),
    output_format: Optional[str] = Form(default=None),
):
    """
    从 URL 下载并压缩图片 (Form 表单模式)
    
    适合处理远程图片
    """
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载图片失败：{e}")
    
    # 从 URL 或 Content-Type 推断文件名
    from urllib.parse import urlparse
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "image.jpg"
    
    max_size = max_size_kb * 1024 if max_size_kb else None
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        run_compressor_sync,
        data,
        filename,
        quality,
        max_size,
        None,
        output_format,
    )
    
    if not result['success']:
        return CompressResponse(
            success=False,
            error=result.get('error', '压缩失败'),
            elapsed_ms=result.get('elapsed_ms'),
        )
    
    return CompressResponse(
        success=True,
        file_id=str(uuid.uuid4()),
        original_size=len(data),
        compressed_size=result['compressed_size'],
        compression_ratio=f"{result['compressed_size'] / len(data) * 100:.1f}%",
        format=output_format or Path(filename).suffix.upper().lstrip('.'),
        elapsed_ms=result['elapsed_ms'],
    )


@app.post("/compress/url/json", response_model=CompressResponse, tags=["Compression"])
async def compress_from_url_json(request: UrlCompressRequest):
    """
    从 URL 下载并压缩图片 (JSON 模式)
    
    适合 Java 后端通过 JSON 请求体调用
    """
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(request.url)
            response.raise_for_status()
            data = response.content
    except Exception as e:
        return CompressResponse(
            success=False,
            error=f"下载图片失败：{e}",
        )
    
    # 从 URL 推断文件名
    from urllib.parse import urlparse
    parsed = urlparse(request.url)
    filename = Path(parsed.path).name or "image.jpg"
    
    max_size = request.max_size_kb * 1024 if request.max_size_kb else None
    resize = None
    if request.max_width or request.max_height:
        resize = (request.max_width or 99999, request.max_height or 99999)
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        run_compressor_sync,
        data,
        filename,
        request.quality,
        max_size,
        resize,
        request.output_format,
    )
    
    if not result['success']:
        return CompressResponse(
            success=False,
            error=result.get('error', '压缩失败'),
            elapsed_ms=result.get('elapsed_ms'),
        )
    
    # 获取图片尺寸
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    width, height = img.size
    
    return CompressResponse(
        success=True,
        file_id=str(uuid.uuid4()),
        original_size=len(data),
        compressed_size=result['compressed_size'],
        compression_ratio=f"{result['compressed_size'] / len(data) * 100:.1f}%",
        format=request.output_format or Path(filename).suffix.upper().lstrip('.'),
        width=width,
        height=height,
        elapsed_ms=result['elapsed_ms'],
    )


@app.post("/compress/base64", response_model=CompressResponse, tags=["Compression"])
async def compress_from_base64(request: Base64CompressRequest):
    """
    压缩 Base64 编码的图片
    
    支持带或不带 data:image/jpeg;base64, 前缀的 Base64 数据
    """
    import base64
    import re
    
    try:
        # 移除 Base64 前缀 (如果有)
        base64_data = request.image_base64
        if ',' in base64_data:
            # 移除 data:image/jpeg;base64, 前缀
            match = re.search(r'data:image/([^;]+);base64,', base64_data)
            if match:
                # 从前缀推断格式
                if not request.output_format:
                    format_map = {
                        'jpeg': 'JPEG',
                        'jpg': 'JPEG',
                        'png': 'PNG',
                        'gif': 'GIF',
                        'webp': 'WEBP',
                        'bmp': 'BMP',
                        'tiff': 'TIFF',
                    }
                    request.output_format = format_map.get(match.group(1).lower())
                base64_data = base64_data.split(',', 1)[1]
        
        # 解码 Base64
        image_data = base64.b64decode(base64_data)
        
    except Exception as e:
        return CompressResponse(
            success=False,
            error=f"Base64 解码失败：{e}",
        )
    
    max_size = request.max_size_kb * 1024 if request.max_size_kb else None
    resize = None
    if request.max_width or request.max_height:
        resize = (request.max_width or 99999, request.max_height or 99999)
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        run_compressor_sync,
        image_data,
        request.filename,
        request.quality,
        max_size,
        resize,
        request.output_format,
    )
    
    if not result['success']:
        return CompressResponse(
            success=False,
            error=result.get('error', '压缩失败'),
            elapsed_ms=result.get('elapsed_ms'),
        )
    
    # 获取图片尺寸
    from PIL import Image
    img = Image.open(io.BytesIO(image_data))
    width, height = img.size
    
    return CompressResponse(
        success=True,
        file_id=str(uuid.uuid4()),
        original_size=len(image_data),
        compressed_size=result['compressed_size'],
        compression_ratio=f"{result['compressed_size'] / len(image_data) * 100:.1f}%",
        format=request.output_format or Path(request.filename).suffix.upper().lstrip('.'),
        width=width,
        height=height,
        elapsed_ms=result['elapsed_ms'],
    )


@app.on_event("startup")
async def startup_event():
    """启动时初始化压缩器"""
    global compressor
    max_workers = int(os.getenv('MAX_WORKERS', '8'))
    compressor = get_compressor(max_workers=max_workers)
    logger.info(f"Image Compressor started with {max_workers} workers")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    if compressor:
        compressor.shutdown()
    executor.shutdown(wait=True)


# ============ 主程序 ============

if __name__ == "__main__":
    # 从环境变量读取配置
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8765'))
    workers = int(os.getenv('UVICORN_WORKERS', '4'))
    
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║           Image Compressor API Server                    ║
    ╠══════════════════════════════════════════════════════════╣
    ║  Host: {host:<48} ║
    ║  Port: {port:<48} ║
    ║  Workers: {workers:<45} ║
    ║  Docs: http://{host}:{port}/docs{' ' * 36}║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
    )
