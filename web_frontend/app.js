// 手写文字生成器 - 网页版
// 完全基于小程序功能实现

// ========== 全局配置 ==========
// 部署配置：设置为false时自动使用服务器地址
const LOCAL_TEST_MODE = true;  // 本地测试时设为true，部署时设为false
const SERVER_IP = '47.107.148.252';  // 服务器公网地址

// API基础地址配置
const API_BASE_URL = LOCAL_TEST_MODE ? 'http://127.0.0.1:5000' : `http://${SERVER_IP}:5000`;

// 纸张尺寸配置（300DPI）
const PAPER_SIZES = {
    'A4': { width: 2480, height: 3508 },
    'A3': { width: 3508, height: 4961 },
    'A5': { width: 1748, height: 2480 },
    'B4': { width: 2953, height: 4169 },
    'B5': { width: 2079, height: 2953 },
    'Letter': { width: 2550, height: 3300 }
};

// 纸张类型配置
const PAPER_TYPES = {
    'red': { isUnderlined: true, lineColor: 'red', paperType: 'lined' },
    'green': { isUnderlined: true, lineColor: 'green', paperType: 'lined' },
    'blue': { isUnderlined: true, lineColor: 'blue', paperType: 'lined' },
    'grid': { isUnderlined: false, lineColor: '', paperType: 'grid' },
    'plain': { isUnderlined: false, lineColor: '', paperType: 'plain' },
    'custom': { isUnderlined: false, lineColor: '', paperType: 'plain' }
};

// 默认文本（东风破歌词）
const DEFAULT_TEXT = `                        《东风破》
                        词：方文山 曲：周杰伦

一盏离愁孤灯伫立在窗口，我在门后假装你人还没走，旧地如重游月圆更寂寞，夜半清醒的烛火不忍苛责我。一壶漂泊浪迹天涯难入喉，你走之后酒暖回忆思念瘦，水向东流时间怎么偷，花开就一次成熟我却错过。谁在用琵琶弹奏一曲东风破，岁月在墙上剥落看见小时候，犹记得那年我们都还很年幼，而如今琴声幽幽我的等候你没听过。谁在用琵琶弹奏一曲东风破，枫叶将故事染色结局我看透，篱笆外的古道我牵着你走过，荒烟蔓草的年头就连分手都很沉默。

一壶漂泊浪迹天涯难入喉，你走之后酒暖回忆思念瘦，水向东流时间怎么偷，花开就一次成熟我却错过。谁在用琵琶弹奏一曲东风破，岁月在墙上剥落看见小时候，犹记得那年我们都还很年幼，而如今琴声幽幽我的等候你没听过。谁在用琵琶弹奏一曲东风破，枫叶将故事染色结局我看透，篱笆外的古道我牵着你走过，荒烟蔓草的年头就连分手都很沉默。

谁在用琵琶弹奏一曲东风破，岁月在墙上剥落看见小时候，犹记得那年我们都还很年幼，而如今琴声幽幽我的等候你没听过。谁在用琵琶弹奏一曲东风破，枫叶将故事染色结局我看透，篱笆外的古道我牵着你走过，荒烟蔓草的年头就连分手都很沉默。`;

// ========== 应用状态 ==========
const appState = {
    // 文本内容
    text: DEFAULT_TEXT,
    textLength: DEFAULT_TEXT.length,
    isDefaultText: true,
    
    // 字体
    fonts: [],
    selectedFont: '',
    customFontFile: null,
    customFontName: '',
    
    // 背景
    backgroundFile: null,
    backgroundPath: '',
    paperSize: 'A4',
    paperType: 'red',
    
    // 尺寸
    width: 2480,
    height: 3508,
    
    // 参数
    fontSize: 90,
    lineSpacing: 120,
    wordSpacing: 10,
    marginTop: 150,
    marginBottom: 150,
    marginLeft: 150,
    marginRight: 150,
    
    // 预览
    previewImages: [],
    currentPage: 0,
    isDefaultPreview: false,
    
    // 相思豆
    currentAction: '', // 'generate' 或 'generatePDF'
    loveseedCode: ''
};

