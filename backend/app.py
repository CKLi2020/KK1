import time
import uuid
from flask import Flask, request, jsonify, send_file, session, current_app, send_from_directory
from handright import Template, handwrite, Feature
# from threading import Thread
from PIL import Image, ImageFont, ImageDraw
from dotenv import load_dotenv
import psutil
import unicodedata

load_dotenv()
import os
import gc

import io
import logging
from flask_cors import CORS
from datetime import timedelta
from flask_session import Session  # 导入扩展
from werkzeug.utils import secure_filename

# 文件模块
from docx import Document
import PyPDF2
import tempfile
import shutil
import zipfile
from pdf import generate_pdf

# 图片处理模块
from identify import identify_distance


# 预处理文本：移除可能导致黑色方块的控制字符
def clean_text_for_handwrite(text):
    """清理文本中的控制字符，保留换行符"""
    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 移除零宽字符和不可见字符
    text = text.replace('\u200b', '')  # 零宽空格
    text = text.replace('\u200c', '')  # 零宽不连字
    text = text.replace('\u200d', '')  # 零宽连字
    text = text.replace('\ufeff', '')  # 零宽无间隔空格 (BOM)
    text = text.replace('\u00ad', '')  # 软连字符
    
    # 移除所有方块符号（Block Elements Unicode范围）
    # U+2580-259F: Block Elements
    block_chars = set(chr(i) for i in range(0x2580, 0x25A0))
    
    # 移除其他常见的占位符/特殊符号
    # U+25A0-25FF: Geometric Shapes
    geometric_chars = set(chr(i) for i in range(0x25A0, 0x2600))
    
    # 移除私有使用区字符（Private Use Area）
    # U+E000-F8FF, U+F0000-FFFFD, U+100000-10FFFD
    
    cleaned = []
    for char in text:
        if char == '\n':
            # 保留换行符
            cleaned.append(char)
        elif char == '\t':
            # 将制表符转换为空格
            cleaned.append('    ')  # 4个空格
        elif char in block_chars or char in geometric_chars:
            # 跳过方块字符和几何图形
            logger.info(f"移除方块/几何字符: '{char}' (U+{ord(char):04X})")
            continue
        else:
            category = unicodedata.category(char)
            # 过滤控制字符和特殊字符
            if category not in ('Cc', 'Cf', 'Co', 'Cs', 'Cn'):
                # Cc=控制字符, Cf=格式字符, Co=私有区, Cs=代理对, Cn=未分配
                # 额外检查：过滤 emoji 和符号
                code_point = ord(char)
                if code_point < 0x1F000 or (0x2000 <= code_point < 0x2100):
                    # 允许常用字符：中文、英文、数字、常用标点符号
                    # 但排除私有使用区
                    if not (0xE000 <= code_point <= 0xF8FF):
                        cleaned.append(char)
                    else:
                        logger.info(f"移除私有区字符: '{char}' (U+{code_point:04X})")
                # 否则跳过（可能是 emoji 或特殊符号）
    
    result = ''.join(cleaned)
    if len(result) != len(text):
        logger.info(f"文本清理：原始长度 {len(text)}, 清理后长度 {len(result)}, 移除了 {len(text) - len(result)} 个字符")
    return result


def filter_unsupported_chars(text, font):
    """
    过滤字体不支持的字符，避免显示黑色方块
    如果字体不支持某个字符，就用空格替换（而不是跳过）
    """
    from PIL import Image, ImageDraw
    
    filtered = []
    for char in text:
        # 保留换行符
        if char == '\n':
            filtered.append(char)
            continue
        
        # 对于空格和制表符，直接保留
        if char in (' ', '\t'):
            filtered.append(char)
            continue
        
        try:
            # 创建一个小的测试图片来检查字符是否能被渲染
            test_img = Image.new('L', (50, 50), color=255)
            draw = ImageDraw.Draw(test_img)
            
            # 尝试绘制字符
            draw.text((10, 10), char, font=font, fill=0)
            
            # 检查图片是否有变化（如果字体不支持，图片应该全白）
            bbox = test_img.getbbox()
            
            if bbox is not None:
                # 图片有内容，说明字符被成功渲染
                filtered.append(char)
            else:
                # 图片全白，说明字体不支持该字符，跳过不添加
                logger.info(f"跳过字体不支持的字符: '{char}' (U+{ord(char):04X})")
        except Exception as e:
            # 如果出现任何异常，为了安全起见，跳过该字符
            logger.warning(f"检查字符时出错，跳过: '{char}' (U+{ord(char):04X}) - {e}")
    
    result = ''.join(filtered)
    logger.info(f"字体过滤：原始长度 {len(text)}, 过滤后长度 {len(result)}")
    return result


# 安全文件删除函数
def safe_remove_directory(directory_path, max_retries=5):
    """安全删除目录，带重试机制和更强的文件处理"""
    if not os.path.exists(directory_path):
        return True

    for attempt in range(max_retries):
        try:
            # 强制垃圾回收，释放可能的文件句柄
            gc.collect()
            # 等待更长时间让系统释放文件句柄
            time.sleep(0.2 * (attempt + 1))  # 递增等待时间

            # 递归删除所有文件和子目录
            deleted_files = []
            failed_files = []

            for root, dirs, files in os.walk(directory_path, topdown=False):
                # 删除文件
                for file in files:
                    file_path = os.path.join(root, file)
                    if safe_remove_single_file(file_path, max_retries=2):
                        deleted_files.append(file_path)
                    else:
                        failed_files.append(file_path)

                # 删除空目录
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        if os.path.exists(dir_path) and not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except Exception as dir_e:
                        logger.warning(
                            f"Failed to delete subdirectory {dir_path}: {dir_e}"
                        )

            # 如果有文件删除失败，记录但继续尝试删除目录
            if failed_files:
                logger.warning(
                    f"Failed to delete {len(failed_files)} files: {failed_files[:3]}..."
                )

            # 最后尝试删除根目录
            if os.path.exists(directory_path):
                try:
                    os.rmdir(directory_path)
                    logger.info(
                        f"Successfully deleted temp directory: {directory_path}"
                    )
                    return True
                except OSError as e:
                    if e.errno == 145:  # 目录不为空
                        # 列出剩余文件
                        remaining_files = []
                        try:
                            for root, dirs, files in os.walk(directory_path):
                                remaining_files.extend(
                                    [os.path.join(root, f) for f in files]
                                )
                        except:
                            pass
                        logger.warning(
                            f"Directory not empty, remaining files: {remaining_files[:5]}"
                        )
                    raise

        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1} to delete {directory_path} failed: {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(1.0 * (attempt + 1))  # 递增等待时间
            else:
                logger.error(
                    f"Failed to delete temp directory after {max_retries} attempts: {directory_path}"
                )
                # 最后尝试：标记目录为稍后清理
                try:
                    cleanup_marker = os.path.join(directory_path, ".cleanup_later")
                    with open(cleanup_marker, "w") as f:
                        f.write(f"Failed to delete at {time.time()}")
                    logger.info(f"Marked directory for later cleanup: {directory_path}")
                except:
                    pass
    return False


def safe_remove_single_file(file_path, max_retries=3):
    """安全删除单个文件"""
    if not os.path.exists(file_path):
        return True

    for attempt in range(max_retries):
        try:
            # 确保文件不是只读
            os.chmod(file_path, 0o777)

            # 强制垃圾回收
            gc.collect()
            time.sleep(0.1)

            # 尝试删除文件
            os.remove(file_path)
            return True

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.3 * (attempt + 1))
            else:
                logger.warning(f"Failed to delete file {file_path}: {e}")
    return False


def safe_remove_file(file_path, max_retries=3):
    """安全删除文件，带重试机制"""
    result = safe_remove_single_file(file_path, max_retries)
    if result:
        logger.info(f"Successfully deleted file: {file_path}")
    else:
        logger.error(f"Failed to delete file after {max_retries} attempts: {file_path}")
    return result


def safe_save_and_close_image(image, image_path):
    """安全保存并关闭图片，确保文件句柄被释放"""
    try:
        # 保存图片
        image.save(image_path)

        # 如果图片对象有 close 方法，调用它
        # if hasattr(image, "close"):
        #     image.close()

        # # 强制垃圾回收
        # gc.collect()

        # # 等待一小段时间确保文件句柄被释放
        # time.sleep(0.1)

        return True
    except Exception as e:
        logger.error(f"Failed to save image {image_path}: {e}")
        return False


def cleanup_marked_directories():
    """清理项目内标记为稍后清理的目录"""
    project_temp_base = "./temp"

    # 确保项目临时目录存在
    os.makedirs(project_temp_base, exist_ok=True)

    try:
        for item in os.listdir(project_temp_base):
            item_path = os.path.join(project_temp_base, item)
            if os.path.isdir(item_path) and item.startswith("tmp"):
                cleanup_marker = os.path.join(item_path, ".cleanup_later")
                if os.path.exists(cleanup_marker):
                    try:
                        # 检查标记时间，如果超过1小时则尝试清理
                        with open(cleanup_marker, "r") as f:
                            content = f.read()
                            if "Failed to delete at" in content:
                                timestamp = float(
                                    content.split("Failed to delete at ")[1]
                                )
                                if time.time() - timestamp > 3600:  # 1小时后
                                    logger.info(
                                        f"Attempting to cleanup marked directory: {item_path}"
                                    )
                                    if safe_remove_directory(item_path, max_retries=2):
                                        logger.info(
                                            f"Successfully cleaned up marked directory: {item_path}"
                                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to cleanup marked directory {item_path}: {e}"
                        )
    except Exception as e:
        logger.warning(f"Error during cleanup of marked directories: {e}")


# sentry 错误报告7.7
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# 限制请求速率 7.9
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 装饰器 7.15
from functools import wraps

# 定时清理文件 10.28
import schedule_clean

