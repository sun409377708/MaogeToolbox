# 图片压缩工具 (Image Compression Tool)

一个简单高效的在线图片压缩工具，支持多种图片格式的压缩。

## 功能特点

- 支持 JPG、PNG、GIF 格式图片
- 支持有损和无损压缩
- 可调节压缩质量
- 实时预览压缩效果
- 显示压缩前后的文件大小对比
- 支持大文件（最大 16MB）
- 智能压缩算法，确保最佳压缩效果

## 技术栈

- 后端：Python + Flask
- 前端：HTML5 + CSS3 + JavaScript
- 图片处理：Pillow
- 服务器：Gunicorn + Gevent

## 安装

1. 克隆仓库
```bash
git clone https://github.com/sun409377708/MaogeToolbox.git
cd MaogeToolbox
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 运行应用
```bash
python app.py
```

访问 http://localhost:5000 即可使用

## 部署

详细的部署说明请参考 [DEPLOY.md](DEPLOY.md)

## 开发者

- 猫哥工具箱团队

## 许可证

MIT License