// ========== DOM 元素 ==========
const elements = {
    // 文本输入
    textInput: document.getElementById('textInput'),
    charCount: document.getElementById('charCount'),
    clearTextBtn: document.getElementById('clearTextBtn'),
    uploadWordBtn: document.getElementById('uploadWordBtn'),
    fileInput: document.getElementById('fileInput'),
    
    // 字体
    fontSelect: document.getElementById('fontSelect'),
    uploadFontBtn: document.getElementById('uploadFontBtn'),
    fontInput: document.getElementById('fontInput'),
    customFontName: document.getElementById('customFontName'),
    
    // 背景
    paperSize: document.getElementById('paperSize'),
    paperType: document.getElementById('paperType'),
    bgInput: document.getElementById('bgInput'),
    bgFileName: document.getElementById('bgFileName'),
    bgPreview: document.getElementById('bgPreview'),
    bgUploadGroup: document.getElementById('bgUploadGroup'),
    clearBgBtn: document.getElementById('clearBgBtn'),
    
    // 参数
    fontSize: document.getElementById('fontSize'),
    fontSizeValue: document.getElementById('fontSizeValue'),
    lineSpacing: document.getElementById('lineSpacing'),
    lineSpacingValue: document.getElementById('lineSpacingValue'),
    wordSpacing: document.getElementById('wordSpacing'),
    wordSpacingValue: document.getElementById('wordSpacingValue'),
    marginTop: document.getElementById('marginTop'),
    marginBottom: document.getElementById('marginBottom'),
    marginLeft: document.getElementById('marginLeft'),
    marginRight: document.getElementById('marginRight'),
    
    // 操作
    previewBtn: document.getElementById('previewBtn'),
    generateBtn: document.getElementById('generateBtn'),
    downloadBtn: document.getElementById('downloadBtn'),
    
    // 预览
    previewImage: document.getElementById('previewImage'),
    previewArea: document.getElementById('previewArea'),
    previewPagination: document.getElementById('previewPagination'),
    prevPageBtn: document.getElementById('prevPageBtn'),
    nextPageBtn: document.getElementById('nextPageBtn'),
    pageInfo: document.getElementById('pageInfo'),
    
    // 相思豆弹窗
    loveseedModal: document.getElementById('loveseedModal'),
    loveseedInput: document.getElementById('loveseedInput'),
    confirmLoveseedBtn: document.getElementById('confirmLoveseedBtn'),
    getLoveseedBtn: document.getElementById('getLoveseedBtn'),
    closeLoveseedModal: document.getElementById('closeLoveseedModal'),
    
    // 加载遮罩
    loadingMask: document.getElementById('loadingMask'),
    loadingText: document.getElementById('loadingText')
};

// ========== 工具函数 ==========

// 显示加载状态
function showLoading(text = '加载中...') {
    elements.loadingText.textContent = text;
    elements.loadingMask.style.display = 'flex';
}

// 隐藏加载状态
function hideLoading() {
    elements.loadingMask.style.display = 'none';
}

// 显示提示
function showAlert(message, type = 'info') {
    alert(message);
}

// 显示确认对话框
function showConfirm(title, message) {
    return confirm(`${title}\n\n${message}`);
}

// 更新字符计数
function updateCharCount() {
    const length = appState.text.length;
    appState.textLength = length;
    elements.charCount.textContent = `字数：${length}`;
    
    // 显示/隐藏清空按钮
    elements.clearTextBtn.style.display = length > 0 ? 'inline-block' : 'none';
}

// 更新翻页按钮状态
function updatePagination() {
    const totalPages = appState.previewImages.length;
    const currentPage = appState.currentPage;
    
    if (totalPages <= 1) {
        elements.previewPagination.style.display = 'none';
        return;
    }
    
    elements.previewPagination.style.display = 'flex';
    elements.pageInfo.textContent = `${currentPage + 1} / ${totalPages}`;
    elements.prevPageBtn.disabled = currentPage === 0;
    elements.nextPageBtn.disabled = currentPage === totalPages - 1;
}

