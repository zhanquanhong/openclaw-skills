#!/usr/bin/env python3
"""
图片压缩 API 服务 - Python 3.6 兼容版
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

from image_compressor import get_compressor, ImageCompressor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Image Compressor API", version="1.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
executor = ThreadPoolExecutor(max_workers=4)
compressor = None


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


def run_compressor(data, filename, quality, max_size, resize):
    import time
    start = time.time()
    try:
        result = compressor.compress_bytes(data, filename, quality, max_size, resize)
        return {'success': True, 'data': result, 'original_size': len(data), 'compressed_size': len(result), 'elapsed_ms': (time.time()-start)*1000}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed_ms': (time.time()-start)*1000}


@app.get("/")
async def root():
    return {"service": "Image Compressor API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0", "supported_formats": list(ImageCompressor.SUPPORTED_FORMATS.keys())}


@app.post("/compress")
async def compress(
    file: UploadFile = File(...),
    quality: int = Form(default=85),
    max_size_kb: int = Form(default=None),
    output_format: str = Form(default=None)
):
    ext = Path(file.filename).suffix.lower().lstrip('.')
    if ext not in ImageCompressor.SUPPORTED_FORMATS:
        raise HTTPException(400, f"不支持的格式：{ext}")
    
    data = await file.read()
    max_size = max_size_kb * 1024 if max_size_kb else None
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, run_compressor, data, file.filename, quality, max_size, None)
    
    if not result['success']:
        raise HTTPException(500, result['error'])
    
    fmt = (output_format or ext).upper()
    content_types = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp', 'GIF': 'image/gif'}
    
    return Response(
        content=result['data'],
        media_type=content_types.get(fmt, 'application/octet-stream'),
        headers={
            'X-Original-Size': str(result['original_size']),
            'X-Compressed-Size': str(result['compressed_size']),
            'X-Compression-Ratio': f"{result['compressed_size']/result['original_size']*100:.1f}%",
            'X-Elapsed-Ms': f"{result['elapsed_ms']:.2f}"
        }
    )


@app.post("/compress/json", response_model=CompressResponse)
async def compress_json(
    file: UploadFile = File(...),
    quality: int = Form(default=85),
    max_size_kb: int = Form(default=None),
    max_width: int = Form(default=None),
    max_height: int = Form(default=None),
    output_format: str = Form(default=None)
):
    ext = Path(file.filename).suffix.lower().lstrip('.')
    if ext not in ImageCompressor.SUPPORTED_FORMATS:
        return CompressResponse(success=False, error=f"不支持的格式：{ext}")
    
    data = await file.read()
    max_size = max_size_kb * 1024 if max_size_kb else None
    resize = (max_width, max_height) if max_width or max_height else None
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, run_compressor, data, file.filename, quality, max_size, resize)
    
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
        format=(output_format or ext).upper(),
        width=img.size[0],
        height=img.size[1],
        elapsed_ms=result['elapsed_ms']
    )


@app.post("/compress/url", response_model=CompressResponse)
async def compress_url(
    url: str = Form(...),
    quality: int = Form(default=85),
    max_size_kb: int = Form(default=None),
    output_format: str = Form(default=None)
):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            data = resp.content
    except Exception as e:
        return CompressResponse(success=False, error=f"下载失败：{e}")
    
    filename = Path(url).name or "image.jpg"
    max_size = max_size_kb * 1024 if max_size_kb else None
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, run_compressor, data, filename, quality, max_size, None)
    
    if not result['success']:
        return CompressResponse(success=False, error=result.get('error'))
    
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    
    return CompressResponse(
        success=True,
        file_id=str(uuid.uuid4()),
        original_size=len(data),
        compressed_size=result['compressed_size'],
        compression_ratio=f"{result['compressed_size']/len(data)*100:.1f}%",
        format=(output_format or Path(filename).suffix.lstrip('.')).upper(),
        width=img.size[0],
        height=img.size[1],
        elapsed_ms=result['elapsed_ms']
    )


@app.post("/compress/base64", response_model=CompressResponse)
async def compress_base64(
    image_base64: str = Form(...),
    filename: str = Form(default="image.jpg"),
    quality: int = Form(default=85),
    max_size_kb: int = Form(default=None),
    output_format: str = Form(default=None)
):
    import base64
    import re
    
    try:
        b64_data = image_base64
        if ',' in b64_data:
            match = re.search(r'data:image/([^;]+);base64,', b64_data)
            if match and not output_format:
                output_format = match.group(1).upper()
            b64_data = b64_data.split(',', 1)[1]
        
        data = base64.b64decode(b64_data)
    except Exception as e:
        return CompressResponse(success=False, error=f"Base64 解码失败：{e}")
    
    max_size = max_size_kb * 1024 if max_size_kb else None
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, run_compressor, data, filename, quality, max_size, None)
    
    if not result['success']:
        return CompressResponse(success=False, error=result.get('error'))
    
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    
    return CompressResponse(
        success=True,
        file_id=str(uuid.uuid4()),
        original_size=len(data),
        compressed_size=result['compressed_size'],
        compression_ratio=f"{result['compressed_size']/len(data)*100:.1f}%",
        format=(output_format or Path(filename).suffix.lstrip('.')).upper(),
        width=img.size[0],
        height=img.size[1],
        elapsed_ms=result['elapsed_ms']
    )


@app.on_event("startup")
async def startup():
    global compressor
    compressor = get_compressor(max_workers=4)
    logger.info("Image Compressor started")


@app.on_event("shutdown")
async def shutdown():
    if compressor:
        compressor.shutdown()
    executor.shutdown(wait=True)


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8765, workers=1)