# 用户服务模块
from user_service import (
    wx_code_to_openid, get_or_create_user, check_user_membership,
    get_packages, create_order, complete_order, log_usage,
    add_watermark_to_image, add_watermark_to_images, FREE_CHAR_LIMIT, APP_NAME,
    is_admin, set_user_admin, admin_grant_membership, 
    get_membership_statistics, search_users, get_all_users
)
from user_service import TEST_ADMIN_OPENID, LOCAL_TEST_MODE

# 相思豆服务模块
from loveseed_service import (
    create_loveseed_order,
    verify_loveseed_code,
    consume_loveseed_download,
    get_all_packages,
    get_all_orders_admin,
    get_all_loveseed_codes_admin,
    create_loveseed_code_manual,
    delete_loveseed_code_admin,
    update_loveseed_downloads_admin
)

# 获取环境变量
mysql_host = os.getenv("MYSQL_HOST", "db")
enable_user_auth = os.getenv("ENABLE_USER_AUTH", "false")
# 获取当前路径
current_path = os.getcwd()
# 创建一个子文件夹用于存储输出的图片
output_path = os.path.join(current_path, "output")
# 如果子文件夹不存在，就创建它
if not os.path.exists(output_path):
    os.makedirs(output_path)
directory = ["./textfileprocess", "imagefileprocess"]
for directory in directory:
    if not os.path.exists(directory):
        os.makedirs(directory)
directory = "./font_assets"
font_file_names = [
    f
    for f in os.listdir(directory)
    if os.path.isfile(os.path.join(directory, f)) and f.endswith(".ttf")
]
# sentry部分 7.7
sentry_sdk.init(
    dsn="https://ed22d5c0e3584faeb4ae0f67d19f68aa@o4505255803551744.ingest.sentry.io/4505485583253504",
    integrations=[
        FlaskIntegration(),
    ],
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
)

# 启动计划任务线程, 定时清理
schedule_clean.start_schedule_thread()

# 创建一个logger
logger = logging.getLogger(__name__)

# 设置日志级别
logger.setLevel(logging.DEBUG)

# 创建 console handler，并设置级别为 DEBUG
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# 创建 file handler，并设置级别为 DEBUG
os.makedirs("logs", exist_ok=True)
fh = logging.FileHandler("logs/app.log")
fh.setLevel(logging.DEBUG)

# 创建 formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# 把 formatter 添加到 ch 和 fh
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# 把 ch 和 fh 添加到 logger
logger.addHandler(ch)
logger.addHandler(fh)

app = Flask(__name__)
CORS(app)  # , origins='*', supports_credentials=True)

# 静态文件路由
@app.route('/static/<path:filename>')
def static_files(filename):
    import os
    # Get absolute path to web_frontend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    web_frontend_path = os.path.join(backend_dir, '..', 'web_frontend')
    web_frontend_path = os.path.abspath(web_frontend_path)
    full_path = os.path.join(web_frontend_path, filename)
    print(f"Static file request: {filename}")
    print(f"Backend dir: {backend_dir}")
    print(f"Web frontend path: {web_frontend_path}")
    print(f"Full path: {full_path}")
    print(f"Path exists: {os.path.exists(full_path)}")
    if os.path.exists(full_path):
        return send_from_directory(web_frontend_path, filename)
    else:
        from flask import abort
        abort(404)



# 设置Flask app的logger级别
app.logger.setLevel(logging.DEBUG)


SECRET_KEY = "437d75c5af744b76607fe862cf8a5a368519aca486d62c5fa69ba42c16809z88"
app.config["SECRET_KEY"] = SECRET_KEY
# app.config["SESSION_COOKIE_SECURE"] = True
# app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["MAX_CONTENT_LENGTH"] = 128 * 1024 * 1024
app.permanent_session_lifetime = timedelta(minutes=5000000)
app.config["SESSION_TYPE"] = "filesystem"  # 设置session存储方式为文件
Session(app)  # 初始化扩展，传入应用程序实例
limiter = Limiter(
    app=app, key_func=get_remote_address, default_limits=["1000 per 5 minute"]
)


# 创建一个新的白色图片，并添加间隔的线条作为背景
def create_notebook_image(
    width,
    height,
    line_spacing,
    top_margin,
    bottom_margin,
    left_margin,
    right_margin,
    font_size,
    isUnderlined,
    line_color="red",  # 横线颜色，默认红色
    paper_type="plain",  # 纸张类型: plain, lined, grid
):
    if paper_type == "grid":
        # 方格纸模式：白色背景 + 青色方格
        grid_color = (0, 180, 180)  # 青色方格线
        paper_color = (255, 255, 255)  # 白色纸张
        image = Image.new("RGB", (width, height), paper_color)
        draw = ImageDraw.Draw(image)
        
        # 计算格子大小（基于字体大小，稍微大一点留边距）
        cell_size = int(font_size * 1.15)  # 格子比字体稍大15%
        
        # 计算起始位置，确保格子从边距开始
        start_x = left_margin
        start_y = top_margin
        
        # 画竖线
        x = start_x
        while x <= width - right_margin:
            draw.line((x, start_y, x, height - bottom_margin), fill=grid_color, width=1)
            x += cell_size
        
        # 画横线
        y = start_y
        while y <= height - bottom_margin:
            draw.line((start_x, y, width - right_margin, y), fill=grid_color, width=1)
            y += cell_size
            
    elif paper_type == "lined" or isUnderlined == True or isUnderlined == "true":
        # 显示横线模式：淡黄色纸张 + 彩色加粗横线
        paper_color = (255, 251, 240)  # 淡黄色纸张
        image = Image.new("RGB", (width, height), paper_color)
        draw = ImageDraw.Draw(image)
        y = top_margin + line_spacing  # 开始的y坐标设为顶部边距加字体大小
        while (
            y < height - bottom_margin
        ):  # 当y坐标小于（图片高度-底部边距）时，继续画线
            # 画加粗横线（画3条相邻的线模拟加粗效果）
            draw.line((left_margin, y-1, width - right_margin, y-1), fill=line_color)
            draw.line((left_margin, y, width - right_margin, y), fill=line_color)
            draw.line((left_margin, y+1, width - right_margin, y+1), fill=line_color)
            y += line_spacing  # 每次循环，y坐标增加行间距
    else:
        # 不显示横线模式：纯白色纸张
        image = Image.new("RGB", (width, height), "white")
    
    return image


def read_docx(file_path):
    document = Document(file_path)
    text = " ".join([paragraph.text for paragraph in document.paragraphs])
    return text


import pypandoc
try:
    # 1. 尝试获取 Pandoc 版本
    # 如果系统里已经安装了（比如你在 Dockerfile 里用 apt-get 装了），这里会成功
    version = pypandoc.get_pandoc_version()
    print(f"Pandoc found: {version}")

except OSError:
    # 2. 如果报错说找不到，说明没装，开始自动下载
    print("Pandoc not found. Downloading...")
    pypandoc.download_pandoc()
    print("Pandoc downloaded successfully.")

def convert_docx_to_text(docx_file_path):
    # 转换文件为纯文本格式，并返回转换后的文本内容
    text = pypandoc.convert_file(docx_file_path, 'plain')
    return text
    # return None


def read_pdf(file_path):
    text = ""
    with open(file_path, "rb") as pdf_file_obj:
        pdf_reader = PyPDF2.PdfReader(pdf_file_obj)
        for page_num in range(len(pdf_reader.pages)):
            page_obj = pdf_reader.pages[page_num]
            text += page_obj.extract_text()
    return text


def handle_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.info("An error occurred during the request: %s", e)
            return jsonify({"status": "error", "message": str(e)}), 500

    return decorated_function