// 显示当前页
function showCurrentPage() {
    const currentImage = appState.previewImages[appState.currentPage];
    if (currentImage) {
        elements.previewImage.onload = function() {
            showWatermark();
        };
        elements.previewImage.src = currentImage;
        updatePagination();
    }
}

// 验证输入
function validateInput() {
    if (!appState.text || appState.text.trim().length === 0) {
        showAlert('请输入要转换的文字', 'warning');
        return false;
    }
    if (!appState.selectedFont && !appState.customFontFile) {
        showAlert('请选择字体', 'warning');
        return false;
    }
    return true;
}

// 构建请求参数
function buildParams() {
    const paperConfig = PAPER_TYPES[appState.paperType];
    
    return {
        text: appState.text,
        font_size: String(appState.fontSize),
        line_spacing: String(appState.lineSpacing),
        word_spacing: String(appState.wordSpacing - 20), // 小程序减20
        fill: '(0, 0, 0, 255)',
        left_margin: String(appState.marginLeft),
        top_margin: String(appState.marginTop),
        right_margin: String(appState.marginRight),
        bottom_margin: String(appState.marginBottom),
        width: String(appState.width),
        height: String(appState.height),
        line_spacing_sigma: '1',
        font_size_sigma: '1',
        word_spacing_sigma: '1',
        perturb_x_sigma: '1',
        perturb_y_sigma: '1',
        perturb_theta_sigma: '0.05',
        strikethrough_probability: '0',
        strikethrough_length_sigma: '1',
        strikethrough_width_sigma: '1',
        strikethrough_angle_sigma: '0.3',
        strikethrough_width: '3',
        ink_depth_sigma: '0',
        isUnderlined: paperConfig.isUnderlined ? 'true' : 'false',
        line_color: paperConfig.lineColor || 'red',
        paper_type: paperConfig.paperType || 'plain',
        font_option: appState.selectedFont,
        preview: 'true',  // 添加preview参数
        enableEnglishSpacing: 'false'
    };
}

// 构建FormData
function buildFormData(params) {
    const formData = new FormData();
    
    // 添加文本参数
    Object.keys(params).forEach(key => {
        formData.append(key, params[key]);
    });
    
    // 添加自定义字体
    if (appState.customFontFile) {
        formData.append('font_file', appState.customFontFile);
    }
    
    // 添加背景图
    if (appState.backgroundFile) {
        formData.append('image', appState.backgroundFile);
    }
    
    return formData;
}

// ========== API 调用 ==========

