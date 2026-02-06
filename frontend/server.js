import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 6670;

// 代理 API 請求到外部伺服器
app.use('/api', createProxyMiddleware({
  target: 'http://47.106.65.25:8001/api',
  changeOrigin: true,
  pathRewrite: {
    '^/api': '/api',
  },
}));

// 提供靜態文件
app.use(express.static(path.join(__dirname, 'dist')));

// 處理 SPA 路由
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
  console.log(`Proxying /api to http://47.106.65.25:8001`);
});