@app.route("/api/generate_handwriting", methods=["POST"])
@limiter.limit("200 per 5 minute")
@handle_exceptions  # 错误捕获的装饰器7.15
def generate_handwriting():
    cpu_usage = psutil.cpu_percent(interval=1)  # 获取 CPU 使用率，1 秒采样间隔
    if cpu_usage > 90:
        # 如果 CPU 使用率超过 90%，返回提醒
        return (
            jsonify(
                {
                    "status": "waiting",
                    "message": f"CPU usage is too high. Please wait and try again. current cpu_usage: {cpu_usage}%",
                }
            ),
            429,
        )  # HTTP 429: Too Many Requests
    # logger.info("已经进入generate_handwriting")
    if enable_user_auth.lower() == "true":
        if "username" not in session:
            return jsonify({"status": "error", "message": "You haven't login."}), 500
    # try:
    # 先获取 form 数据
    data = request.form
    if len(data["text"]) > 10000 and (
        request.base_url == "https://handwrite.14790897.xyz"
        or request.base_url == "https://handwrite.paperai.life"
    ):
        # 请自己构建应用来运行而不是使用这个网页
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "The text is too long to process. If you want to use this service, please build your own application.",
                }
            ),  
            500,
        )
    required_form_fields = [
        "text",
        "font_size",
        "line_spacing",
        "fill",
        "left_margin",
        "top_margin",
        "right_margin",
        "bottom_margin",
        "word_spacing",
        "line_spacing_sigma",
        "font_size_sigma",
        "word_spacing_sigma",
        "perturb_x_sigma",
        "perturb_y_sigma",
        "perturb_theta_sigma",
        "preview",
    ]
    # "height","width",

    for field in required_form_fields:
        if field not in data:
            return (
                jsonify(
                    {
                        "status": "fail",
                        "message": f"Missing required field: {field}",
                    }
                ),
                400,
            )
        else:
            logger.info(f"{field}: {data[field]}")  # 打印具体的 form 字段值
            # 如果存在height和width，就创建一个新的背景图     todo
            # height=int(data["height"]),
            # width=int(data["width"]),

    # 如果用户提供了宽度和高度，创建一个新的笔记本背景图像
    if "width" in data and "height" in data:
        line_spacing = int(data.get("line_spacing", 30))
        top_margin = int(data.get("top_margin", 0))
        bottom_margin = int(data.get("bottom_margin", 0))
        left_margin = int(data.get("left_margin", 0))
        right_margin = int(data.get("right_margin", 0))
        width = int(data["width"])
        height = int(data["height"])
        font_size = int(data.get("font_size", 0))
        isUnderlined = data.get("isUnderlined", False)
        background_image = create_notebook_image(
            width,
            height,
            line_spacing,
            top_margin,
            bottom_margin,
            left_margin,
            right_margin,
            font_size,
            isUnderlined,
        )

    else:
        # 否则使用用户上传的背景图像
        background_image = request.files.get("background_image")
        if background_image is None:
            return (
                jsonify(
                    {
                        "status": "fail",
                        "message": "Missing required field: background_image",
                    }
                ),
                400,
            )
        image_data = io.BytesIO(background_image.read())

        # 使用 PIL 打开图像
        try:
            background_image = Image.open(image_data)

            # 如果图像包含 Alpha 通道（模式为 'RGBA' 或 'LA'），则去除 Alpha 通道
            if background_image.mode in ("RGBA", "LA"):
                # 将图像转换为 'RGB' 模式
                background_image = background_image.convert("RGB")

        except IOError:
            return jsonify({"status": "error", "message": "Invalid image format"}), 400

    text_to_generate = data["text"]
    
    # 预处理文本：移除可能导致黑色方块的控制字符
    text_to_generate = clean_text_for_handwrite(text_to_generate)

    # Conditionally adjust spacing for English text based on user setting
    if data.get("enableEnglishSpacing", "false").lower() == "true":
        # Only apply to English words, leave Chinese text unchanged
        import re

        def replace_english_spaces(text):
            """Replace single spaces with double spaces only for English text, preserving all other whitespace"""
            # Pattern to identify English characters (including common punctuation, hyphens, underscores)
            english_pattern = r'^[a-zA-Z0-9.,!?;:\'\"()\-_]+$'

            # Split by lines to preserve newlines
            lines = text.split('\n')
            processed_lines = []

            for line in lines:
                # Only process spaces within each line, preserve tabs and other whitespace
                # Split only on spaces (not all whitespace)
                parts = line.split(' ')
                if len(parts) <= 1:
                    # No spaces in this line, keep as is
                    processed_lines.append(line)
                    continue

                result = []
                for i, part in enumerate(parts):
                    result.append(part)

                    # If this isn't the last part, check if we should add double space
                    if i < len(parts) - 1:
                        current_is_english = bool(re.match(english_pattern, part)) if part.strip() else False
                        next_is_english = bool(re.match(english_pattern, parts[i + 1])) if parts[i + 1].strip() else False

                        # Add double space only if both current and next parts are English
                        if current_is_english and next_is_english:
                            result.append('  ')  # Double space
                        else:
                            result.append(' ')   # Single space

                processed_lines.append(''.join(result))

            # Rejoin with newlines to preserve line structure
            return '\n'.join(processed_lines)

        text_to_generate = replace_english_spaces(text_to_generate)

    # if data["preview"] == "true":
    #     # 截短字符，只生成一面
    #     preview_length = 300  # 可以调整为所需的预览长度
    #     text_to_generate = text_to_generate[:preview_length]

    # 从表单中获取字体文件并处理 7.4
    if "font_file" in request.files:
        font = request.files["font_file"].read()
        font = ImageFont.truetype(io.BytesIO(font), size=int(data["font_size"]))
    else:
        font_option = data["font_option"]
        logger.info(f"font_option: {font_option}")
        logger.info(f"font_file_names: {font_file_names}")
        if font_option in font_file_names:
            # 确定字体文件的完整路径
            font_path = os.path.join("font_assets", font_option)
            logger.info(f"font_path: {font_path}")
            # 打开字体文件并读取其内容为字节
            with open(font_path, "rb") as f:
                font_content = f.read()
            # 通过 io.BytesIO 创建一个 BytesIO 对象，然后使用 ImageFont.truetype 从字节中加载字体
            font = ImageFont.truetype(
                io.BytesIO(font_content), size=int(data["font_size"])
            )
        else:
            return (
                jsonify(
                    {
                        "status": "fail",
                        "message": "Missing  fontfile.",
                    }
                ),
                400,
            )

    template = Template(
        background=background_image,
        font=font,
        line_spacing=int(data["line_spacing"]),  # + int(data["font_size"])
        # fill=ast.literal_eval(data["fill"])[:3],  # Ignore the alpha value
        # fill=(0),#如果feel是只有一个颜色的话那么在改变墨水的时候会导致R变化而GB不变化,颜色会变红 9.17
        left_margin=int(data["left_margin"]),
        top_margin=int(data["top_margin"]),
        right_margin=int(data["right_margin"]) - int(data["word_spacing"]) * 2,
        bottom_margin=int(data["bottom_margin"]),
        word_spacing=int(data["word_spacing"]),
        line_spacing_sigma=int(data["line_spacing_sigma"]),  # 行间距随机扰动
        font_size_sigma=int(data["font_size_sigma"]),  # 字体大小随机扰动
        word_spacing_sigma=int(data["word_spacing_sigma"]),  # 字间距随机扰动
        end_chars="，。",  # 防止特定字符因排版算法的自动换行而出现在行首
        perturb_x_sigma=int(data["perturb_x_sigma"]),  # 笔画横向偏移随机扰动
        perturb_y_sigma=int(data["perturb_y_sigma"]),  # 笔画纵向偏移随机扰动
        perturb_theta_sigma=float(data["perturb_theta_sigma"]),  # 笔画旋转偏移随机扰动
        strikethrough_probability=float(
            data["strikethrough_probability"]
        ),  # 删除线概率
        strikethrough_length_sigma=float(
            data["strikethrough_length_sigma"]
        ),  # 删除线长度随机扰动
        strikethrough_width_sigma=float(
            data["strikethrough_width_sigma"]
        ),  # 删除线宽度随机扰动
        strikethrough_angle_sigma=float(
            data["strikethrough_angle_sigma"]
        ),  # 删除线角度随机扰动
        strikethrough_width=float(data["strikethrough_width"]),  # 删除线宽度
        ink_depth_sigma=float(data["ink_depth_sigma"]),  # 墨水深度随机扰动
    )

    # 创建一个BytesIO对象，用于保存.zip文件的内容
    logger.info(f"data[pdf_save]: {data['pdf_save']}")
    if not data["pdf_save"] == "true":
        # 过滤字体不支持的字符
        text_to_generate = filter_unsupported_chars(text_to_generate, font)
        images = handwrite(text_to_generate, template)
        logger.info("handwrite initial images generated successfully")
        # 创建项目内的临时目录，避免使用系统临时目录
        project_temp_base = "./temp"
        os.makedirs(project_temp_base, exist_ok=True)
        temp_dir = tempfile.mkdtemp(dir=project_temp_base)
        unique_filename = "images_" + str(time.time())
        zip_path = f"./temp/{unique_filename}.zip"
        try:
            for i, im in enumerate(images):
                # 保存每张图像到临时目录
                image_path = os.path.join(temp_dir, f"{i}.png")

                # 使用安全保存函数
                if safe_save_and_close_image(im, image_path):
                    logger.info(f"Image {i} saved successfully")
                else:
                    logger.error(f"Failed to save image {i}")

                del im  # 释放内存

                if data["preview"] == "true":
                    # 预览模式：读取文件内容到内存，然后清理临时目录

                    with open(image_path, "rb") as f:
                        image_data = f.read()

                    # 立即清理整个临时目录
                    # safe_remove_directory(temp_dir)

                    # 从内存发送文件
                    return send_file(
                        io.BytesIO(image_data),
                        mimetype="image/png",
                        as_attachment=False,
                    )

            if not data["preview"] == "true":
                # 创建ZIP文件
                shutil.make_archive(zip_path[:-4], "zip", temp_dir)

                # 读取ZIP文件到内存，然后立即删除文件
                try:
                    with open(zip_path, "rb") as f:
                        zip_data = f.read()

                    # 立即删除ZIP文件
                    safe_remove_file(zip_path)

                    # 从内存发送文件
                    response = send_file(
                        io.BytesIO(zip_data),
                        download_name="images.zip",
                        mimetype="application/zip",
                        as_attachment=True,
                    )
                except Exception as e:
                    logger.error(f"Failed to read ZIP file: {e}")
                    # 降级到直接发送文件
                    response = send_file(
                        zip_path,
                        download_name="images.zip",
                        mimetype="application/zip",
                        as_attachment=True,
                    )
            return response
        finally:
            # 使用改进的安全删除函数
            safe_remove_directory(temp_dir)
            # ZIP文件已在上面删除，这里只是保险
    else:
        logger.info("PDF generate")
        temp_pdf_file_path = None  # 初始化变量
        # 过滤字体不支持的字符
        text_to_generate = filter_unsupported_chars(text_to_generate, font)
        images = handwrite(text_to_generate, template)
        try:
            temp_pdf_file_path = generate_pdf(images=images)
            # 将文件路径存储在请求上下文中，以便稍后可以访问它
            request.temp_file_path = temp_pdf_file_path
            return send_file(
                temp_pdf_file_path,
                download_name="images.pdf",
                mimetype="application/pdf",
                as_attachment=True,
                conditional=True,
            )
        finally:
            pass
        #     if temp_pdf_file_path is not None:  # 检查变量是否已赋值
        #         for _ in range(5):  # 尝试5次
        #             try:
        #                 os.remove(temp_pdf_file_path)  # 尝试删除文件
        #                 break  # 如果成功删除，跳出循环
        #             except Exception as e:  # 捕获并处理删除文件时可能出现的异常
        #                 logger.error(f"Failed to remove temporary PDF file: {e}")
        #                 time.sleep(1)
        # unique_filename = "images_" + str(time.time()) + ".zip"

        # # 如果用户选择了保存为PDF，将所有图片合并为一个PDF文件
        # pdf_bytes = handwrite(text_to_generate, template, export_pdf=True, file_path=unique_filename)
        # logger.info("pdf generated successfully")
        # # 返回PDF文件
        # # mysql_operation(pdf_io)
        # return send_file(
        #     pdf_bytes,
        #     # attachment_filename="images.pdf",
        #     download_name="images.pdf",
        #     mimetype="application/pdf",
        #     as_attachment=True,
        # )