// 加载字体列表
async function loadFonts() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/miniprogram/fonts`);
        const data = await response.json();
        
        if (data.status === 'success' && data.fonts) {
            appState.fonts = data.fonts;
            
            // 填充字体选择框
            elements.fontSelect.innerHTML = '<option value="">请选择字体</option>';
            data.fonts.forEach(font => {
                const option = document.createElement('option');
                option.value = font.filename;
                option.textContent = font.name || font.filename;
                elements.fontSelect.appendChild(option);
            });
            
            // 默认选择司马彦字体
            const simayanFont = data.fonts.find(f => f.filename.includes('司马彦'));
            if (simayanFont) {
                appState.selectedFont = simayanFont.filename;
                elements.fontSelect.value = simayanFont.filename;
            }
        }
    } catch (err) {
        console.error('加载字体失败:', err);
        showAlert('加载字体失败', 'error');
    }
}

// 解析文档
async function parseDocument(file) {
    showLoading('解析文档中...');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/api/textfileprocess`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`服务器错误: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.text) {
            appState.text = data.text;
            appState.isDefaultText = false;
            elements.textInput.value = data.text;
            updateCharCount();
            // 不显示成功提示，直接显示结果
        } else if (data.error) {
            throw new Error(data.error);
        } else {
            throw new Error('未知错误');
        }
    } catch (err) {
        console.error('解析文档失败:', err);
        showAlert('解析文档失败: ' + err.message, 'error');
    } finally {
        hideLoading();
    }
}

// 预览
async function doPreview() {
    if (!validateInput()) return;
    
    appState.isDefaultPreview = false;
    showLoading('生成预览中...');
    
    try {
        const params = buildParams();
        const formData = buildFormData(params);
        
        console.log('发送预览请求...');
        const response = await fetch(`${API_BASE_URL}/api/miniprogram/preview`, {
            method: 'POST',
            body: formData
        });
        
        console.log('响应状态:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('预览响应数据:', data);
            
            if (data.status === 'success') {
                // base64图片
                const images = data.images || [data.image];
                console.log('图片数量:', images.length);
                
                if (images[0]) {
                    // 保存所有页面
                    appState.previewImages = images.map(img => 
                        img.startsWith('data:') ? img : 'data:image/png;base64,' + img
                    );
                    appState.currentPage = 0;
                    
                    // 显示第一页
                    elements.previewImage.style.display = 'block';
                    showCurrentPage();

                    // 隐藏占位符
                    const placeholder = elements.previewArea.querySelector('.preview-placeholder');
                    if (placeholder) {
                        placeholder.style.display = 'none';
                    }
                    
                    // 更新翻页按钮
                    updatePagination();
                    
                    console.log(`预览成功，共${images.length}页`);
                    
                    // 不显示成功提示，预览图片已经显示了
                } else {
                    throw new Error('没有返回图片数据');
                }
            } else {
                throw new Error(data.message || '预览失败');
            }
        } else {
            const text = await response.text();
            console.error('预览失败响应:', text);
            let errorMsg = '预览生成失败';
            try {
                const data = JSON.parse(text);
                errorMsg = data.message || errorMsg;
            } catch(e) {
                errorMsg = text || errorMsg;
            }
            throw new Error(errorMsg);
        }
    } catch (err) {
        console.error('预览失败:', err);
        showAlert(err.message || '预览失败', 'error');
    } finally {
        hideLoading();
    }
}

// 生成图片
async function doGenerate(loveseedCode) {
    if (!validateInput()) return;
    
    // 先执行预览
    try {
        await doPreview();
    } catch (e) {
        console.warn('预览失败，但继续尝试生成', e);
    }
    
    showLoading('生成图片中...');
    
    try {
        const params = buildParams();
        params.preview = 'false';  // 不是预览
        params.loveseed_code = loveseedCode;
        const formData = buildFormData(params);
        formData.set('pdf_save', 'false');
        // formData.set('zip_save', 'true'); // 不再使用ZIP打包
        
        const response = await fetch(`${API_BASE_URL}/api/miniprogram/generate`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'success') {
                if (data.file_id) {
                    // 下载文件 (PDF或ZIP)
                    const downloadUrl = `${API_BASE_URL}/api/miniprogram/download/${data.file_id}`;
                    const downloadResp = await fetch(downloadUrl);
                    const blob = await downloadResp.blob();
                    const url = URL.createObjectURL(blob);
                    
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = data.file_type === 'pdf' ? `手写文稿_${Date.now()}.pdf` : `手写图片_${Date.now()}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                } else if (data.images) {
                    // 直接下载图片
                    data.images.forEach((imgData, index) => {
                        const a = document.createElement('a');
                        a.href = imgData;
                        a.download = `手写图片_${Date.now()}_${index + 1}.png`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                    });
                }
                
                // 不显示成功提示，下载已经开始了
            } else {
                throw new Error(data.message || '生成失败');
            }
        } else {
            const text = await response.text();
            let errorMsg = '生成失败';
            try {
                const data = JSON.parse(text);
                errorMsg = data.message || data.error || errorMsg;
            } catch(e) {
                errorMsg = text || errorMsg;
            }
            throw new Error(errorMsg);
        }
    } catch (err) {
        console.error('生成图片失败:', err);
        showAlert(err.message || '生成图片失败', 'error');
    } finally {
        hideLoading();
    }
}

