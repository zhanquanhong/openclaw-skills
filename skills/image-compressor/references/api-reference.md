# API 参考文档

## 端点概览

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/` | 服务信息 |
| GET | `/health` | 健康检查 |
| POST | `/compress` | 压缩单张图片 (multipart) |
| POST | `/compress/json` | 压缩单张图片 (JSON 参数) |
| POST | `/compress/batch` | 批量压缩 |
| POST | `/compress/url` | 从 URL 压缩 (Form) |
| POST | `/compress/url/json` | 从 URL 压缩 (JSON) |
| POST | `/compress/base64` | 压缩 Base64 图片 |

---

## GET /

返回服务基本信息。

**响应:**
```json
{
  "service": "Image Compressor API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

## GET /health

健康检查端点。

**响应:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "supported_formats": ["bmp", "gif", "heic", "jfif", "jpeg", "jpg", "livp", "png", "ppm", "tif", "tiff", "webp"],
  "max_workers": 8
}
```

---

## POST /compress

压缩单张图片。

**Content-Type:** `multipart/form-data`

**参数:**

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `file` | File | 是 | - | 图片文件 |
| `quality` | Integer | 否 | 85 | 压缩质量 (1-100) |
| `max_size_kb` | Integer | 否 | null | 目标文件大小 (KB) |
| `max_width` | Integer | 否 | null | 最大宽度 |
| `max_height` | Integer | 否 | null | 最大高度 |
| `output_format` | String | 否 | null | 输出格式 |

**成功响应:**

返回压缩后的图片数据，Content-Type 根据输出格式确定。

**响应头:**
```
Content-Disposition: attachment; filename="compressed_image.jpg"
Content-Type: image/jpeg
X-Original-Size: 2048576
X-Compressed-Size: 512000
X-Compression-Ratio: 25.0%
X-Elapsed-Ms: 156.23
```

**错误响应:**
```json
{
  "detail": "不支持的格式：xxx. 支持的格式：[...]"
}
```

**HTTP 状态码:**
- `200`: 成功
- `400`: 不支持的格式
- `500`: 压缩失败

---

## POST /compress/json

压缩单张图片 (JSON 参数模式)。

**Content-Type:** `multipart/form-data`

**参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `file` | File | 是 | 图片文件 |
| `request` | CompressRequest | 是 | JSON 格式的请求参数 |

**CompressRequest 结构:**
```json
{
  "quality": 85,
  "max_size_kb": 500,
  "max_width": 1920,
  "max_height": 1080,
  "output_format": "WEBP",
  "keep_metadata": false
}
```

**响应:**
```json
{
  "success": true,
  "file_id": "uuid-string",
  "original_size": 2048576,
  "compressed_size": 512000,
  "compression_ratio": "25.0%",
  "format": "WEBP",
  "width": 1920,
  "height": 1080,
  "elapsed_ms": 156.23
}
```

---

## POST /compress/batch

批量压缩多张图片。

**Content-Type:** `multipart/form-data`

**参数:**

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `files` | File[] | 是 | - | 图片文件列表 |
| `quality` | Integer | 否 | 85 | 压缩质量 |
| `max_size_kb` | Integer | 否 | null | 目标文件大小 |
| `output_format` | String | 否 | null | 输出格式 |

**响应:**

返回 ZIP 文件，包含所有压缩后的图片。

**响应头:**
```
Content-Disposition: attachment; filename="compressed_images.zip"
Content-Type: application/zip
X-Results: [{"filename": "image1.jpg", "success": true, ...}, ...]
```

---

## POST /compress/url

从 URL 下载并压缩图片 (Form 表单模式)。

**Content-Type:** `multipart/form-data` 或 `application/x-www-form-urlencoded`

**参数:**

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `url` | String | 是 | - | 图片 URL |
| `quality` | Integer | 否 | 85 | 压缩质量 |
| `max_size_kb` | Integer | 否 | null | 目标文件大小 |
| `output_format` | String | 否 | null | 输出格式 |

**响应:**
```json
{
  "success": true,
  "file_id": "uuid-string",
  "original_size": 2048576,
  "compressed_size": 512000,
  "compression_ratio": "25.0%",
  "format": "JPEG",
  "elapsed_ms": 234.56
}
```

---

## POST /compress/url/json

从 URL 下载并压缩图片 (JSON 模式)。

**Content-Type:** `application/json`

**请求体:**
```json
{
  "url": "https://example.com/image.jpg",
  "quality": 80,
  "max_size_kb": 500,
  "max_width": 1920,
  "max_height": 1080,
  "output_format": "WEBP"
}
```

**参数:**

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `url` | String | 是 | - | 图片 URL 地址 |
| `quality` | Integer | 否 | 85 | 压缩质量 (1-100) |
| `max_size_kb` | Integer | 否 | null | 目标文件大小 (KB) |
| `max_width` | Integer | 否 | null | 最大宽度 |
| `max_height` | Integer | 否 | null | 最大高度 |
| `output_format` | String | 否 | null | 输出格式 |

**响应:**
```json
{
  "success": true,
  "file_id": "uuid-string",
  "original_size": 2048576,
  "compressed_size": 512000,
  "compression_ratio": "25.0%",
  "format": "WEBP",
  "width": 1920,
  "height": 1080,
  "elapsed_ms": 234.56
}
```

---

## POST /compress/base64

压缩 Base64 编码的图片。

**Content-Type:** `application/json`

**请求体:**
```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "filename": "photo.jpg",
  "quality": 75,
  "max_size_kb": 300,
  "max_width": 1920,
  "output_format": "WEBP"
}
```

**参数:**

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `image_base64` | String | 是 | - | Base64 图片数据 (可带或不带 data:image/...;base64, 前缀) |
| `filename` | String | 否 | image.jpg | 文件名，用于推断格式 |
| `quality` | Integer | 否 | 85 | 压缩质量 (1-100) |
| `max_size_kb` | Integer | 否 | null | 目标文件大小 (KB) |
| `max_width` | Integer | 否 | null | 最大宽度 |
| `max_height` | Integer | 否 | null | 最大高度 |
| `output_format` | String | 否 | null | 输出格式 |

**Base64 格式说明:**
- 支持带前缀：`data:image/jpeg;base64,/9j/...`
- 支持不带前缀：`/9j/4AAQSkZJRg...`
- 自动从前缀推断图片格式

**响应:**
```json
{
  "success": true,
  "file_id": "uuid-string",
  "original_size": 2048576,
  "compressed_size": 512000,
  "compression_ratio": "25.0%",
  "format": "WEBP",
  "width": 1920,
  "height": 1080,
  "elapsed_ms": 234.56
}
```

**错误响应:**
```json
{
  "success": false,
  "error": "Base64 解码失败：Invalid base64 string",
  "elapsed_ms": 1.23
}
```

---

## 错误码

| 状态码 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 / 不支持的格式 |
| 413 | 文件过大 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

---

## 速率限制

默认无限制，生产环境建议在 nginx 层配置：

```nginx
limit_req_zone $binary_remote_addr zone=compress:10m rate=10r/s;

server {
    location /compress {
        limit_req zone=compress burst=20 nodelay;
        proxy_pass http://image_compressor;
    }
}
```

---

## 安全建议

1. **文件类型验证**: 服务端已验证扩展名，建议客户端也验证 MIME 类型
2. **文件大小限制**: nginx 配置 `client_max_body_size`
3. **CORS**: 生产环境限制具体域名
4. **认证**: 需要时添加 API Key 认证中间件

```python
# 认证中间件示例
@app.middleware("http")
async def authenticate(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")
    if api_key != os.getenv("API_KEY"):
        return JSONResponse(status_code=401, detail="Unauthorized")
    return await call_next(request)
```