# @app.after_request
# def cleanup(response):
#     # 从请求上下文中获取文件路径
#     temp_file_path = getattr(request, 'temp_file_path', None)
#     if temp_file_path is not None:
#         # 尝试删除文件
#         try:
#             os.remove(temp_file_path)
#         except Exception as e:
#             app.logger.error(f"Failed to remove temporary PDF file: {e}")
#     # 返回原始响应
#     return response


@app.route("/api/textfileprocess", methods=["POST"])
@limiter.limit("200 per 5 minute")
def textfileprocess():
    try:
        if "file" not in request.files:
            logger.error("No file part in the request")
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files["file"]
        original_filename = file.filename
        logger.info(f"Received file: {original_filename}")
        
        if not original_filename:
            logger.error("Empty filename")
            return jsonify({"error": "No file part in the request"}), 400

        if file and (
            original_filename.endswith(".docx")
            or original_filename.endswith(".pdf")
            or original_filename.endswith(".doc")
            or original_filename.endswith(".txt")
            or original_filename.endswith(".rtf")
        ):
            # 获取文件扩展名
            file_ext = original_filename.rsplit('.', 1)[-1].lower()
            logger.info(f"File extension: {file_ext}")
            
            # 使用UUID生成安全的文件名，保留扩展名
            safe_filename = f"{uuid.uuid4()}.{file_ext}"
            filepath = os.path.join(".", "textfileprocess", safe_filename)
            logger.info(f"Saving to: {filepath}")
            
            file.save(filepath)
            logger.info(f"File saved successfully")
            
            text = "读取失败"  # Default value for text
            try:
                if original_filename.endswith(".docx"):
                    logger.info("Converting docx to text...")
                    text = convert_docx_to_text(filepath)
                    logger.info(f"Converted text length: {len(text)}")
                elif original_filename.endswith(".pdf"):
                    logger.info("Reading PDF...")
                    text = read_pdf(filepath)
                    logger.info(f"PDF text length: {len(text)}")
                elif original_filename.endswith(".txt") or original_filename.endswith(".rtf"):
                    logger.info("Reading text file...")
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    logger.info(f"Text file length: {len(text)}")
                elif original_filename.endswith(".doc"):
                    text = "doc文件暂不支持"
            except Exception as e:
                logger.error(f"Error reading file: {e}", exc_info=True)
                safe_remove_file(filepath)
                return jsonify({"error": f"Error reading file: {str(e)}"}), 500

            # 删除临时文件
            safe_remove_file(filepath)

            return jsonify({"text": text})

        logger.error(f"Invalid file type: {original_filename}")
        return jsonify({"error": "Invalid file type"}), 400
        
    except Exception as e:
        logger.error(f"Unexpected error in textfileprocess: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/imagefileprocess", methods=["POST"])
@limiter.limit("200 per 5 minute")
def imagefileprocess():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file part in the request"}), 400

    if file and (
        file.filename.endswith(".jpf")
        or file.filename.endswith(".png")
        or file.filename.endswith(".jpg")
        or file.filename.endswith(".jpeg")
    ):
        filename = secure_filename(file.filename)
        filepath = os.path.join("./imagefileprocess", filename)
        file.save(filepath)
        (
            avg_l_whitespace,
            avg_r_whitespace,
            avg_t_whitespace,
            avg_b_whitespace,
            avg_distance,
        ) = identify_distance(filepath)
        safe_remove_file(filepath)
        return jsonify(
            {
                "marginLeft": avg_l_whitespace,
                "marginRight": avg_r_whitespace,
                "marginTop": avg_t_whitespace,
                "marginBottom": avg_b_whitespace,
                "lineSpacing": avg_distance,
            }
        )
    else:
        return jsonify({"error": "Invalid file type"}), 400


def get_filenames_in_dir(directory):
    return [
        f
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f.endswith(".ttf")
    ]


@app.route("/api/fonts_info", methods=["GET"])
def get_fonts_info():
    filenames = get_filenames_in_dir("./font_assets")
    logger.info(f"filenames: {filenames}")
    if filenames == []:
        return jsonify({"error": "fontfile not found"}), 400
    return jsonify(filenames)


def mysql_operation(image_data):
    cursor = current_app.cnx.cursor()
    username = session["username"]
    # 先检查用户是否已存在
    cursor.execute("SELECT * FROM user_images WHERE username=%s", (username,))
    result = cursor.fetchone()

    # 根据查询结果来判断应该插入新纪录还是更新旧纪录
    if result is None:
        # 如果用户不存在，插入新纪录
        sql = "INSERT INTO user_images (username, image) VALUES (%s, %s)"
        params = (username, image_data)
    else:
        # 如果用户已存在，更新旧纪录
        sql = "UPDATE user_images SET image=%s WHERE username=%s"
        params = (image_data, username)
    try:
        pass
        # 执行 SQL 语句
        # 提交到数据库执行
        cursor.execute(sql, params)
        current_app.cnx.commit()
    except Exception as e:
        # 发生错误时回滚
        current_app.cnx.rollback()
        logger.info(f"An error occurred: {e}")


# @app.route("/api/login", methods=["POST"])
# def login():
#     data = request.get_json()
#     username = data.get("username")
#     password = data.get("password")
#     logger.info(f"Received username: {username}")  # 打印接收到的用户名
#     logger.info(f"Received password: {password}")  # 打印接收到的密码
#     try:
#         cursor = current_app.cnx.cursor()
#         cursor.execute(
#             f"SELECT password FROM user_images WHERE username=%s", (username,)
#         )
#         result = cursor.fetchone()
#     except Exception as e:
#         logger.error(f"An error occurred: {e}")
#         return jsonify({"error": "An error occurred"}), 500

#     if result and result[0] == password:
#         session["username"] = username
#         session.permanent = True
#         logger.info(f"Login success for user: {username}")
#         return {"status": "success"}, 200
#     else:
#         logger.error(f"Login failed for user: {username}")
#         return {
#             "status": "failed",
#             "error": "Login failed. Check your username and password.",
#         }, 401


# @app.route("/api/register", methods=["POST"])
# def register():
#     data = request.get_json()
#     username = data.get("username")
#     password = data.get("password")
#     try:
#         cursor = current_app.cnx.cursor()
#         cursor.execute(f"SELECT * FROM user_images WHERE username=%s", (username,))
#         result = cursor.fetchone()
#     except Exception as e:
#         logger.error(f"An error occurred: {e}")
#         return jsonify({"error": "An error occurred"}), 500

#     if not result:
#         try:
#             cursor.execute(
#                 f"INSERT INTO user_images (username, password) VALUES (%s, %s)",
#                 (username, password),
#             )
#             current_app.cnx.commit()
#             session["username"] = username
#             logger.info(f"User: {username} registered successfully.")
#             return jsonify(
#                 {
#                     "status": "success",
#                     "message": "Account created successfully. You can now log in.",
#                 }
#             )
#         except mysql.connector.Error as err:
#             logger.error(f"Failed to insert user: {username} into DB. Error: {err}")
#             return (
#                 jsonify(
#                     {
#                         "status": "fail",
#                         "message": "Error occurred during registration.",
#                     }
#                 ),
#                 500,
#             )
#     else:
#         logger.error(f"Username: {username} already exists.")
#         return (
#             jsonify(
#                 {
#                     "status": "fail",
#                     "message": "Username already exists. Choose a different one.",
#                 }
#             ),
#             400,
#         )


# 捕获所有未捕获的异常，返回给前端，只能用于生产环境7.12
# @app.errorhandler(Exception)
# def handle_exception(e):
#     # Pass the error to Flask's default error handling.
#       tb = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
#     response = {
#
#             "type": type(e).__name__,  # The type of the exception
#             "message": str(e),  # The message of the exception
#
#     }
#     return jsonify(response), 500


# @app.before_request
# def before_request():
#     if enable_user_auth.lower() == "true":
#         current_app.cnx = mysql.connector.connect(
#             host=mysql_host, user="myuser", password="mypassword", database="mydatabase"
#         )
#     else:
#         pass


# ==================== 小程序专用 API ====================
import base64
import uuid

# 存储临时下载文件的字典 {file_id: (file_path, expire_time)}
temp_download_files = {}


