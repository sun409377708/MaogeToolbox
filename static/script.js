document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const compressionType = document.getElementById('compressionType');
    const qualitySlider = document.getElementById('qualitySlider');
    const compressButton = document.getElementById('compressButton');
    const originalPreview = document.getElementById('originalPreview');
    const compressedPreview = document.getElementById('compressedPreview');
    const originalSize = document.getElementById('originalSize');
    const compressedSize = document.getElementById('compressedSize');
    const qualityContainer = document.getElementById('qualityContainer');
    const batchProgress = document.getElementById('batchProgress');
    const progressList = document.getElementById('progressList');
    const downloadSection = document.getElementById('downloadSection');
    const compressionRatio = document.getElementById('compressionRatio');
    const originalSizeStats = document.getElementById('originalSizeStats');
    const compressedSizeStats = document.getElementById('compressedSizeStats');
    const uploadArea = document.getElementById('uploadArea');
    const uploadContent = document.getElementById('uploadContent');
    const uploadPreview = document.getElementById('uploadPreview');
    const imagePreview = document.getElementById('imagePreview');
    const fileName = document.getElementById('fileName');
    const imageSize = document.getElementById('imageSize');
    const imageDimensions = document.getElementById('imageDimensions');
    const changeFileBtn = document.getElementById('changeFile');

    let currentFile = null;
    let files = [];
    let compressedImageData = null;

    compressionType.addEventListener('change', function() {
        qualityContainer.style.display = 
            this.value === 'lossy' ? 'block' : 'none';
    });

    fileInput.addEventListener('change', function(e) {
        files = Array.from(e.target.files);
        if (files.length > 0) {
            currentFile = files[0];
            updatePreview(currentFile, originalPreview, originalSize);
            compressButton.disabled = false;
            // 清空压缩预览
            compressedPreview.innerHTML = '<p class="text-gray-500">等待压缩</p>';
            compressedSize.textContent = '大小：-';
        }
    });

    function updatePreview(file, previewElement, sizeElement) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewElement.innerHTML = `<img src="${e.target.result}" class="max-h-full max-w-full object-contain">`;
            sizeElement.textContent = `大小：${formatFileSize(file.size)}`;
        };
        reader.readAsDataURL(file);
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function calculateCompressionRatio(originalSize, compressedSize) {
        return ((1 - compressedSize / originalSize) * 100).toFixed(1) + '%';
    }

    function showDownloadSection(originalSize, compressedSize) {
        compressionRatio.textContent = calculateCompressionRatio(originalSize, compressedSize);
        originalSizeStats.textContent = formatFileSize(originalSize);
        compressedSizeStats.textContent = formatFileSize(compressedSize);

        downloadSection.classList.remove('hidden');
    }

    compressButton.addEventListener('click', async function() {
        if (files.length === 0) return;

        batchProgress.classList.remove('hidden');
        progressList.innerHTML = '';

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const progressItem = createProgressItem(file.name);
            progressList.appendChild(progressItem);

            try {
                const compressedBlob = await compressFile(file, progressItem);
                if (file === currentFile) {
                    // 更新压缩预览
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        compressedPreview.innerHTML = `<img src="${e.target.result}" class="max-h-full max-w-full object-contain">`;
                        compressedSize.textContent = `大小：${formatFileSize(compressedBlob.size)}`;
                    };
                    reader.readAsDataURL(compressedBlob);
                }
            } catch (error) {
                updateProgressItemStatus(progressItem, 'error', error.message);
            }
        }
    });

    function createProgressItem(filename) {
        const div = document.createElement('div');
        div.className = 'flex items-center justify-between p-2 bg-gray-50 rounded';
        div.innerHTML = `
            <span class="text-sm">${filename}</span>
            <span class="text-sm text-gray-500">处理中...</span>
        `;
        return div;
    }

    function updateProgressItemStatus(item, status, message) {
        const statusSpan = item.querySelector('span:last-child');
        statusSpan.textContent = message;
        if (status === 'error') {
            statusSpan.classList.add('text-red-500');
        } else if (status === 'success') {
            statusSpan.classList.add('text-green-500');
        }
    }

    async function compressFile(file, progressItem) {
        const formData = new FormData();
        formData.append('image', file);  
        formData.append('compression_type', compressionType.value);
        formData.append('quality', qualitySlider.value);

        const response = await fetch('/compress', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '压缩失败');
        }

        const blob = await response.blob();
        compressedImageData = blob;  
        
        // 显示下载区域
        showDownloadSection(file.size, blob.size);
        
        updateProgressItemStatus(progressItem, 'success', '完成');
        return blob;
    }

    async function compressImage(file) {
        const formData = new FormData();
        formData.append('image', file);
        formData.append('quality', qualitySlider.value);
        formData.append('compression_type', document.querySelector('input[name="compression_type"]:checked').value);

        try {
            const response = await fetch('/compress', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('压缩失败');
            }

            const blob = await response.blob();
            compressedImageData = blob;
            
            // 显示下载区域
            showDownloadSection(file.size, blob.size);
            
            // 预览压缩后的图片
            const compressedImageUrl = URL.createObjectURL(blob);
            document.getElementById('compressedPreview').src = compressedImageUrl;
            
            return compressedImageUrl;
        } catch (error) {
            console.error('压缩错误:', error);
            alert('图片压缩失败，请重试');
        }
    }

    // 添加下载按钮事件监听
    document.getElementById('downloadButton').addEventListener('click', () => {
        if (compressedImageData) {
            const link = document.createElement('a');
            const url = URL.createObjectURL(compressedImageData);
            const originalFileName = document.querySelector('input[type="file"]').files[0].name;
            const extension = originalFileName.split('.').pop();
            const newFileName = `compressed_${originalFileName.replace(`.${extension}`, '')}.${extension}`;
            
            link.href = url;
            link.download = newFileName;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }
    });

    // 拖拽相关事件
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        uploadArea.classList.add('drag-over');
    }

    function unhighlight() {
        uploadArea.classList.remove('drag-over');
    }

    // 处理文件上传
    uploadArea.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFiles, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles({ target: { files } });
    }

    async function handleFiles(e) {
        const files = [...e.target.files];
        if (files.length === 0) return;

        const file = files[0]; // 只处理第一个文件
        if (!file.type.startsWith('image/')) {
            alert('请上传图片文件');
            return;
        }

        // 显示文件信息
        fileName.textContent = file.name;
        imageSize.textContent = formatFileSize(file.size);

        // 创建预览
        const reader = new FileReader();
        reader.onload = async function(e) {
            // 预览图片
            imagePreview.src = e.target.result;
            
            // 获取图片尺寸
            const img = new Image();
            img.onload = function() {
                imageDimensions.textContent = `${img.width} × ${img.height}`;
            };
            img.src = e.target.result;

            // 显示预览区域
            uploadContent.classList.add('hidden');
            uploadPreview.classList.remove('hidden');
            
            // 启用压缩按钮
            compressButton.disabled = false;
        };
        reader.readAsDataURL(file);

        // 保存当前文件
        currentFile = file;
    }

    // 更换文件按钮
    changeFileBtn.addEventListener('click', () => {
        fileInput.click();
    });
});
