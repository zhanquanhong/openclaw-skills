package com.example.imagecompressor;

import okhttp3.*;
import java.io.File;
import java.io.IOException;
import java.util.concurrent.TimeUnit;

/**
 * 图片压缩 API Java 客户端
 * 
 * 使用示例:
 * <pre>
 * ImageCompressorClient client = new ImageCompressorClient("http://localhost:8765");
 * byte[] compressed = client.compress(new File("image.jpg"), 80, 500);
 * </pre>
 */
public class ImageCompressorClient {
    
    private final String baseUrl;
    private final OkHttpClient httpClient;
    
    /**
     * 创建客户端
     * @param baseUrl API 服务地址，如 http://localhost:8765
     */
    public ImageCompressorClient(String baseUrl) {
        this.baseUrl = baseUrl;
        this.httpClient = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .build();
    }
    
    /**
     * 自定义 HTTP 客户端的构造函数
     */
    public ImageCompressorClient(String baseUrl, OkHttpClient httpClient) {
        this.baseUrl = baseUrl;
        this.httpClient = httpClient;
    }
    
    /**
     * 压缩图片
     * 
     * @param file 图片文件
     * @param quality 压缩质量 (1-100)
     * @param maxSizeKb 目标文件大小 (KB)，null 表示不限制
     * @return 压缩后的字节数据
     * @throws IOException 网络或压缩错误
     */
    public byte[] compress(File file, int quality, Integer maxSizeKb) throws IOException {
        return compress(file, quality, maxSizeKb, null, null, null);
    }
    
    /**
     * 压缩图片 (完整参数)
     * 
     * @param file 图片文件
     * @param quality 压缩质量 (1-100)
     * @param maxSizeKb 目标文件大小 (KB)
     * @param maxWidth 最大宽度
     * @param maxHeight 最大高度
     * @param outputFormat 输出格式 (JPEG, PNG, WEBP 等)
     * @return 压缩后的字节数据
     * @throws IOException 网络或压缩错误
     */
    public byte[] compress(
        File file,
        int quality,
        Integer maxSizeKb,
        Integer maxWidth,
        Integer maxHeight,
        String outputFormat
    ) throws IOException {
        
        // 构建 multipart 请求
        RequestBody fileBody = RequestBody.create(
            file,
            MediaType.parse(getMimeType(file.getName()))
        );
        
        MultipartBody.Builder builder = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", file.getName(), fileBody)
            .addFormDataPart("quality", String.valueOf(quality));
        
        if (maxSizeKb != null) {
            builder.addFormDataPart("max_size_kb", String.valueOf(maxSizeKb));
        }
        if (maxWidth != null) {
            builder.addFormDataPart("max_width", String.valueOf(maxWidth));
        }
        if (maxHeight != null) {
            builder.addFormDataPart("max_height", String.valueOf(maxHeight));
        }
        if (outputFormat != null) {
            builder.addFormDataPart("output_format", outputFormat);
        }
        
        Request request = new Request.Builder()
            .url(baseUrl + "/compress")
            .post(builder.build())
            .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                String errorBody = response.body() != null ? response.body().string() : "Unknown error";
                throw new IOException("压缩失败：" + response.code() + " - " + errorBody);
            }
            
            // 打印压缩统计信息
            printCompressionStats(response);
            