@app.route("/api/miniprogram/preview", methods=["POST"])
@limiter.limit("200 per 5 minute")
@handle_exceptions
def miniprogram_preview():
    """
    小程序预览接口 - 返回 base64 编码的图片
    更适合小程序直接展示
    """
    cpu_usage = psutil.cpu_percent(interval=1)
    if cpu_usage > 90:
        return jsonify({"status": "error", "message": "服务器繁忙，请稍后再试"}), 429

    data = request.form
    
    # 获取用户信息和会员状态
    openid = request.headers.get("X-Openid") or data.get("openid")
    use_free_mode = data.get("use_free_mode", "false") == "true"  # 是否使用免费模式
    
    is_vip = False
    user = None
    user_is_admin = False
    if openid:
        user = get_or_create_user(openid)
        if user:
            is_vip, _, _ = check_user_membership(user)
            # 管理员视为VIP，无限制使用所有功能
            user_is_admin = is_admin(openid)
            if user_is_admin:
                is_vip = True
    
    # 验证必要字段
    required_fields = [
        "text", "font_size", "line_spacing", "fill",
        "left_margin", "top_margin", "right_margin", "bottom_margin",
        "word_spacing", "line_spacing_sigma", "font_size_sigma",
        "word_spacing_sigma", "perturb_x_sigma", "perturb_y_sigma", "perturb_theta_sigma"
    ]
    
    for field in required_fields:
        if field not in data:
            return jsonify({"status": "error", "message": f"缺少必要参数: {field}"}), 400
    
    text_to_generate = data["text"]
    if not text_to_generate.strip():
        return jsonify({"status": "error", "message": "请输入要生成的文字"}), 400
    
    # 预处理文本：移除可能导致黑色方块的控制字符
    text_to_generate = clean_text_for_handwrite(text_to_generate)
    
    # 取消对免费模式的字数限制 — 所有用户均可生成全部内容
    char_count = len(text_to_generate.replace('\n', '').replace(' ', ''))
    need_watermark = False # 预览不再由后端添加水印，改为前端添加
    
    logger.info(f"Preview request: is_vip={is_vip}, need_watermark={need_watermark}")

    # 处理背景图片
    paper_type = data.get("paper_type", "plain")
    
    # 获取纸张尺寸参数（必须有）
    if "width" not in data or "height" not in data:
        return jsonify({"status": "error", "message": "请指定纸张宽高"}), 400
    
    line_spacing = int(data.get("line_spacing", 30))
    top_margin = int(data.get("top_margin", 0))
    bottom_margin = int(data.get("bottom_margin", 0))
    left_margin = int(data.get("left_margin", 0))
    right_margin = int(data.get("right_margin", 0))
    width = int(data["width"])
    height = int(data["height"])
    font_size = int(data.get("font_size", 0))
    isUnderlined = data.get("isUnderlined", "false") == "true"
    line_color = data.get("line_color", "red")
    
    # 优先检查是否有上传的自定义背景图片
    background_file = request.files.get("background_image")
    if background_file is not None:
        # 使用上传的背景图片，缩放到用户选择的纸张尺寸
        image_data = io.BytesIO(background_file.read())
        background_image = Image.open(image_data)
        if background_image.mode in ("RGBA", "LA"):
            background_image = background_image.convert("RGB")
        # 缩放图片到用户选择的纸张尺寸
        background_image = background_image.resize((width, height), Image.Resampling.LANCZOS)
    else:
        # 没有上传背景图片，使用 create_notebook_image 生成背景
        background_image = create_notebook_image(
            width, height, line_spacing, top_margin, bottom_margin,
            left_margin, right_margin, font_size, isUnderlined, line_color, paper_type
        )
    
    # 处理字体
    if "font_file" in request.files:
        font_data = request.files["font_file"].read()
        font = ImageFont.truetype(io.BytesIO(font_data), size=int(data["font_size"]))
    elif "font_option" in data and data["font_option"]:
        font_path = os.path.join("./font_assets", data["font_option"])
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, size=int(data["font_size"]))
        else:
            return jsonify({"status": "error", "message": f"字体不存在: {data['font_option']}"}), 400
    else:
        return jsonify({"status": "error", "message": "请选择字体"}), 400
    
    # 确定是否使用网格布局（方格纸模式）
    use_grid_layout = paper_type == "grid"
    features = {Feature.GRID_LAYOUT} if use_grid_layout else set()
    
    # 方格纸模式下，行间距需要与格子大小一致
    grid_cell_size = int(int(data["font_size"]) * 1.15) if use_grid_layout else int(data["line_spacing"])
    
    # 创建模板
    template = Template(
        background=background_image,
        font=font,
        line_spacing=grid_cell_size,
        left_margin=int(data["left_margin"]),
        top_margin=int(data["top_margin"]),
        right_margin=int(data["right_margin"]) - int(data.get("word_spacing", 0)) * 2 if not use_grid_layout else int(data["right_margin"]),
        bottom_margin=int(data["bottom_margin"]),
        word_spacing=int(data.get("word_spacing", 0)) if not use_grid_layout else 0,
        line_spacing_sigma=int(data["line_spacing_sigma"]) if not use_grid_layout else 0,
        font_size_sigma=int(data["font_size_sigma"]) if not use_grid_layout else 0,
        word_spacing_sigma=int(data["word_spacing_sigma"]) if not use_grid_layout else 0,
        end_chars="，。" if not use_grid_layout else "",
        perturb_x_sigma=int(data["perturb_x_sigma"]) if not use_grid_layout else 2,
        perturb_y_sigma=int(data["perturb_y_sigma"]) if not use_grid_layout else 2,
        perturb_theta_sigma=float(data["perturb_theta_sigma"]),
        strikethrough_probability=float(data.get("strikethrough_probability", 0)),
        strikethrough_length_sigma=float(data.get("strikethrough_length_sigma", 0)),
        strikethrough_width_sigma=float(data.get("strikethrough_width_sigma", 0)),
        strikethrough_angle_sigma=float(data.get("strikethrough_angle_sigma", 0)),
        strikethrough_width=float(data.get("strikethrough_width", 1)),
        ink_depth_sigma=float(data.get("ink_depth_sigma", 0)),
        features=features,
    )
    
    # 生成图片
    # 过滤字体不支持的字符
    text_to_generate = filter_unsupported_chars(text_to_generate, font)
    images = list(handwrite(text_to_generate, template))
    
    # 非会员添加水印（实际实现已移除）
    if need_watermark:
        images = add_watermark_to_images(images)
    
    # 记录使用日志（has_watermark 固定为 False，因为已移除水印）
    user_id = user['id'] if user else None
    log_usage(user_id, openid, 'preview', char_count, False)
    
    # 生成所有页面的 base64 图片
    image_list = []
    for i, im in enumerate(images):
        img_buffer = io.BytesIO()
        im.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        image_list.append(f"data:image/png;base64,{img_base64}")
        im.close()
    
    if image_list:
        return jsonify({
            "status": "success",
            "images": image_list,
            "total": len(image_list),
            "charCount": char_count,
            "message": f"预览生成成功，共 {len(image_list)} 页"
        })
    
    return jsonify({"status": "error", "message": "生成失败"}), 500


