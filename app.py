import os
from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image
import io
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compress', methods=['POST'])
def compress():
    if 'image' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
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
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
