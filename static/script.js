document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const compressionType = document.getElementById('compressionType');
    const qualitySlider = document.getElementById('qualitySlider');
    const compressButton = document.getElementById('compressButton');
    const uploadArea = document.getElementById('uploadArea');
    const uploadContent = document.getElementById('uploadContent');
    const uploadPreview = document.getElementById('uploadPreview');
    const imagePreview = document.getElementById('imagePreview');
    const fileName = document.getElementById('fileName');
    const imageSize = document.getElementById('imageSize');
    const imageDimensions = document.getElementById('imageDimensions');
    const changeFileBtn = document.getElementById('changeFile');
    const downloadSection = document.getElementById('downloadSection');
    const compressionRatio = document.getElementById('compressionRatio');
    const originalSizeStats = document.getElementById('originalSizeStats');
    const compressedSizeStats = document.getElementById('compressedSizeStats');

    let currentFile = null;
    let compressedBlob = null;

    // 文件输入变化处理
    fileInput.addEventListener('change', handleFiles);

    // 压缩类型变化处理
    compressionType.addEventListener('change', function() {
        const qualityContainer = document.getElementById('qualityContainer');
        qualityContainer.style.display = this.value === 'lossy' ? 'block' : 'none';
    });

    // 压缩按钮点击处理
    compressButton.addEventListener('click', async function() {
        if (!currentFile) return;

        try {
            const formData = new FormData();
            formData.append('file', currentFile);
            formData.append('compression_type', compressionType.value);
            formData.append('quality', qualitySlider.value);

            const response = await fetch('/api/compress', {
                method: 'POST',
                body: formData
            });

            // 检查响应的 Content-Type
            const contentType = response.headers.get('content-type');
            
            if (!response.ok) {
                if (contentType && contentType.includes('application/json')) {
                    const error = await response.json();
                    throw new Error(error.error || '压缩失败');
                } else {
                    throw new Error('压缩失败: ' + response.statusText);
                }
            }

            // 如果响应成功，检查是否是图片
            if (!contentType || !contentType.includes('image/')) {
                throw new Error('服务器返回了无效的数据类型');
            }

            compressedBlob = await response.blob();
            
            // 计算并显示压缩信息
            const ratio = ((1 - compressedBlob.size / currentFile.size) * 100).toFixed(1);
            compressionRatio.textContent = ratio + '%';
            originalSizeStats.textContent = formatFileSize(currentFile.size);
            compressedSizeStats.textContent = formatFileSize(compressedBlob.size);
            
            // 显示下载区域
            downloadSection.classList.remove('hidden');
            
        } catch (error) {
            console.error('压缩错误:', error);
            alert('压缩失败: ' + error.message);
        }
    });

    // 下载按钮点击处理
    document.getElementById('downloadButton').addEventListener('click', function() {
        if (!compressedBlob) return;
        
        const url = URL.createObjectURL(compressedBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `compressed_${currentFile.name}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });

    // 文件处理函数
    async function handleFiles(e) {
        const selectedFiles = e.target.files || e.dataTransfer.files;
        if (!selectedFiles.length) return;

        const file = selectedFiles[0]; // 只处理第一个文件
        
        // 检查文件类型
        const isImage = file.type.startsWith('image/') || 
                       file.name.toLowerCase().endsWith('.heic');
                       
        if (!isImage) {
            alert('请上传图片文件');
            return;
        }

        try {
            // 更新UI显示
            uploadContent.classList.add('hidden');
            uploadPreview.classList.remove('hidden');
            downloadSection.classList.add('hidden'); // 隐藏下载区域
            
            // 显示文件名和大小
            fileName.textContent = file.name;
            imageSize.textContent = formatFileSize(file.size);
            
            // 预览图片
            await previewImage(file);
            
            // 启用压缩按钮
            compressButton.disabled = false;
            
            // 保存当前文件
            currentFile = file;
            compressedBlob = null; // 清除之前的压缩结果
        } catch (error) {
            console.error('处理文件错误:', error);
            alert('处理文件失败: ' + error.message);
        }
    }

    // 图片预览函数
    async function previewImage(file) {
        try {
            let imageUrl;
            
            if (file.name.toLowerCase().endsWith('.heic')) {
                // HEIC格式使用服务器端预览
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await fetch('/api/preview', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || '预览失败');
                }
                
                const blob = await response.blob();
                imageUrl = URL.createObjectURL(blob);
            } else {
                // 其他格式直接预览
                imageUrl = URL.createObjectURL(file);
            }
            
            // 加载图片并获取尺寸
            await new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => {
                    imagePreview.src = imageUrl;
                    imageDimensions.textContent = `${img.naturalWidth} × ${img.naturalHeight}`;
                    resolve();
                };
                img.onerror = () => reject(new Error('加载图片失败'));
                img.src = imageUrl;
            });
        } catch (error) {
            console.error('预览错误:', error);
            imagePreview.src = '';
            imageDimensions.textContent = '';
            throw error;
        }
    }

    // 文件大小格式化
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 拖放处理
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // 拖放高亮效果
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('drag-over');
        }, false);
    });

    // 处理拖放
    uploadArea.addEventListener('drop', (e) => {
        handleFiles(e);
    }, false);

    // 更换文件按钮
    changeFileBtn.addEventListener('click', () => {
        fileInput.click();
    });
});