// 生成PDF
async function doGeneratePDF(loveseedCode) {
    if (!validateInput()) return;
    
    // 先执行预览
    try {
        await doPreview();
    } catch (e) {
        console.warn('预览失败，但继续尝试生成', e);
    }
    
    showLoading('生成PDF中...');
    
    try {
        const params = buildParams();
        params.preview = 'false';  // 不是预览
        params.loveseed_code = loveseedCode;
        const formData = buildFormData(params);
        formData.set('pdf_save', 'true');  // PDF模式
        
        const response = await fetch(`${API_BASE_URL}/api/miniprogram/generate`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'success' && data.file_id) {
                // 下载文件
                const downloadUrl = `${API_BASE_URL}/api/miniprogram/download/${data.file_id}`;
                const downloadResp = await fetch(downloadUrl);
                const blob = await downloadResp.blob();
                const url = URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = `手写文稿_${Date.now()}.pdf`;
                a.click();
                URL.revokeObjectURL(url);
                
                // 不显示成功提示，PDF下载已经开始了
            } else {
                throw new Error(data.message || '生成PDF失败');
            }
        } else {
            const text = await response.text();
            let errorMsg = '生成PDF失败';
            try {
                const data = JSON.parse(text);
                errorMsg = data.message || data.error || errorMsg;
            } catch(e) {
                errorMsg = text || errorMsg;
            }
            throw new Error(errorMsg);
        }
    } catch (err) {
        console.error('生成PDF失败:', err);
        showAlert(err.message || '生成PDF失败', 'error');
    } finally {
        hideLoading();
    }
}

// ========== 事件处理 ==========

// 文本输入
elements.textInput.addEventListener('input', function(e) {
    const text = e.target.value;
    
    // 如果是默认文本，用户开始输入时清空
    if (appState.isDefaultText && text.length > 0) {
        appState.text = text;
        appState.isDefaultText = false;
    } else {
        appState.text = text;
    }
    
    updateCharCount();
});

// 清空文本
elements.clearTextBtn.addEventListener('click', function() {
    if (showConfirm('清空文本', '确定要清空所有文字吗？')) {
        appState.text = '';
        appState.isDefaultText = false;
        elements.textInput.value = '';
        updateCharCount();
    }
});

// 上传文档按钮
const uploadWordBtn = document.getElementById('uploadWordBtn');
const fileInput = document.getElementById('fileInput');

if (uploadWordBtn && fileInput) {
    uploadWordBtn.addEventListener('click', function() {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (file) {
            await parseDocument(file);
        }
        e.target.value = ''; // 清空，允许重复上传同一文件
    });
}

// 字体选择
elements.fontSelect.addEventListener('change', function(e) {
    appState.selectedFont = e.target.value;
    if (e.target.value) {
        // 清空自定义字体
        appState.customFontFile = null;
        appState.customFontName = '';
        elements.customFontName.textContent = '';
    }
});

// 上传自定义字体
elements.uploadFontBtn.addEventListener('click', function() {
    elements.fontInput.click();
});

elements.fontInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        if (!file.name.toLowerCase().endsWith('.ttf')) {
            showAlert('请选择TTF格式的字体文件', 'warning');
            return;
        }
        appState.customFontFile = file;
        appState.customFontName = file.name;
        elements.customFontName.textContent = file.name;
        
        // 清空字体选择
        appState.selectedFont = '';
        elements.fontSelect.value = '';
        
        // 不显示成功提示，已显示文件名
    }
    e.target.value = '';
});

// 纸张规格
elements.paperSize.addEventListener('change', function(e) {
    const size = e.target.value;
    appState.paperSize = size;
    const dimensions = PAPER_SIZES[size];
    appState.width = dimensions.width;
    appState.height = dimensions.height;
});

// 纸张类型
elements.paperType.addEventListener('change', function(e) {
    const type = e.target.value;
    appState.paperType = type;
    
    // 如果选择上传背景图片
    if (type === 'custom') {
        elements.bgUploadGroup.style.display = 'block';
        elements.bgInput.click();
    } else {
        // 清除背景
        appState.backgroundFile = null;
        appState.backgroundPath = '';
        elements.bgFileName.textContent = '';
        elements.bgPreview.style.display = 'none';
        elements.bgUploadGroup.style.display = 'none';
    }
});

