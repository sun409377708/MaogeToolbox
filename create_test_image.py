from PIL import Image, ImageDraw

# 创建一个 100x100 的白色图片
img = Image.new('RGB', (100, 100), color='white')

# 在图片上画一些内容
draw = ImageDraw.Draw(img)
draw.rectangle([30, 30, 70, 70], fill='red')
draw.ellipse([40, 40, 60, 60], fill='blue')

# 保存图片
img.save('test.jpg', 'JPEG', quality=95)