@app.route("/api/miniprogram/generate", methods=["POST"])
@limiter.limit("100 per 5 minute")
@handle_exceptions
def miniprogram_generate():
    """
    小程序生成接口 - 返回文件下载链接
    生成完整的图片包或 PDF
    """
    cpu_usage = psutil.cpu_percent(interval=1)
    if cpu_usage > 90:
        return jsonify({"status": "error", "message": "服务器繁忙，请稍后再试"}), 429

    data = request.form
    
    # 获取用户信息和会员状态
    openid = request.headers.get("X-Openid") or data.get("openid")
    use_free_mode = data.get("use_free_mode", "false") == "true"  # 是否使用免费模式
    
    is_vip = False
    user = None
    user_is_admin = False
    if openid:
        user = get_or_create_user(openid)
        if user:
            is_vip, _, _ = check_user_membership(user)
            # 管理员视为VIP，无限制使用所有功能
            user_is_admin = is_admin(openid)
            if user_is_admin:
                is_vip = True
    
    # 验证必要字段
    required_fields = [
        "text", "font_size", "line_spacing", "fill",
        "left_margin", "top_margin", "right_margin", "bottom_margin",
        "word_spacing", "line_spacing_sigma", "font_size_sigma",
        "word_spacing_sigma", "perturb_x_sigma", "perturb_y_sigma", "perturb_theta_sigma"
    ]
    
    for field in required_fields:
        if field not in data:
            return jsonify({"status": "error", "message": f"缺少必要参数: {field}"}), 400
    
    text_to_generate = data["text"]
    if not text_to_generate.strip():
        return jsonify({"status": "error", "message": "请输入要生成的文字"}), 400
    
    # 验证相思豆（如果提供了）
    loveseed_code = data.get("loveseed_code")
    if loveseed_code:
        try:
            # 验证相思豆
            loveseed = verify_loveseed_code(loveseed_code)
            if loveseed:
                # 扣除次数
                consume_loveseed_download(loveseed_code, openid, 'generate_pdf' if data.get("pdf_save", "false") == "true" else 'generate_image', len(text_to_generate))
                is_vip = True  # 相思豆有效，视为VIP（无水印）
                need_watermark = False
        except Exception as e:
            logger.error(f"相思豆验证失败: {e}")
            return jsonify({"status": "error", "message": str(e)}), 400
    elif not is_vip and not use_free_mode:
        # 如果不是VIP且没有提供相思豆，且不是免费模式，则要求相思豆
        # 但为了兼容旧版本，暂时允许生成带水印的图片
        # 如果前端明确要求必须有相思豆才能下载（如本次需求），则可以在这里强制检查
        # 根据需求：如果想下载图片或者PDF，都需要输入相思豆
        if not data.get("preview", "false") == "true": # 如果不是预览
             return jsonify({"status": "error", "message": "请先获取相思豆"}), 402

    # 预处理文本：移除可能导致黑色方块的控制字符
    text_to_generate = clean_text_for_handwrite(text_to_generate)
    
    # 取消对免费模式的字数限制 — 所有用户均可生成全部内容
    char_count = len(text_to_generate.replace('\n', '').replace(' ', ''))
    need_watermark = not is_vip  # 非会员仍然会看到水印
    
    zip_mode = data.get("zip_save", "false") == "true"
    pdf_mode = data.get("pdf_save", "false") == "true"
    paper_type = data.get("paper_type", "plain")
    
    # 获取纸张尺寸参数（必须有）
    if "width" not in data or "height" not in data:
        return jsonify({"status": "error", "message": "请指定纸张宽高"}), 400
    
    line_spacing = int(data.get("line_spacing", 30))
    top_margin = int(data.get("top_margin", 0))
    bottom_margin = int(data.get("bottom_margin", 0))
    left_margin = int(data.get("left_margin", 0))
    right_margin = int(data.get("right_margin", 0))
    width = int(data["width"])
    height = int(data["height"])
    font_size = int(data.get("font_size", 0))
    isUnderlined = data.get("isUnderlined", "false") == "true"
    line_color = data.get("line_color", "red")
    
    # 优先检查是否有上传的自定义背景图片
    background_file = request.files.get("background_image")
    if background_file is not None:
        # 使用上传的背景图片，缩放到用户选择的纸张尺寸
        image_data = io.BytesIO(background_file.read())
        background_image = Image.open(image_data)
        if background_image.mode in ("RGBA", "LA"):
            background_image = background_image.convert("RGB")
        # 缩放图片到用户选择的纸张尺寸
        background_image = background_image.resize((width, height), Image.Resampling.LANCZOS)
    else:
        # 没有上传背景图片，使用 create_notebook_image 生成背景
        background_image = create_notebook_image(
            width, height, line_spacing, top_margin, bottom_margin,
            left_margin, right_margin, font_size, isUnderlined, line_color, paper_type
        )
    
    # 确定是否使用网格布局（方格纸模式）
    use_grid_layout = paper_type == "grid"
    features = {Feature.GRID_LAYOUT} if use_grid_layout else set()
    
    # 处理字体
    if "font_file" in request.files:
        font_data = request.files["font_file"].read()
        font = ImageFont.truetype(io.BytesIO(font_data), size=int(data["font_size"]))
    elif "font_option" in data and data["font_option"]:
        font_path = os.path.join("./font_assets", data["font_option"])
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, size=int(data["font_size"]))
        else:
            return jsonify({"status": "error", "message": f"字体不存在: {data['font_option']}"}), 400
    else:
        return jsonify({"status": "error", "message": "请选择字体"}), 400
    
    # 方格纸模式下，行间距需要与格子大小一致
    grid_cell_size = int(int(data["font_size"]) * 1.15) if use_grid_layout else int(data["line_spacing"])
    
    # 创建模板
    template = Template(
        background=background_image,
        font=font,
        line_spacing=grid_cell_size,
        left_margin=int(data["left_margin"]),
        top_margin=int(data["top_margin"]),
        right_margin=int(data["right_margin"]) - int(data.get("word_spacing", 0)) * 2 if not use_grid_layout else int(data["right_margin"]),
        bottom_margin=int(data["bottom_margin"]),
        word_spacing=int(data.get("word_spacing", 0)) if not use_grid_layout else 0,
        line_spacing_sigma=int(data["line_spacing_sigma"]) if not use_grid_layout else 0,
        font_size_sigma=int(data["font_size_sigma"]) if not use_grid_layout else 0,
        word_spacing_sigma=int(data["word_spacing_sigma"]) if not use_grid_layout else 0,
        end_chars="，。" if not use_grid_layout else "",
        perturb_x_sigma=int(data["perturb_x_sigma"]) if not use_grid_layout else 2,
        perturb_y_sigma=int(data["perturb_y_sigma"]) if not use_grid_layout else 2,
        perturb_theta_sigma=float(data["perturb_theta_sigma"]),
        strikethrough_probability=float(data.get("strikethrough_probability", 0)),
        strikethrough_length_sigma=float(data.get("strikethrough_length_sigma", 0)),
        strikethrough_width_sigma=float(data.get("strikethrough_width_sigma", 0)),
        strikethrough_angle_sigma=float(data.get("strikethrough_angle_sigma", 0)),
        strikethrough_width=float(data.get("strikethrough_width", 1)),
        ink_depth_sigma=float(data.get("ink_depth_sigma", 0)),
        features=features,
    )
    
    # 生成图片
    # 过滤字体不支持的字符
    text_to_generate = filter_unsupported_chars(text_to_generate, font)
    images = list(handwrite(text_to_generate, template))
    
    # 非会员添加水印（实际实现已移除）
    if need_watermark:
        images = add_watermark_to_images(images)

    # 记录使用日志（has_watermark 固定为 False，因为已移除水印）
    user_id = user['id'] if user else None
    action_type = 'generate_pdf' if data.get("pdf_save", "false") == "true" else 'generate_image'
    log_usage(user_id, openid, action_type, char_count, False)
    
    # 创建临时目录
    project_temp_base = "./temp"
    os.makedirs(project_temp_base, exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir=project_temp_base)
    
    try:
        image_paths = []
        for i, im in enumerate(images):
            image_path = os.path.join(temp_dir, f"{i}.png")
            if safe_save_and_close_image(im, image_path):
                image_paths.append(image_path)
            del im
        
        # 生成文件ID
        file_id = str(uuid.uuid4())
        
        if pdf_mode:
            # 生成 PDF
            pdf_path = os.path.join(project_temp_base, f"{file_id}.pdf")
            generate_pdf(image_paths, pdf_path)
            file_path = pdf_path
            file_type = "pdf"
            mimetype = "application/pdf"
            
            # 存储文件信息（1小时后过期）
            expire_time = time.time() + 3600
            temp_download_files[file_id] = (file_path, expire_time, mimetype)
            
            # 清理临时图片目录
            safe_remove_directory(temp_dir)
            
            return jsonify({
                "status": "success",
                "file_id": file_id,
                "file_type": file_type,
                "download_url": f"/api/miniprogram/download/{file_id}",
                "page_count": len(image_paths),
                "expires_in": 3600,
                "message": "PDF生成成功，请在1小时内下载"
            })
        elif zip_mode:
            # 生成 ZIP
            zip_path = os.path.join(project_temp_base, f"{file_id}.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for i, image_path in enumerate(image_paths):
                    zf.write(image_path, f"page_{i+1}.png")
            
            file_path = zip_path
            file_type = "zip"
            mimetype = "application/zip"
            
            # 存储文件信息（1小时后过期）
            expire_time = time.time() + 3600
            temp_download_files[file_id] = (file_path, expire_time, mimetype)
            
            # 清理临时图片目录
            safe_remove_directory(temp_dir)
            
            return jsonify({
                "status": "success",
                "file_id": file_id,
                "file_type": file_type,
                "download_url": f"/api/miniprogram/download/{file_id}",
                "page_count": len(image_paths),
                "expires_in": 3600,
                "message": "图片打包成功，请在1小时内下载"
            })
        else:
            # 返回 base64 图片数组（用于保存到相册）
            image_list = []
            for image_path in image_paths:
                with open(image_path, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode("utf-8")
                    image_list.append(f"data:image/png;base64,{img_base64}")
            
            # 清理临时图片目录
            safe_remove_directory(temp_dir)
            
            return jsonify({
                "status": "success",
                "images": image_list,
                "page_count": len(image_list),
                "message": f"图片生成成功，共 {len(image_list)} 页"
            })
        
    except Exception as e:
        safe_remove_directory(temp_dir)
        logger.error(f"生成失败: {e}")
        return jsonify({"status": "error", "message": f"生成失败: {str(e)}"}), 500


@app.route("/api/miniprogram/download/<file_id>", methods=["GET"])
def miniprogram_download(file_id):
    """
    小程序下载接口 - 根据 file_id 下载生成的文件
    """
    if file_id not in temp_download_files:
        return jsonify({"status": "error", "message": "文件不存在或已过期"}), 404
    
    file_path, expire_time, mimetype = temp_download_files[file_id]
    
    # 检查是否过期
    if time.time() > expire_time:
        # 清理过期文件
        safe_remove_file(file_path)
        del temp_download_files[file_id]
        return jsonify({"status": "error", "message": "文件已过期，请重新生成"}), 410
    
    if not os.path.exists(file_path):
        del temp_download_files[file_id]
        return jsonify({"status": "error", "message": "文件不存在"}), 404
    
    # 确定文件名
    if mimetype == "application/pdf":
        download_name = "handwriting.pdf"
    else:
        download_name = "images.zip"
    
    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=download_name
    )


@app.route("/api/miniprogram/fonts", methods=["GET"])
def miniprogram_fonts():
    """
    获取可用字体列表（小程序专用）
    """
    directory = "./font_assets"
    fonts = []
    
    if os.path.exists(directory):
        for f in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(".ttf"):
                fonts.append({
                    "name": f[:-4],  # 去掉后缀
                    "filename": f
                })
    
    return jsonify({
        "status": "success",
        "fonts": fonts
    })


# ==================== 用户认证与会员接口 ====================

@app.route("/api/miniprogram/login", methods=["POST"])
@limiter.limit("30 per minute")
def miniprogram_login():
    """
    微信小程序登录
    通过 wx.login() 获取的 code 换取用户信息
    """
    data = request.get_json() or request.form.to_dict()
    
    code = data.get("code")
    nickname = data.get("nickname", "")
    avatar_url = data.get("avatarUrl", "")
    
    if not code:
        return jsonify({"status": "error", "message": "缺少登录凭证"}), 400
    
    # 通过 code 换取 openid
    openid = wx_code_to_openid(code)
    if not openid:
        return jsonify({"status": "error", "message": "登录失败，请重试"}), 400
    
    # 获取或创建用户
    user = get_or_create_user(openid, nickname, avatar_url)
    if not user:
        return jsonify({"status": "error", "message": "用户创建失败"}), 500
    
    # 检查会员状态
    is_vip, member_type, days_remaining = check_user_membership(user)
    
    # 生成简单的 token（实际生产环境应使用 JWT）
    token = f"{openid}_{int(time.time())}"
    
    return jsonify({
        "status": "success",
        "data": {
            "token": token,
            "openid": openid,
            "nickname": user.get("nickname", ""),
            "avatarUrl": user.get("avatar_url", ""),
            "isVip": is_vip,
            "memberType": member_type,
            "daysRemaining": days_remaining,
            # freeCharLimit removed — no client-side limit enforced
        }
    })


@app.route("/api/miniprogram/user/info", methods=["GET"])
@limiter.limit("60 per minute")
def miniprogram_user_info():
    """
    获取用户信息
    """
    openid = request.headers.get("X-Openid") or request.args.get("openid")
    
    if not openid:
        return jsonify({
            "status": "success",
            "data": {
                "isLoggedIn": False,
                "isVip": False,
                "isAdmin": False,
                "memberType": "guest",
                # freeCharLimit removed
            }
        })
    
    user = get_or_create_user(openid)
    if not user:
        return jsonify({
            "status": "success",
            "data": {
                "isLoggedIn": False,
                "isVip": False,
                "isAdmin": False,
                "memberType": "guest",
                # freeCharLimit removed
            }
        })
    
    is_vip, member_type, days_remaining = check_user_membership(user)
    user_is_admin = is_admin(openid)
    
    # 管理员视为VIP
    if user_is_admin:
        is_vip = True
    
    return jsonify({
        "status": "success",
        "data": {
            "isLoggedIn": True,
            "openid": openid,
            "nickname": user.get("nickname", ""),
            "avatarUrl": user.get("avatar_url", ""),
            "isVip": is_vip,
            "isAdmin": user_is_admin,
            "memberType": member_type if not user_is_admin else "admin",
            "daysRemaining": days_remaining if not user_is_admin else 99999,
            "totalCharsGenerated": user.get("total_chars_generated", 0),
                # freeCharLimit removed
        }
    })


@app.route("/api/miniprogram/packages", methods=["GET"])
@limiter.limit("60 per minute")
def miniprogram_packages():
    """
    获取套餐列表
    """
    packages = get_packages()
    
    return jsonify({
        "status": "success",
        "data": {
            "packages": packages,
            # freeCharLimit removed
            "appName": APP_NAME
        }
    })


@app.route('/api/dev/admin-openid', methods=['GET'])
def dev_admin_openid():
    """
    开发用接口：在 LOCAL_TEST_MODE 下返回测试管理员 openid。
    仅用于本地开发和调试，生产环境应当禁用或移除。
    """
    try:
        if str(os.getenv('LOCAL_TEST_MODE', 'true')).lower() == 'true' or LOCAL_TEST_MODE:
            return jsonify({ 'status': 'success', 'adminOpenid': TEST_ADMIN_OPENID })
        else:
            return jsonify({ 'status': 'error', 'message': 'not available' }), 403
    except Exception as e:
        return jsonify({ 'status': 'error', 'message': str(e) }), 500


@app.route("/api/miniprogram/order/create", methods=["POST"])
def miniprogram_create_order():
    return jsonify({"status": "error", "message": "订单创建已被移除"}), 410


@app.route("/api/miniprogram/order/complete", methods=["POST"])
def miniprogram_complete_order():
    return jsonify({"status": "error", "message": "订单完成接口已被移除"}), 410


@app.route("/api/miniprogram/pay/notify", methods=["POST"])
def miniprogram_pay_notify():
    """
    微信支付回调通知
    """
    # TODO: 实现微信支付回调验证和处理
    # 1. 验证签名
    # 2. 解析订单信息
    # 3. 调用 complete_order 完成订单
    
    return """<xml>
        <return_code><![CDATA[SUCCESS]]></return_code>
        <return_msg><![CDATA[OK]]></return_msg>
    </xml>"""


# ==================== 管理员API ====================

@app.route("/api/miniprogram/admin/check", methods=["GET"])
@limiter.limit("30 per minute")
def check_admin_status():
    """
    检查当前用户是否是管理员
    """
    openid = request.headers.get("X-WX-Openid")
    
    if not openid:
        return jsonify({"status": "error", "message": "未获取到用户信息"}), 401
    
    admin_status = is_admin(openid)
    
    return jsonify({
        "status": "success",
        "isAdmin": admin_status
    })


@app.route("/api/miniprogram/admin/stats", methods=["GET"])
@limiter.limit("30 per minute")
def admin_get_stats():
    """
    获取会员统计数据（需要管理员权限）
    """
    openid = request.headers.get("X-WX-Openid")
    
    if not openid:
        return jsonify({"status": "error", "message": "未获取到用户信息"}), 401
    
    if not is_admin(openid):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    stats = get_membership_statistics()
    
    return jsonify({
        "status": "success",
        "data": stats
    })


@app.route("/api/miniprogram/admin/users", methods=["GET"])
@limiter.limit("30 per minute")
def admin_get_users():
    """
    获取用户列表（需要管理员权限）
    """
    openid = request.headers.get("X-WX-Openid")
    
    if not openid:
        return jsonify({"status": "error", "message": "未获取到用户信息"}), 401
    
    if not is_admin(openid):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("pageSize", 20, type=int)
    
    users = get_all_users(page, page_size)
    
    return jsonify({
        "status": "success",
        "data": users
    })


@app.route("/api/miniprogram/admin/users/search", methods=["GET"])
@limiter.limit("30 per minute")
def admin_search_users():
    """
    搜索用户（需要管理员权限）
    """
    openid = request.headers.get("X-WX-Openid")
    
    if not openid:
        return jsonify({"status": "error", "message": "未获取到用户信息"}), 401
    
    if not is_admin(openid):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    keyword = request.args.get("keyword", "")
    
    if not keyword:
        return jsonify({"status": "error", "message": "搜索关键词不能为空"}), 400
    
    users = search_users(keyword)
    
    return jsonify({
        "status": "success",
        "data": users
    })


@app.route("/api/miniprogram/admin/grant-membership", methods=["POST"])
@limiter.limit("30 per minute")
def admin_grant_member():
    """
    管理员给用户开通会员（需要管理员权限）
    """
    openid = request.headers.get("X-WX-Openid")
    
    if not openid:
        return jsonify({"status": "error", "message": "未获取到用户信息"}), 401
    
    if not is_admin(openid):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    data = request.get_json() or request.form.to_dict()
    
    target_openid = data.get("targetOpenid")
    member_type = data.get("memberType", "monthly")
    days = data.get("days", 30)
    
    if not target_openid:
        return jsonify({"status": "error", "message": "目标用户openid不能为空"}), 400
    
    try:
        days = int(days)
    except:
        days = 30
    
    success, message = admin_grant_membership(target_openid, member_type, days)
    
    if success:
        return jsonify({
            "status": "success",
            "message": message
        })
    else:
        return jsonify({"status": "error", "message": message}), 400


@app.route("/api/miniprogram/admin/set-admin", methods=["POST"])
@limiter.limit("10 per minute")
def admin_set_user_admin():
    """
    设置用户为管理员（需要管理员权限）
    """
    openid = request.headers.get("X-WX-Openid")
    
    if not openid:
        return jsonify({"status": "error", "message": "未获取到用户信息"}), 401
    
    if not is_admin(openid):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    data = request.get_json() or request.form.to_dict()
    
    target_openid = data.get("targetOpenid")
    is_admin_flag = data.get("isAdmin", False)
    
    if not target_openid:
        return jsonify({"status": "error", "message": "目标用户openid不能为空"}), 400
    
    success = set_user_admin(target_openid, is_admin_flag)
    
    if success:
        return jsonify({
            "status": "success",
            "message": f"用户管理员权限已{'开启' if is_admin_flag else '关闭'}"
        })
    else:
        return jsonify({"status": "error", "message": "设置失败"}), 400


@app.after_request
def after_request(response):
    if enable_user_auth.lower() == "true":
        if hasattr(current_app, "cnx"):
            current_app.cnx.close()
        # 仅用于调试 7.13
        # session.clear()
        return response
    else:
        print(response)
        return response


# ==================== 相思豆系统 API ====================

@app.route("/api/loveseed/packages", methods=["GET"])
@limiter.limit("200 per 5 minute")
def get_loveseed_packages():
    """
    获取所有可用套餐
    """
    try:
        packages = get_all_packages()
        return jsonify({
            "status": "success",
            "packages": packages
        })
    except Exception as e:
        logger.error(f"获取套餐失败: {e}")
        return jsonify({"status": "error", "message": "获取套餐失败"}), 500


@app.route("/api/payment/create-charge", methods=["POST"])
@limiter.limit("50 per 5 minute")
def create_payment_charge_endpoint():
    """
    创建支付凭据（Ping++）
    """
    try:
        from loveseed_service import create_payment_order
        
        data = request.get_json()
        package_id = data.get("package_id")
        channel = data.get("channel", "wx_pub_qr")  # 默认微信扫码
        client_ip = request.remote_addr or "127.0.0.1"
        
        if not package_id:
            return jsonify({"status": "error", "message": "缺少套餐ID"}), 400
        
        result = create_payment_order(package_id, channel, client_ip)
        
        return jsonify({
            "status": "success",
            "data": {
                "charge": result['charge'],
                "order_no": result['order_no'],
                "package": result['package']
            }
        })
    except Exception as e:
        logger.error(f"创建支付凭据失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/payment/check-status", methods=["POST"])
@limiter.limit("100 per 5 minute")
def check_payment_status_endpoint():
    """
    查询支付状态
    """
    try:
        from loveseed_service import check_payment_status, handle_payment_success
        
        data = request.get_json()
        charge_id = data.get("charge_id")
        
        if not charge_id:
            return jsonify({"status": "error", "message": "缺少charge_id"}), 400
        
        status = check_payment_status(charge_id)
        
        # 如果已支付，生成相思豆
        if status['paid']:
            loveseed_info = handle_payment_success(status['order_no'])
            return jsonify({
                "status": "success",
                "paid": True,
                "loveseed_info": loveseed_info
            })
        else:
            return jsonify({
                "status": "success",
                "paid": False
            })
    except Exception as e:
        logger.error(f"查询支付状态失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/payment/webhook", methods=["POST"])
def payment_webhook():
    """
    Ping++ Webhook 回调
    接收支付成功通知
    """
    try:
        from loveseed_service import handle_payment_success
        from payment_service import verify_webhook_signature
        
        # 验证签名
        signature = request.headers.get('X-Pingplusplus-Signature', '')
        raw_data = request.get_data()
        
        if not verify_webhook_signature(raw_data, signature):
            logger.warning("支付回调签名验证失败")
            return jsonify({"status": "error", "message": "签名验证失败"}), 401
        
        # 解析事件
        event = request.get_json()
        event_type = event.get('type')
        
        if event_type == 'charge.succeeded':
            # 支付成功
            charge = event.get('data', {}).get('object', {})
            order_no = charge.get('order_no')
            
            if order_no:
                loveseed_info = handle_payment_success(order_no)
                logger.info(f"支付成功: {order_no}, 相思豆: {loveseed_info['loveseed_code']}")
        
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"处理支付回调失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/loveseed/create-order", methods=["POST"])
@limiter.limit("50 per 5 minute")
def create_loveseed_order_endpoint():
    """
    创建订单并生成相思豆
    支付完成后调用
    """
    try:
        data = request.get_json()
        package_id = data.get("package_id")
        amount = data.get("amount")
        
        if not package_id or amount is None:
            return jsonify({"status": "error", "message": "缺少必要参数"}), 400
        
        result = create_loveseed_order(package_id, amount)
        
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        logger.error(f"创建订单失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/loveseed/verify", methods=["POST"])
@limiter.limit("100 per 5 minute")
def verify_loveseed():
    """
    验证相思豆是否有效
    """
    try:
        data = request.get_json()
        loveseed_code = data.get("loveseed_code", "").strip()
        
        if not loveseed_code:
            return jsonify({"status": "error", "message": "请输入相思豆"}), 400
        
        if len(loveseed_code) != 6 or not loveseed_code.isdigit():
            return jsonify({"status": "error", "message": "相思豆格式不正确，应为6位数字"}), 400
        
        loveseed_info = verify_loveseed_code(loveseed_code)
        
        if loveseed_info:
            return jsonify({
                "status": "success",
                "valid": True,
                "data": loveseed_info
            })
        else:
            return jsonify({
                "status": "error",
                "valid": False,
                "message": "相思豆无效或已用尽"
            }), 400
    except Exception as e:
        logger.error(f"验证相思豆失败: {e}")
        return jsonify({"status": "error", "message": "验证失败"}), 500


