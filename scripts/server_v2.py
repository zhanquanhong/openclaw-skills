#!/usr/bin/env python3
"""
图片压缩 API 服务 - 增强版
集成 Google 风格 AI 压缩算法
"""

import os
import io
import uuid
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from image_compressor import get_compressor as get_traditional_compressor
from google_compressor import get_google_compressor, GoogleStyleCompressor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Image Compressor API", version="2.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
executor = ThreadPoolExecutor(max_workers=8)
traditional_compressor = None
google_compressor = None


class CompressResponse(BaseModel):
    success: bool
    file_id: str = None
    original_size: int = None
    compressed_size: int = None
    compression_ratio: str = None
    format: str = None
    width: int = None
    height: int = None
    elapsed_ms: float = None
    error: str = None
    algorithm: str = None
    quality_mode: str = None


class CompressRequest(BaseModel):
    quality: int = 85
    max_size_kb: int = None
    max_width: int = None
    max_height: int = None
    output_format: str = None
    algorithm: str = 'traditional'  # 'traditional' or 'google'
    quality_mode: str = 'balanced'  # 'fast', 'balanced', 'quality', 'google'


def run_traditional_compress(data, filename, quality, max_size, resize):
    import time
    start = time.time()
    try:
        result = traditional_compressor.compress_bytes(data, filename, quality, max_size, resize)
        return {
            'success': True,
            'data': result,
            'original_size': len(data),
            'compressed_size': len(result),
            'elapsed_ms': (time.time()-start)*1000,
            'algorithm': 'traditional'
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed_ms': (time.time()-start)*1000}


def run_google_compress(data, filename, quality, max_size, quality_mode):
    import time
    from PIL import Image
    start = time.time()
    try:
        img = Image.open(io.BytesIO(data))
        result = google_compressor.compress(
            img,
            target_size_kb=max_size,
            output_format='auto',
            quality_mode=quality_mode
        )
        return {
            'success': True,
            'data': result['data'],
            'original_size': len(data),
            'compressed_size': result['compressed_size'],
            'elapsed_ms': (time.time()-start)*1000,
            'algorithm': 'google',
            'quality_mode': quality_mode,
            'features': result.get('features', {})
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed_ms': (time.time()-start)*1000}


@app.get("/")
async def root():
    return {
        "service": "Image Compressor API",
        "version": "2.0.0",
        "algorithms": ["traditional", "google"],
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "algorithms": {
            "traditional": "Standard JPEG/PNG/WebP compression",
            "google": "AI-enhanced compression with perceptual optimization"
        }
    }


@app.post("/compress", response_model=CompressResponse)
async def compress(
    file: UploadFile = File(...),
    quality: int = Form(default=85),
    max_size_kb: int = Form(default=None),
    algorithm: str = Form(default='traditional'),
    quality_mode: str = Form(default='balanced')
):
    """
    压缩图片
    
    - **file**: 图片文件
    - **quality**: 压缩质量 1-100
    - **max_size_kb**: 目标文件大小 (KB)
    - **algorithm**: 压缩算法 ('traditional' 或 'google')
    - **quality_mode**: 质量模式 ('fast', 'balanced', 'quality', 'google')
    """
    ext = Path(file.filename).suffix.lower().lstrip('.')
    
    data = await file.read()
    max_size = max_size_kb * 1024 if max_size_kb else None
    
    loop = asyncio.get_event_loop()
    
    if algorithm == 'google':
        result = await loop.run_in_executor(
            executor,
            run_google_compress,
            data, file.filename, quality, max_size, quality_mode
        )
    else:
        result = await loop.run_in_executor(
            executor,
            run_traditional_compress,
            data, file.filename, quality, max_size, None
        )
    
    if not result['success']:
        return CompressResponse(success=False, error=result.get('error'))
    
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    
    return CompressResponse(
        success=True,
        file_id=str(uuid.uuid4()),
        original_size=result['original_size'],
        compressed_size=result['compressed_size'],
        compression_ratio=f"{result['compressed_size']/result['original_size']*100:.1f}%",
        format=Path(file.filename).suffix.upper().lstrip('.'),
        width=img.size[0],
        height=img.size[1],
        elapsed_ms=result['elapsed_ms'],
        algorithm=result.get('algorithm', 'traditional'),
        quality_mode=quality_mode if algorithm == 'google' else None
    )


@app.post("/compress/compare", response_model=dict)
async def compress_compare(
    file: UploadFile = File(...),
    quality: int = Form(default=85),
    max_size_kb: int = Form(default=None)
):
    """
    对比传统算法和 Google 算法的压缩效果
    
    返回两种算法的压缩结果对比
    """
    data = await file.read()
    max_size = max_size_kb * 1024 if max_size_kb else None
    
    loop = asyncio.get_event_loop()
    
    # 传统算法
    traditional_result = await loop.run_in_executor(
        executor,
        run_traditional_compress,
        data, file.filename, quality, max_size, None
    )
    
    # Google 算法
    google_result = await loop.run_in_executor(
        executor,
        run_google_compress,
        data, file.filename, quality, max_size, 'google'
    )
    
    return {
        'original_size': len(data),
        'traditional': {
            'compressed_size': traditional_result.get('compressed_size'),
            'ratio': f"{traditional_result.get('compressed_size', 0)/len(data)*100:.1f}%" if traditional_result['success'] else None,
            'elapsed_ms': traditional_result.get('elapsed_ms'),
            'success': traditional_result['success'],
        },
        'google': {
            'compressed_size': google_result.get('compressed_size'),
            'ratio': f"{google_result.get('compressed_size', 0)/len(data)*100:.1f}%" if google_result['success'] else None,
            'elapsed_ms': google_result.get('elapsed_ms'),
            'success': google_result['success'],
            'quality_mode': 'google',
        },
        'comparison': {
            'size_diff': (traditional_result.get('compressed_size', 0) - google_result.get('compressed_size', 0)) if traditional_result['success'] and google_result['success'] else None,
            'speed_diff': (google_result.get('elapsed_ms', 0) - traditional_result.get('elapsed_ms', 0)) if traditional_result['success'] and google_result['success'] else None,
        } if traditional_result['success'] and google_result['success'] else None
    }


@app.on_event("startup")
async def startup():
    global traditional_compressor, google_compressor
    traditional_compressor = get_traditional_compressor(max_workers=4)
    google_compressor = get_google_compressor(quality_mode='balanced')
    logger.info("Image Compressor v2.0 started with Google-style compression")


@app.on_event("shutdown")
async def shutdown():
    if traditional_compressor:
        traditional_compressor.shutdown()
    if google_compressor:
        google_compressor.shutdown()
    executor.shutdown(wait=True)


if __name__ == "__main__":
    uvicorn.run("server_v2:app", host="0.0.0.0", port=8766, workers=2)