// 上传背景图
elements.bgInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        if (!file.type.startsWith('image/')) {
            showAlert('请选择图片文件', 'warning');
            return;
        }
        
        appState.backgroundFile = file;
        appState.backgroundPath = URL.createObjectURL(file);
        elements.bgFileName.textContent = file.name;
        elements.bgPreview.src = appState.backgroundPath;
        elements.bgPreview.style.display = 'block';
        elements.clearBgBtn.style.display = 'inline-block';
        elements.bgUploadGroup.style.display = 'block';
        
        // 不显示成功提示，图片预览已经显示了
    }
    e.target.value = '';
});

// 清除背景
elements.clearBgBtn.addEventListener('click', function() {
    appState.backgroundFile = null;
    appState.backgroundPath = '';
    elements.bgFileName.textContent = '';
    elements.bgPreview.style.display = 'none';
    elements.clearBgBtn.style.display = 'none';
    
    // 重置纸张类型为默认
    appState.paperType = 'red';
    elements.paperType.value = 'red';
    elements.bgUploadGroup.style.display = 'none';
});

// 滑块参数
elements.fontSize.addEventListener('input', function(e) {
    appState.fontSize = parseInt(e.target.value);
    elements.fontSizeValue.textContent = e.target.value;
});

elements.lineSpacing.addEventListener('input', function(e) {
    appState.lineSpacing = parseInt(e.target.value);
    elements.lineSpacingValue.textContent = e.target.value;
});

elements.wordSpacing.addEventListener('input', function(e) {
    appState.wordSpacing = parseInt(e.target.value);
    elements.wordSpacingValue.textContent = e.target.value;
});

// 边距参数
elements.marginTop.addEventListener('input', function(e) {
    appState.marginTop = parseInt(e.target.value) || 0;
});

elements.marginBottom.addEventListener('input', function(e) {
    appState.marginBottom = parseInt(e.target.value) || 0;
});

elements.marginLeft.addEventListener('input', function(e) {
    appState.marginLeft = parseInt(e.target.value) || 0;
});

elements.marginRight.addEventListener('input', function(e) {
    appState.marginRight = parseInt(e.target.value) || 0;
});

// 预览按钮
elements.previewBtn.addEventListener('click', function() {
    doPreview();
});

// 翻页按钮
elements.prevPageBtn.addEventListener('click', function() {
    if (appState.currentPage > 0) {
        appState.currentPage--;
        showCurrentPage();
    }
});

elements.nextPageBtn.addEventListener('click', function() {
    if (appState.currentPage < appState.previewImages.length - 1) {
        appState.currentPage++;
        showCurrentPage();
    }
});

// 生成图片按钮
elements.generateBtn.addEventListener('click', function() {
    if (!validateInput()) return;
    appState.currentAction = 'generate';
    elements.loveseedModal.style.display = 'flex';
});

// 生成PDF按钮
elements.downloadBtn.addEventListener('click', function() {
    if (!validateInput()) return;
    appState.currentAction = 'generatePDF';
    elements.loveseedModal.style.display = 'flex';
});

// 相思豆弹窗 - 确认
elements.confirmLoveseedBtn.addEventListener('click', function() {
    const code = elements.loveseedInput.value.trim();
    
    if (code.length !== 6 || !/^\d{6}$/.test(code)) {
        showAlert('请输入6位数字的相思豆码', 'warning');
        return;
    }
    
    appState.loveseedCode = code;
    elements.loveseedModal.style.display = 'none';
    elements.loveseedInput.value = '';
    
    // 执行对应操作
    if (appState.currentAction === 'generate') {
        doGenerate(code);
    } else if (appState.currentAction === 'generatePDF') {
        doGeneratePDF(code);
    }
});


// 相思豆弹窗 - 获取相思豆
elements.getLoveseedBtn.addEventListener('click', function() {
    // 打开获取相思豆的页面
    const paymentUrl = window.location.origin + '/payment/index.html';
    window.open(paymentUrl, '_blank');
});

// 相思豆弹窗 - 关闭
elements.closeLoveseedModal.addEventListener('click', function() {
    elements.loveseedModal.style.display = 'none';
    elements.loveseedInput.value = '';
});