@app.route("/api/loveseed/consume", methods=["POST"])
@limiter.limit("100 per 5 minute")
def consume_loveseed():
    """
    消耗一次下载次数
    小程序生成图片/PDF时调用
    """
    try:
        data = request.get_json()
        loveseed_code = data.get("loveseed_code", "").strip()
        openid = request.headers.get("X-Openid") or data.get("openid")
        action_type = data.get("action_type", "generate_image")
        char_count = data.get("char_count", 0)
        
        if not loveseed_code:
            return jsonify({"status": "error", "message": "请输入相思豆"}), 400
        
        result = consume_loveseed_download(loveseed_code, openid, action_type, char_count)
        
        if result:
            return jsonify({
                "status": "success",
                "data": result,
                "message": f"生成成功！剩余{result['remaining_downloads']}次下载机会"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "相思豆无效或已用尽"
            }), 400
    except Exception as e:
        logger.error(f"消耗下载次数失败: {e}")
        return jsonify({"status": "error", "message": "消耗失败"}), 500


# ==================== 管理员相思豆管理API ====================

@app.route("/api/admin/loveseed/orders", methods=["GET"])
@limiter.limit("30 per minute")
def admin_get_orders():
    """
    获取所有订单列表（管理员）
    """
    # 简单的管理员验证（可以改用更安全的方式）
    admin_token = request.headers.get("X-Admin-Token") or request.args.get("admin_token")
    
    # 测试模式或验证管理员token
    if not LOCAL_TEST_MODE and admin_token != os.getenv("ADMIN_TOKEN", "admin123"):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    try:
        orders = get_all_orders_admin()
        return jsonify({
            "status": "success",
            "data": orders
        })
    except Exception as e:
        logger.error(f"获取订单列表失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/loveseed/codes", methods=["GET"])
