import os
import socket
import logging
from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image, ImageDraw
import io
from werkzeug.utils import secure_filename
import qrcode
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask, SolidFillColorMask
import sys
import jieba
from collections import Counter
import requests

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
    logger.info(f"Created upload directory: {app.config['UPLOAD_FOLDER']}")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(start_port=5000, max_port=5100):
    """查找可用端口，从start_port开始，最大尝试到max_port"""
    port = start_port
    while port <= max_port:
        if not is_port_in_use(port):
            return port
        port += 1
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image(image, compression_type, quality):
    img = Image.open(image)
    original_format = img.format.lower()
    
    # 获取原始图片的尺寸
    width, height = img.size
    
    # 如果图片尺寸大于2000像素，按比例缩小
    max_dimension = 2000
    if width > max_dimension or height > max_dimension:
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # 转换颜色模式
    if compression_type == 'lossy':
        if img.mode in ['RGBA', 'P']:
            # 如果有透明通道，先在白色背景上合成
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')
    
    output = io.BytesIO()
    
    if compression_type == 'lossy':
        # JPEG压缩
        try:
            # 使用渐进式JPEG
            img.save(output, format='JPEG', quality=quality, optimize=True, progressive=True)
        except Exception as e:
            # 如果JPEG压缩失败，尝试PNG压缩
            img.save(output, format='PNG', optimize=True)
    else:  # lossless
        if original_format == 'png':
            # PNG优化
            img.save(output, format='PNG', optimize=True, compress_level=9)
        elif original_format in ['jpeg', 'jpg']:
            # 对于JPEG，尝试无损的PNG压缩
            img.save(output, format='PNG', optimize=True, compress_level=9)
        else:
            # 其他格式使用原格式优化
            img.save(output, format=img.format, optimize=True)
    
    # 检查压缩效果
    output.seek(0, io.SEEK_END)
    compressed_size = output.tell()
    image.seek(0, io.SEEK_END)
    original_size = image.tell()
    
    # 如果压缩效果不理想（压缩率小于5%），尝试其他压缩方法
    if compressed_size > original_size * 0.95:
        image.seek(0)
        img = Image.open(image)
        
        # 尝试不同的压缩策略
        output = io.BytesIO()
        if compression_type == 'lossy':
            # 降低质量
            adjusted_quality = max(quality - 10, 30)  # 不低于30
            img.save(output, format='JPEG', quality=adjusted_quality, optimize=True, progressive=True)
        else:
            # 对于无损压缩，尝试转换为优化的PNG
            img.save(output, format='PNG', optimize=True, compress_level=9)
        
        # 再次检查大小
        output.seek(0, io.SEEK_END)
        new_compressed_size = output.tell()
        
        # 如果新的压缩效果更好，使用新的结果
        if new_compressed_size < compressed_size:
            compressed_size = new_compressed_size
            output.seek(0)
            return output
    
    # 如果压缩后仍然变大，返回原图
    if compressed_size >= original_size:
        image.seek(0)
        return image
    
    output.seek(0)
    return output

# DeepSeek API 配置
DEEPSEEK_API_KEY = "sk-9dfa947798e84808a42a351cf41d80c1"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def analyze_with_deepseek(text, analysis_type):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompts = {
        "style": "请分析以下文本的写作风格，包括语言特点、修辞手法等：",
        "sentiment": "请分析以下文本的情感色彩和情绪变化：",
        "structure": "请分析以下文本的结构组织和段落安排："
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的文学分析助手，请对文本进行分析。"},
            {"role": "user", "content": f"{prompts[analysis_type]}\n\n{text}"}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"DeepSeek API error: {str(e)}")
        return f"分析过程中出现错误：{str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compress')
def compress_page():
    return render_template('compress.html')