// ========== 初始化 ==========
async function init() {
    // 加载字体列表
    await loadFonts();
    
    // 设置默认文本
    elements.textInput.value = DEFAULT_TEXT;
    updateCharCount();
    
    // 加载默认预览图
    appState.isDefaultPreview = true;
    appState.previewImages = ['images/default_preview.png'];
    appState.currentPage = 0;
    
    elements.previewImage.style.display = 'block';
    showCurrentPage();

    // 隐藏占位符
    const placeholder = elements.previewArea.querySelector('.preview-placeholder');
    if (placeholder) {
        placeholder.style.display = 'none';
    }
    
    console.log('手写文字生成器初始化完成');
}

// 显示水印
function showWatermark() {
    // 如果是默认预览图，不显示水印
    if (appState.isDefaultPreview) {
        const overlay = document.getElementById('watermarkOverlay');
        if (overlay) overlay.style.display = 'none';
        return;
    }

    const overlay = document.getElementById('watermarkOverlay');
    if (!overlay) return;
    
    overlay.style.display = 'block';
    overlay.innerHTML = ''; // 清空旧水印
    
    // 确保 overlay 有尺寸
    const width = overlay.offsetWidth;
    const height = overlay.offsetHeight;
    
    if (width === 0 || height === 0) {
        // 如果尺寸为0，可能是图片还没渲染完，延迟重试
        setTimeout(showWatermark, 100);
        return;
    }
    
    const text = "一纸相思手写坊";
    const fontSize = 48;
    const gap = 240;
    const angle = -30;
    
    // 创建多个水印元素铺满
    // 简单的计算铺满数量
    const cols = Math.ceil(width / gap);
    const rows = Math.ceil(height / gap);
    
    for (let i = 0; i < rows; i++) {
        for (let j = 0; j < cols; j++) {
            const div = document.createElement('div');
            div.textContent = text;
            div.style.position = 'absolute';
            div.style.left = (j * gap) + 'px';
            div.style.top = (i * gap) + 'px';
            div.style.fontSize = fontSize + 'px';
            div.style.color = 'rgba(255, 0, 0, 0.4)';
            div.style.transform = `rotate(${angle}deg)`;
            div.style.pointerEvents = 'none';
            div.style.userSelect = 'none';
            div.style.whiteSpace = 'nowrap';
            overlay.appendChild(div);
        }
    }
}

// 加载站点配置
async function loadSiteConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/site-config`);
        if (response.ok) {
            const result = await response.json();
            if (result.status === 'success' && result.data) {
                const config = result.data;
                
                // 更新版权信息
                if (config.copyright_text) {
                    document.getElementById('copyrightText').textContent = config.copyright_text;
                }
                
                // 更新ICP信息
                const icpInfo = document.getElementById('icpInfo');
                const icpLink = document.getElementById('icpLink');
                if (config.icp_beian && config.icp_beian.trim()) {
                    icpLink.textContent = config.icp_beian;
                    icpLink.href = 'https://beian.miit.gov.cn/';
                    icpInfo.style.display = 'block';
                } else {
                    icpInfo.style.display = 'none';
                }
                
                // 更新友情链接
                const friendLinksContainer = document.getElementById('friendLinksContainer');
                const friendLinksList = document.getElementById('friendLinksList');
                if (config.friend_links && config.friend_links.length > 0) {
                    friendLinksList.innerHTML = '';
                    config.friend_links.forEach(link => {
                        if (link.name && link.url) {
                            const linkElement = document.createElement('a');
                            linkElement.textContent = link.name;
                            linkElement.href = link.url;
                            linkElement.target = '_blank';
                            linkElement.style.marginRight = '15px';
                            linkElement.style.color = 'white';
                            linkElement.style.textDecoration = 'none';
                            friendLinksList.appendChild(linkElement);
                        }
                    });
                    friendLinksContainer.style.display = 'block';
                } else {
                    friendLinksContainer.style.display = 'none';
                }
            }
        }
    } catch (error) {
        console.log('Failed to load site config:', error);
        // 静默失败，使用默认配置
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    init();
    loadSiteConfig(); // 加载站点配置
});
