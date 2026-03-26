# Image Compressor Skill

高性能图片压缩 API 服务，支持多种格式和目标大小控制。

## 功能特性

- ✅ 支持 12 种图片格式：bmp, gif, heic, jfif, jpeg, jpg, livp, png, ppm, tif, tiff, webp
- ✅ 目标大小控制 - 自动迭代压缩直到达到指定大小
- ✅ 高并发 - FastAPI + 线程池，支持 200+ 张/秒
- ✅ 低内存 - 流式处理，单图内存限制
- ✅ HTTP API - Java 后端可直接调用
- ✅ Docker 部署 - 支持容器化
- ✅ 三种输入方式：文件上传、URL 下载、Base64 编码

## 快速开始

### 安装依赖

```bash
cd scripts
pip3 install -r requirements.txt
```

### 启动服务

```bash
./start.sh
```

服务默认运行在 `http://localhost:8765`

### API 文档

访问 `http://localhost:8765/docs` 查看 Swagger UI

## 使用示例

### curl 调用

```bash
# 文件压缩
curl -X POST "http://localhost:8765/compress" \
  -F "file=@image.jpg" \
  -F "quality=80" \
  -F "max_size_kb=500" \
  -o compressed.jpg

# URL 压缩
curl -X POST "http://localhost:8765/compress/url" \
  -F "url=https://example.com/image.jpg" \
  -F "quality=80"

# Base64 压缩
curl -X POST "http://localhost:8765/compress/base64" \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "data:image/jpeg;base64,...", "quality": 75}'
```

### Java 调用

```java
ImageCompressorClient client = new ImageCompressorClient("http://localhost:8765");

// 文件压缩
byte[] compressed = client.compress(new File("image.jpg"), 80, 500);

// URL 压缩
CompressResult result = client.compressFromUrlJson(
    "https://example.com/image.jpg", 80, 500, null, null, "WEBP"
);

// Base64 压缩
CompressResult result = client.compressFromBase64(
    base64Data, "photo.jpg", 75, 300, "WEBP"
);
```

## 配置选项

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8765` | 监听端口 |
| `WORKERS` | `4` | Uvicorn 工作进程数 |
| `MAX_WORKERS` | `8` | 压缩线程池大小 |

## 性能基准

| 场景 | 并发数 | 平均耗时 | 吞吐量 |
|------|--------|----------|--------|
| 单图压缩 (2MB JPEG) | 1 | ~150ms | - |
| 批量压缩 | 10 | ~200ms | 50 张/秒 |
| 高并发 | 100 | ~500ms | 200 张/秒 |

## 文件结构

```
image-compressor/
├── SKILL.md              # 技能文档
├── README.md             # 本文件
├── scripts/
│   ├── image_compressor.py  # 核心压缩库
│   ├── server.py            # FastAPI 服务
│   ├── server_py36.py       # Python 3.6 兼容版
│   ├── ImageCompressorClient.java  # Java 客户端
│   ├── requirements.txt     # Python 依赖
│   ├── start.sh            # 启动脚本
│   ├── Dockerfile          # Docker 镜像
│   └── docker-compose.yml  # Docker 编排
└── references/
    └── api-reference.md    # API 参考文档
```

## License

MIT