@app.route('/qr')
def qr_page():
    return render_template('qr.html')

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        content = request.form.get('content')
        style = request.form.get('style', 'square')
        logo = request.files.get('logo')

        if not content:
            return jsonify({'error': '请输入内容'}), 400

        # 创建QR码，使用最高纠错级别
        qr = qrcode.QRCode(
            version=None,  # 自动选择最小尺寸
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # 最高纠错级别
            box_size=10,
            border=4,
        )
        qr.add_data(content)
        qr.make(fit=True)

        # 设置样式
        if style == 'rounded':
            qr_image = qr.make_image(image_factory=qrcode.image.PilImage,
                                   module_drawer=RoundedModuleDrawer())
        elif style == 'circle':
            qr_image = qr.make_image(image_factory=qrcode.image.PilImage,
                                   module_drawer=CircleModuleDrawer())
        else:
            qr_image = qr.make_image(fill_color="black", back_color="white")

        # 如果上传了logo，添加到二维码中心
        if logo and allowed_file(logo.filename):
            # 打开logo图片
            logo_image = Image.open(logo)
            
            # 计算合适的logo大小（二维码大小的15%）
            logo_size = int(qr_image.size[0] * 0.15)
            logo_image = logo_image.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            
            # 计算logo放置位置（居中）
            pos = ((qr_image.size[0] - logo_size) // 2,
                  (qr_image.size[1] - logo_size) // 2)
            
            # 创建圆形蒙版
            mask = Image.new('L', (logo_size, logo_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, logo_size, logo_size), fill=255)
            
            # 确保二维码图片是RGBA模式
            qr_image = qr_image.convert('RGBA')
            
            # 创建一个新图层用于logo
            logo_layer = Image.new('RGBA', qr_image.size, (0, 0, 0, 0))
            
            # 将logo粘贴到新图层上
            if logo_image.mode == 'RGBA':
                logo_layer.paste(logo_image, pos, mask=logo_image.split()[3])
            else:
                logo_layer.paste(logo_image, pos, mask=mask)
            
            # 在logo周围添加白色背景
            bg_size = int(logo_size * 1.1)
            bg_pos = ((qr_image.size[0] - bg_size) // 2,
                     (qr_image.size[1] - bg_size) // 2)
            bg_layer = Image.new('RGBA', qr_image.size, (0, 0, 0, 0))
            bg_draw = ImageDraw.Draw(bg_layer)
            bg_draw.ellipse((bg_pos[0], bg_pos[1],
                           bg_pos[0] + bg_size,
                           bg_pos[1] + bg_size),
                          fill=(255, 255, 255, 255))
            
            # 合并所有图层
            qr_image = Image.alpha_composite(qr_image, bg_layer)
            qr_image = Image.alpha_composite(qr_image, logo_layer)

        # 保存到内存
        img_io = io.BytesIO()
        qr_image.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/compress', methods=['POST'])
def compress():
    if 'image' not in request.files:
        logger.error("No file provided")
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        logger.error("No file selected")
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        logger.error(f"File type not allowed: {file.filename}")
        return jsonify({'error': 'File type not allowed'}), 400
    
    compression_type = request.form.get('compression_type', 'lossy')
    quality = int(request.form.get('quality', 50))
    
    try:
        compressed = compress_image(file, compression_type, quality)
        return send_file(
            compressed,
            as_attachment=True,
            download_name=f'compressed_{secure_filename(file.filename)}',
            mimetype='image/jpeg' if compression_type == 'lossy' and (file.filename.lower().endswith('jpg') or file.filename.lower().endswith('jpeg')) else 'image/png'
        )
    except Exception as e:
        logger.error(f"Failed to compress image: {e}")
        return jsonify({'error': str(e)}), 500

# 小说分析相关路由
@app.route('/novel')
def novel():
    return render_template('novel.html')

@app.route('/api/analyze-style', methods=['POST'])
def analyze_style():
    try:
        text = request.json.get('text', '')
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        # 使用 DeepSeek API 进行分析
        analysis = analyze_with_deepseek(text, "style")
        return jsonify({"result": analysis})
    except Exception as e:
        logger.error(f"Error in style analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze-sentiment', methods=['POST'])
def analyze_sentiment():
    try:
        text = request.json.get('text', '')
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        # 使用 DeepSeek API 进行分析
        analysis = analyze_with_deepseek(text, "sentiment")
        return jsonify({"result": analysis})
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze-structure', methods=['POST'])
def analyze_structure():
    try:
        text = request.json.get('text', '')
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        # 使用 DeepSeek API 进行分析
        analysis = analyze_with_deepseek(text, "structure")
        return jsonify({"result": analysis})
    except Exception as e:
        logger.error(f"Error in structure analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze_novel():
    try:
        data = request.get_json()
        if not data or 'text' not in data or 'type' not in data:
            return jsonify({'error': '请提供文本和分析类型'}), 400

        text = data['text']
        analysis_type = data['type']

        # 构建 prompt
        prompts = {
            'style': "请分析以下文本的写作风格，包括语言特点、修辞手法、叙事视角等：\n\n",
            'sentiment': "请分析以下文本的情感倾向，包括主要情绪、情感变化、情感强度等：\n\n",
            'structure': "请分析以下文本的结构特点，包括段落组织、情节发展、时空安排等：\n\n"
        }

        if analysis_type not in prompts:
            return jsonify({'error': '不支持的分析类型'}), 400

        prompt = prompts[analysis_type] + text

        # 调用 DeepSeek API
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的文学分析助手，擅长分析文本的写作风格、情感和结构。请用markdown格式输出分析结果，确保分析专业、深入且易于理解。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
        )

        if response.status_code != 200:
            return jsonify({'error': 'AI 服务暂时不可用'}), 500

        result = response.json()
        analysis = result['choices'][0]['message']['content']

        return jsonify({'result': analysis})

    except Exception as e:
        app.logger.error(f"分析过程出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 从环境变量获取端口，如果没有设置则使用默认值
    default_port = int(os.environ.get('PORT', 5000))
    
    try:
        # 检查默认端口是否可用
        if is_port_in_use(default_port):
            logger.warning(f"Port {default_port} is in use")
            port = find_available_port(default_port)
            logger.info(f"Found available port: {port}")
        else:
            port = default_port
            logger.info(f"Using default port: {port}")
        
        # 启动服务器
        logger.info(f"Starting server on port {port}...")
        app.run(debug=True, host='0.0.0.0', port=port)
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
