import os
import socket
import logging
from flask import Flask, render_template, request, jsonify, send_file, url_for
from PIL import Image, ImageDraw
import pillow_heif
import io
from werkzeug.utils import secure_filename
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask, SolidFillColorMask
import sys
import jieba
from collections import Counter
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置错误处理
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large'}), 413

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic', 'heif'}

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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
    """压缩图片"""
    try:
        # 如果是HEIC格式，先转换为PIL Image
        if isinstance(image, str) and image.lower().endswith(('.heic', '.HEIC')):
            try:
                # 使用新版本的 pillow-heif 处理方式
                heif_image = pillow_heif.read_heif(image)
                image = Image.frombytes(
                    heif_image.mode, 
                    heif_image.size, 
                    heif_image.data,
                    "raw",
                )
            except Exception as e:
                logger.error(f"Error converting HEIC: {str(e)}")
                raise
        elif not isinstance(image, Image.Image):
            image = Image.open(image)

        # 确保图片是RGB模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 获取原始图片的尺寸
        width, height = image.size
        
        # 如果图片尺寸大于2000像素，按比例缩小
        max_dimension = 2000
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        
        if compression_type == 'lossy':
            # JPEG压缩
            try:
                # 使用渐进式JPEG
                image.save(output, format='JPEG', quality=quality, optimize=True, progressive=True)
            except Exception as e:
                logger.error(f"JPEG compression failed: {str(e)}, falling back to PNG")
                # 如果JPEG压缩失败，尝试PNG压缩
                image.save(output, format='PNG', optimize=True)
        else:  # lossless
            # 无损压缩统一使用PNG
            image.save(output, format='PNG', optimize=True, compress_level=9)
        
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise

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

@app.route('/all_tools')
def all_tools():
    return render_template('all_tools.html')

@app.route('/compress')
def compress_page():
    return render_template('compress.html')

@app.route('/qr')
def qr_page():
    return render_template('qr.html')

@app.route('/novel')
def novel():
    return render_template('novel.html')

@app.route('/screenshot')
def screenshot_page():
    return render_template('screenshot.html')

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    try:
        content = request.form.get('content')
        style = request.form.get('style', 'square')
        logo = request.files.get('logo')

        if not content:
            return jsonify({'error': '请输入内容'}), 400

        # 创建基本的QR码配置
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
            qr_image = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(radius_ratio=0.8)
            )
        elif style == 'circle':
            qr_image = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=CircleModuleDrawer()
            )
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
        return jsonify({'error': f"生成二维码时发生错误：{str(e)}"}), 500

@app.route('/api/compress', methods=['POST'])
def compress():
    logger.debug("Received compression request")
    if 'file' not in request.files:
        logger.error("No file in request")
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        logger.error(f"File type not allowed: {file.filename}")
        return jsonify({'error': 'File type not allowed'}), 400
    
    compression_type = request.form.get('compression_type', 'lossy')
    quality = int(request.form.get('quality', 50))
    
    logger.debug(f"Processing file: {file.filename}, type: {compression_type}, quality: {quality}")
    
    temp_path = None
    try:
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        logger.debug(f"Saving file to: {temp_path}")
        file.save(temp_path)
        
        if not os.path.exists(temp_path):
            logger.error(f"Failed to save file to {temp_path}")
            return jsonify({'error': 'Failed to save uploaded file'}), 500
        
        logger.debug("Starting image compression")
        compressed = compress_image(temp_path, compression_type, quality)
        logger.debug("Compression completed")
        
        os.remove(temp_path)
        
        mimetype = 'image/jpeg' if compression_type == 'lossy' else 'image/png'
        return send_file(
            compressed,
            as_attachment=True,
            download_name=f'compressed_{secure_filename(file.filename)}',
            mimetype=mimetype
        )
    except Exception as e:
        logger.error(f"Failed to compress image: {str(e)}", exc_info=True)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up temporary file: {str(cleanup_error)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview', methods=['POST'])
def preview():
    """预览图片，如果是HEIC格式会转换为JPEG"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # 保存上传的文件到临时位置
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(temp_path)
        
        # 如果是HEIC格式，转换为JPEG
        if file.filename.lower().endswith(('.heic', '.HEIC')):
            heif_file = pillow_heif.read_heif(temp_path)
            image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
            )
            
            # 转换为RGB模式
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # 将转换后的图片保存到内存中
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            # 删除临时文件
            os.remove(temp_path)
            
            return send_file(
                output,
                mimetype='image/jpeg'
            )
        else:
            # 非HEIC格式直接返回
            return send_file(temp_path)
    except Exception as e:
        logger.error(f"Failed to preview image: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.binary_location = '/usr/bin/chromium'
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

@app.route('/api/screenshot', methods=['POST'])
def take_screenshot():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'error': '请提供URL'}), 400

        driver = init_driver()
        try:
            # 访问页面
            driver.get(url)
            
            # 等待页面加载完成
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 等待一下以确保动态内容加载完成
            time.sleep(2)
            
            # 获取页面实际高度
            height = driver.execute_script("return Math.max("
                "document.body.scrollHeight, document.documentElement.scrollHeight,"
                "document.body.offsetHeight, document.documentElement.offsetHeight,"
                "document.body.clientHeight, document.documentElement.clientHeight);")
            
            # 调整窗口大小以适应内容
            driver.set_window_size(1280, height)
            
            # 生成截图
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'screenshot_{timestamp}.png'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            driver.save_screenshot(filepath)
            
            return jsonify({
                'message': '截图成功',
                'filename': filename,
                'url': url_for('download_file', filename=filename)
            })
            
        finally:
            driver.quit()

    except Exception as e:
        app.logger.error(f"截图出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 小说分析相关路由
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

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    port = 8000
    try:
        app.run(debug=True, host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Failed to start server on port {port}: {e}")
        logger.error("Please make sure port 8000 is available")
        raise
