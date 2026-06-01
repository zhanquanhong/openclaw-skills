# Token Watcher 代理通道 — 渠道接入指南

## 基本原理

```
你的 API Key sk-xxx (各渠道共用)
        │
  ┌─────┴──────┐
  │ token-      │  监听多个端口，每个端口对应一个渠道
  │ watcher     │  从 API 响应中提取 usage 字段 → 落库
  │ (代理)      │  区分渠道 → 统计到 Dashboard
  └──┬───┬───┬──┘
     │   │   │
  ┌──┘ ┌─┘ ┌─┘
  ▼    ▼   ▼
渠道A 渠道B 渠道C
```

**只改 URL，不改 API Key 和模型名**。API Key 还是交给厂商，代理只是"过路"截获 token 数据。

---

## 1. OpenClaw

**配置位置**: `~/.openclaw/openclaw.json`

```json
{
  "models": {
    "providers": {
      "deepseek": {
        "baseUrl": "http://localhost:8091",
        "apiKey": "sk-你的key"
      }
    }
  }
}
```

**端口说明**: 8091 = OpenClaw 渠道（多端口模式下端口和渠道绑定）

**验证方式**: 改完保存后，在 OpenClaw 里随便问一句话。Dashboard 上会出现一条 `渠道=OpenClaw` 的记录。

---

## 2. Python SDK (openai / litellm / langchain)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8092/v1",   # 只改这里
    api_key="sk-你的key",                    # 原样
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "你好"}],
)
```

**端口说明**: 8092 = Python（也可以通过 X-Channel 头自定义）

**aiohttp / httpx 等底层请求**:
```python
# 如果直接发 HTTP 请求
requests.post(
    "http://localhost:8092/v1/chat/completions",
    headers={
        "Authorization": "Bearer sk-你的key",
        "Content-Type": "application/json",
    },
    json={"model": "deepseek-chat", "messages": [...]},
)
```

---

## 3. Java 后端 (Spring Boot / OkHttp / HttpClient)

```java
// 方式一：使用 openai-java SDK
OpenAiClient client = OpenAiClient.builder()
    .baseUrl("http://localhost:8093")   // 改地址
    .apiKey("sk-你的key")               // 不动
    .build();

// 方式二：原生 HttpClient
HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("http://localhost:8093/v1/chat/completions"))
    .header("Authorization", "Bearer sk-你的key")
    .header("Content-Type", "application/json")
    .POST(BodyPublishers.ofString(jsonBody))
    .build();
```

**端口说明**: 8093 = Java 后端

---

## 4. curl 命令行

```bash
# 原来:
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer sk-你的key" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}]}'

# 改成:
curl http://localhost:8090/v1/chat/completions \
  -H "Authorization: Bearer sk-你的key" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}]}'
```

**端口说明**: 8090 = default（未指定渠道时走这个）

**携带渠道标识**:
```bash
curl http://localhost:8090/v1/chat/completions \
  -H "Authorization: Bearer sk-你的key" \
  -H "X-Channel: 我的脚本" \          # 自定义渠道名
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

## 5. Continue.dev (IDE 插件)

**配置位置**: `~/.continue/config.json`

```json
{
  "models": [
    {
      "title": "DeepSeek (代理)",
      "provider": "openai",
      "model": "deepseek-chat",
      "apiBase": "http://localhost:8090",       // 改地址
      "apiKey": "sk-你的key"                     // 不动
    }
  ]
}
```

---

## 6. LobeChat / ChatGPT-Next-Web

在自定义模型提供商设置中：

| 字段 | 原值 | 改为 |
|------|------|------|
| API 地址 | `https://api.deepseek.com/v1` | `http://localhost:8090/v1` |
| API Key | sk-xxx | 不变 |
| 模型名 | deepseek-chat | 不变 |

---

## 7. 多端口配置一览

端口映射关系（启动时通过 `--map-port` 指定）：

| 端口 | 渠道 | 推荐用途 |
|------|------|---------|
| 8090 | default | 未区分渠道的通用请求 |
| 8091 | OpenClaw | OpenClaw AI 助手 |
| 8092 | Python脚本 | Python 脚本/SDK/notebook |
| 8093 | Java后端 | Spring Boot 等后端服务 |

**启动命令**:
```bash
cd ~/.openclaw/workspace/skills/token-watcher
PROXY_SSL_VERIFY_NONE=1 uv run python -m src.main proxy \
  --upstream https://api.deepseek.com \
  --map-port 8090=default \
  --map-port 8091=OpenClaw \
  --map-port 8092=Python脚本 \
  --map-port 8093=Java后端
```

---

## 8. 查看用量

```bash
# Dashboard（端口 8100）
cd ~/.openclaw/workspace/skills/token-watcher
uv run python -m src.main dashboard --port 8100
```

浏览器打开 `http://localhost:8100`。

Dashboard 展示：
- 各渠道 Token 消耗排名
- 每日趋势折线图
- 高浪费对话标记
- 智能优化建议

---

## 常见问题

**Q: 改代理地址后 API Key 就不安全了吗？**
A: 不。代理只读取响应中的 `usage` 字段做统计，不做任何修改。API Key 透传到上游厂商，不会从代理泄漏。代理也不存储 API Key。

**Q: 代理挂了会影响正常请求吗？**
A: 会。代理是转发网关，挂了之后客户端请求会失败。建议生产环境用进程管理工具（systemd/supervisor）保持代理存活。

**Q: 上游换成 OpenAI / Claude 也可以吗？**
A: 可以。`--upstream` 参数指定任何 OpenAI 兼容 API 地址即可。模型定价需要在 `config.py` 的 `model_pricing` 里配置。

**Q: 流式请求也能统计吗？**
A: 能。代理实时转发流式 chunk，同时从最后一个 SSE data 块中提取 `usage` 字段。厂商响应里没带 usage 的流式请求无法统计（会记录 0 token）。

**Q: 团队有 10 个人共享一个 Key，怎么区分？**
A: 给每个人分配不同端口，或者在每个人的代码里加 `X-Channel: 张三` 请求头。Dashboard 上按渠道列就能看到每个人的用量。