@limiter.limit("30 per minute")
def admin_get_loveseed_codes():
    """
    获取所有相思豆码列表（管理员）
    """
    admin_token = request.headers.get("X-Admin-Token") or request.args.get("admin_token")
    
    if not LOCAL_TEST_MODE and admin_token != os.getenv("ADMIN_TOKEN", "admin123"):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    try:
        codes = get_all_loveseed_codes_admin()
        return jsonify({
            "status": "success",
            "data": codes
        })
    except Exception as e:
        logger.error(f"获取相思豆码列表失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/loveseed/create", methods=["POST"])
@limiter.limit("10 per minute")
def admin_create_loveseed():
    """
    手动创建相思豆码（管理员）
    """
    admin_token = request.headers.get("X-Admin-Token") or request.json.get("admin_token") if request.json else None
    
    if not LOCAL_TEST_MODE and admin_token != os.getenv("ADMIN_TOKEN", "admin123"):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    try:
        data = request.get_json()
        loveseed_code = data.get("loveseed_code", "").strip()
        download_count = data.get("download_count")
        
        if not loveseed_code or not download_count:
            return jsonify({"status": "error", "message": "缺少必要参数"}), 400
        
        if len(loveseed_code) != 6 or not loveseed_code.isdigit():
            return jsonify({"status": "error", "message": "相思豆码必须是6位数字"}), 400
        
        try:
            download_count = int(download_count)
            if download_count <= 0:
                return jsonify({"status": "error", "message": "下载次数必须大于0"}), 400
        except ValueError:
            return jsonify({"status": "error", "message": "下载次数必须是数字"}), 400
        
        result = create_loveseed_code_manual(loveseed_code, download_count)
        
        if result:
            return jsonify({
                "status": "success",
                "message": "创建成功",
                "data": result
            })
        else:
            return jsonify({"status": "error", "message": "创建失败，相思豆码可能已存在"}), 400
    except Exception as e:
        logger.error(f"创建相思豆码失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/loveseed/delete", methods=["POST"])
@limiter.limit("10 per minute")
def admin_delete_loveseed():
    """
    删除相思豆码（管理员）
    """
    admin_token = request.headers.get("X-Admin-Token") or request.json.get("admin_token") if request.json else None
    
    if not LOCAL_TEST_MODE and admin_token != os.getenv("ADMIN_TOKEN", "admin123"):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    try:
        data = request.get_json()
        loveseed_code = data.get("loveseed_code", "").strip()
        
        if not loveseed_code:
            return jsonify({"status": "error", "message": "缺少相思豆码"}), 400
        
        result = delete_loveseed_code_admin(loveseed_code)
        
        if result:
            return jsonify({
                "status": "success",
                "message": "删除成功"
            })
        else:
            return jsonify({"status": "error", "message": "删除失败，相思豆码不存在"}), 400
    except Exception as e:
        logger.error(f"删除相思豆码失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/loveseed/update", methods=["POST"])
@limiter.limit("10 per minute")
def admin_update_loveseed():
    """
    更新相思豆码的剩余次数（管理员）
    """
    admin_token = request.headers.get("X-Admin-Token") or request.json.get("admin_token") if request.json else None
    
    if not LOCAL_TEST_MODE and admin_token != os.getenv("ADMIN_TOKEN", "admin123"):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    try:
        data = request.get_json()
        loveseed_code = data.get("loveseed_code", "").strip()
        new_downloads = data.get("new_downloads")
        
        if not loveseed_code or new_downloads is None:
            return jsonify({"status": "error", "message": "缺少必要参数"}), 400
        
        try:
            new_downloads = int(new_downloads)
            if new_downloads < 0:
                return jsonify({"status": "error", "message": "下载次数不能为负数"}), 400
        except ValueError:
            return jsonify({"status": "error", "message": "下载次数必须是数字"}), 400
        
        result = update_loveseed_downloads_admin(loveseed_code, new_downloads)
        
        if result:
            return jsonify({
                "status": "success",
                "message": "更新成功"
            })
        else:
            return jsonify({"status": "error", "message": "更新失败，相思豆码不存在"}), 400
    except Exception as e:
        logger.error(f"更新相思豆码失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ==================== 站点配置管理API ====================

@app.route("/api/site-config", methods=["GET"])
@limiter.limit("30 per minute")
def get_site_config():
    """
    获取站点配置（公开接口）
    """
    try:
        config_file = os.path.join(os.path.dirname(__file__), 'site_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                import json
                config = json.load(f)
        else:
            # 默认配置
            config = {
                "icp_beian": "",
                "copyright_text": "Copyright © 2025 一纸相思手写坊 All Rights Reserved.",
                "friend_links": []
            }
        
        return jsonify({
            "status": "success",
            "data": config
        })
    except Exception as e:
        logger.error(f"获取站点配置失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/site-config", methods=["POST"])
@limiter.limit("10 per minute")
def save_site_config():
    """
    保存站点配置（管理员）
    """
    admin_token = request.headers.get("X-Admin-Token") or request.json.get("admin_token") if request.json else None
    
    if not LOCAL_TEST_MODE and admin_token != os.getenv("ADMIN_TOKEN", "admin123"):
        return jsonify({"status": "error", "message": "权限不足"}), 403
    
    try:
        data = request.get_json()
        
        config = {
            "icp_beian": data.get("icp_beian", "").strip(),
            "copyright_text": data.get("copyright_text", "").strip(),
            "friend_links": data.get("friend_links", [])
        }
        
        # 验证友情链接格式
        for link in config["friend_links"]:
            if not isinstance(link, dict) or "name" not in link or "url" not in link:
                return jsonify({"status": "error", "message": "友情链接格式错误"}), 400
        
        # 保存配置到文件
        config_file = os.path.join(os.path.dirname(__file__), 'site_config.json')
        with open(config_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        return jsonify({
            "status": "success",
            "message": "配置保存成功"
        })
    except Exception as e:
        logger.error(f"保存站点配置失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/payment/<path:path>")
def send_payment(path):
    return send_from_directory('../web_frontend/payment', path)

if __name__ == "__main__":
    # 启动时清理之前标记的目录
    cleanup_marked_directories()
    app.run(debug=True, host="0.0.0.0", port=5000)


# poetry
def main():
    app.run(debug=True, host="0.0.0.0", port=5000)

    # good luck 6/16/2023
    # thank you 2/14/2025


"""    
数据库初始化操作

CREATE TABLE user_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE, 
    password VARCHAR(255), 
    image BLOB,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


数据库结构
mysql -u root -p进入数据库
USE your_database;数据库中的一个库
describe user_images;表：
"""