            return response.body().bytes();
        }
    }
    
    /**
     * 从 URL 压缩图片 (Form 表单模式)
     * 
     * @param imageUrl 图片 URL
     * @param quality 压缩质量 (1-100)
     * @param maxSizeKb 目标文件大小 (KB)
     * @return 压缩结果
     * @throws IOException 网络或压缩错误
     */
    public CompressResult compressFromUrl(String imageUrl, int quality, Integer maxSizeKb) throws IOException {
        RequestBody requestBody = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("url", imageUrl)
            .addFormDataPart("quality", String.valueOf(quality))
            .addFormDataPart("max_size_kb", maxSizeKb != null ? String.valueOf(maxSizeKb) : "null")
            .build();
        
        Request request = new Request.Builder()
            .url(baseUrl + "/compress/url")
            .post(requestBody)
            .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                String errorBody = response.body() != null ? response.body().string() : "Unknown error";
                throw new IOException("压缩失败：" + response.code() + " - " + errorBody);
            }
            
            String json = response.body().string();
            return parseResult(json);
        }
    }
    
    /**
     * 从 URL 压缩图片 (JSON 模式)
     * 
     * @param imageUrl 图片 URL
     * @param quality 压缩质量 (1-100)
     * @param maxSizeKb 目标文件大小 (KB)
     * @param maxWidth 最大宽度
     * @param maxHeight 最大高度
     * @param outputFormat 输出格式
     * @return 压缩结果
     * @throws IOException 网络或压缩错误
     */
    public CompressResult compressFromUrlJson(
        String imageUrl,
        int quality,
        Integer maxSizeKb,
        Integer maxWidth,
        Integer maxHeight,
        String outputFormat
    ) throws IOException {
        String jsonBody = createUrlJsonBody(imageUrl, quality, maxSizeKb, maxWidth, maxHeight, outputFormat);
        
        RequestBody body = RequestBody.create(jsonBody, MediaType.parse("application/json"));
        
        Request request = new Request.Builder()
            .url(baseUrl + "/compress/url/json")
            .post(body)
            .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                String errorBody = response.body() != null ? response.body().string() : "Unknown error";
                throw new IOException("压缩失败：" + response.code() + " - " + errorBody);
            }
            
            String json = response.body().string();
            return parseResult(json);
        }
    }
    
    /**
     * 压缩 Base64 图片
     * 
     * @param base64Data Base64 编码的图片数据 (可带或不带 data:image/jpeg;base64, 前缀)
     * @param filename 文件名 (用于推断格式)
     * @param quality 压缩质量 (1-100)
     * @param maxSizeKb 目标文件大小 (KB)
     * @param outputFormat 输出格式
     * @return 压缩结果
     * @throws IOException 网络或压缩错误
     */
    public CompressResult compressFromBase64(
        String base64Data,
        String filename,
        int quality,
        Integer maxSizeKb,
        String outputFormat
    ) throws IOException {
        String jsonBody = createBase64JsonBody(base64Data, filename, quality, maxSizeKb, outputFormat);
        
        RequestBody body = RequestBody.create(jsonBody, MediaType.parse("application/json"));
        
        Request request = new Request.Builder()
            .url(baseUrl + "/compress/base64")
            .post(body)
            .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                String errorBody = response.body() != null ? response.body().string() : "Unknown error";
                throw new IOException("压缩失败：" + response.code() + " - " + errorBody);
            }
            
            String json = response.body().string();
            return parseResult(json);
        }
    }
    
    /**
     * 健康检查
     * 
     * @return 服务是否可用
     */
    public boolean healthCheck() throws IOException {
        Request request = new Request.Builder()
            .url(baseUrl + "/health")
            .get()
            .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            return response.isSuccessful();
        }
    }
    
    /**
     * 获取支持的格式列表
     * 
     * @return 支持的格式列表
     * @throws IOException 网络错误
     */
    public String[] getSupportedFormats() throws IOException {
        Request request = new Request.Builder()
            .url(baseUrl + "/health")
            .get()
            .build();
        
        try (Response response = httpClient.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("获取格式列表失败");
            }
            
            String json = response.body().string();
            // 简单解析 JSON 提取 supported_formats
            // 生产环境建议使用 Jackson 或 Gson
            int start = json.indexOf("\"supported_formats\":[");
            if (start == -1) return new String[0];
            
            int end = json.indexOf("]", start);
            String arrayStr = json.substring(start + 23, end);
            return arrayStr.replaceAll("[\"\\[\\]]", "").split(",");
        }
    }
    
    private void printCompressionStats(Response response) {
        String originalSize = response.header("X-Original-Size");
        String compressedSize = response.header("X-Compressed-Size");
        String ratio = response.header("X-Compression-Ratio");
        String elapsedMs = response.header("X-Elapsed-Ms");
        
        if (ratio != null) {
            System.out.printf("压缩完成：原始=%s bytes, 压缩后=%s bytes, 压缩率=%s, 耗时=%s ms%n",
                originalSize, compressedSize, ratio, elapsedMs);
        }
    }
    
    private String getMimeType(String filename) {
        String ext = filename.substring(filename.lastIndexOf(".") + 1).toLowerCase();
        switch (ext) {
            case "jpg":
            case "jpeg":
            case "jfif":
                return "image/jpeg";
            case "png":
                return "image/png";
            case "gif":
                return "image/gif";
            case "webp":
                return "image/webp";
            case "bmp":
                return "image/bmp";
            case "tiff":
            case "tif":
                return "image/tiff";
            case "heic":
            case "heif":
                return "image/heif";
            default:
                return "application/octet-stream";
        }
    }
    
    private CompressResult parseResult(String json) {
        // 简单 JSON 解析 (生产环境建议使用 Jackson 或 Gson)
        CompressResult result = new CompressResult();
        result.success = json.contains("\"success\":true");
        
        if (result.success) {
            result.fileId = extractJsonValue(json, "file_id");
            result.originalSize = extractJsonLong(json, "original_size");
            result.compressedSize = extractJsonLong(json, "compressed_size");
            result.compressionRatio = extractJsonValue(json, "compression_ratio");
            result.format = extractJsonValue(json, "format");
            result.elapsedMs = extractJsonDouble(json, "elapsed_ms");
        } else {
            result.error = extractJsonValue(json, "error");
        }
        
        return result;
    }
    
    // ============ JSON 构建辅助方法 ============
    
    private String createUrlJsonBody(
        String imageUrl,
        int quality,
        Integer maxSizeKb,
        Integer maxWidth,
        Integer maxHeight,
        String outputFormat
    ) {
        StringBuilder sb = new StringBuilder();
        sb.append("{");
        sb.append("\"url\":\"").append(escapeJson(imageUrl)).append("\"");
        sb.append(",\"quality\":").append(quality);
        
        if (maxSizeKb != null) {
            sb.append(",\"max_size_kb\":").append(maxSizeKb);
        }
        if (maxWidth != null) {
            sb.append(",\"max_width\":").append(maxWidth);
        }
        if (maxHeight != null) {
            sb.append(",\"max_height\":").append(maxHeight);
        }
        if (outputFormat != null) {
            sb.append(",\"output_format\":\"").append(escapeJson(outputFormat)).append("\"");
        }
        
        sb.append("}");
        return sb.toString();
    }
    
    private String createBase64JsonBody(
        String base64Data,
        String filename,
        int quality,
        Integer maxSizeKb,
        String outputFormat
    ) {
        StringBuilder sb = new StringBuilder();
        sb.append("{");
        sb.append("\"image_base64\":\"").append(escapeJson(base64Data)).append("\"");
        sb.append(",\"filename\":\"").append(escapeJson(filename)).append("\"");
        sb.append(",\"quality\":").append(quality);
        
        if (maxSizeKb != null) {
            sb.append(",\"max_size_kb\":").append(maxSizeKb);
        }
        if (outputFormat != null) {
            sb.append(",\"output_format\":\"").append(escapeJson(outputFormat)).append("\"");
        }
        
        sb.append("}");
        return sb.toString();
    }
    
    private String escapeJson(String text) {
        if (text == null) return "";
        return text
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t");
    }
    
    // ============ JSON 解析方法 ============
    
    private String extractJsonValue(String json, String key) {
        String searchKey = "\"" + key + "\":";
        int start = json.indexOf(searchKey);
        if (start == -1) return null;
        
        start = json.indexOf("\"", start + searchKey.length());
        if (start == -1) return null;
        
        int end = json.indexOf("\"", start + 1);
        if (end == -1) return null;
        
        return json.substring(start + 1, end);
    }
    
    private long extractJsonLong(String json, String key) {
        String searchKey = "\"" + key + "\":";
        int start = json.indexOf(searchKey);
        if (start == -1) return 0;
        
        start += searchKey.length();
        int end = json.indexOf(",", start);
        if (end == -1) end = json.indexOf("}", start);
        
        try {
            return Long.parseLong(json.substring(start, end).trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }
    
    private double extractJsonDouble(String json, String key) {
        String searchKey = "\"" + key + "\":";
        int start = json.indexOf(searchKey);
        if (start == -1) return 0.0;
        
        start += searchKey.length();
        int end = json.indexOf(",", start);
        if (end == -1) end = json.indexOf("}", start);
        
        try {
            return Double.parseDouble(json.substring(start, end).trim());
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }
    
    /**
     * 压缩结果类
     */
    public static class CompressResult {
        public boolean success;
        public String fileId;
        public Long originalSize;
        public Long compressedSize;
        public String compressionRatio;
        public String format;
        public Double elapsedMs;
        public String error;
        
        @Override
        public String toString() {
            if (success) {
                return String.format("CompressResult{success=true, ratio=%s, elapsed=%.2fms}", 
                    compressionRatio, elapsedMs);
            } else {
                return String.format("CompressResult{success=false, error=%s}", error);
            }
        }
    }
    
    /**
     * 主函数 - 使用示例
     */
    public static void main(String[] args) {
        try {
            ImageCompressorClient client = new ImageCompressorClient("http://localhost:8765");
            
            // 健康检查
            if (!client.healthCheck()) {
                System.out.println("服务不可用");
                return;
            }
            System.out.println("服务正常");
            
            // 示例 1: 压缩本地文件
            File inputFile = new File("test.jpg");
            if (inputFile.exists()) {
                byte[] compressed = client.compress(inputFile, 80, 500);
                System.out.println("文件压缩完成，大小：" + compressed.length + " bytes");
                
                java.nio.file.Files.write(
                    java.nio.file.Paths.get("compressed_file.jpg"),
                    compressed
                );
            }
            
            // 示例 2: URL 图片压缩
            CompressResult urlResult = client.compressFromUrlJson(
                "https://example.com/image.jpg",
                80,
                500,
                1920,
                null,
                "WEBP"
            );
            System.out.println("URL 压缩：" + urlResult);
            
            // 示例 3: Base64 图片压缩
            String base64Data = "data:image/jpeg;base64,/9j/4AAQSkZJRg...";
            CompressResult base64Result = client.compressFromBase64(
                base64Data,
                "photo.jpg",
                75,
                300,
                "WEBP"
            );
            System.out.println("Base64 压缩：" + base64Result);
            
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
