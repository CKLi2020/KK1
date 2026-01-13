"""
用户认证和会员服务模块
"""
import os
import requests
import hashlib
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
import mysql.connector
import logging

logger = logging.getLogger(__name__)

# 微信小程序配置（需要在环境变量中设置）
WX_APPID = os.getenv("WX_APPID", "")
WX_SECRET = os.getenv("WX_SECRET", "")

# 微信支付配置
WX_MCH_ID = os.getenv("WX_MCH_ID", "")  # 商户号
WX_API_KEY = os.getenv("WX_API_KEY", "")  # API密钥

# 小程序名称（用于水印）
APP_NAME = os.getenv("APP_NAME", "手写生成器")

# 免费用户字数限制
# Effectively disable free character limit; keep a high ceiling to prevent accidental extremes
FREE_CHAR_LIMIT = 10_000_000

# 本地测试模式（没有数据库时使用）
LOCAL_TEST_MODE = os.getenv("LOCAL_TEST_MODE", "true").lower() == "true"

# 测试管理员openid列表（本地测试用）
TEST_ADMIN_OPENID = "test_admin_openid_12345"

# 模拟用户数据（本地测试用）
MOCK_USERS = {
    TEST_ADMIN_OPENID: {
        'id': 1,
        'openid': TEST_ADMIN_OPENID,
        'nickname': '测试管理员',
        'avatar_url': '',
        'is_admin': 1,
        'member_type': 'admin',
        'member_expire_time': datetime.now() + timedelta(days=99999),
        'total_chars_generated': 0,
        'created_at': datetime.now()
    }
}


def get_db_connection():
    """获取数据库连接"""
    if LOCAL_TEST_MODE:
        return None  # 本地测试模式不需要数据库
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "mydatabase"),
        charset='utf8mb4'
    )


def wx_code_to_openid(code):
    """
    通过微信 code 换取 openid
    """
    if not WX_APPID or not WX_SECRET:
        logger.warning("微信小程序配置缺失，使用模拟 openid")
        # 开发模式：生成模拟 openid
        return f"dev_openid_{hashlib.md5(code.encode()).hexdigest()[:16]}"
    
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": WX_APPID,
        "secret": WX_SECRET,
        "js_code": code,
        "grant_type": "authorization_code"
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if "openid" in data:
            return data["openid"]
        else:
            logger.error(f"微信登录失败: {data}")
            return None
    except Exception as e:
        logger.error(f"微信登录请求失败: {e}")
        return None


def get_or_create_user(openid, nickname="", avatar_url=""):
    """
    根据 openid 获取或创建用户
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        if openid in MOCK_USERS:
            return MOCK_USERS[openid]
        # 创建模拟用户
        mock_user = {
            'id': len(MOCK_USERS) + 1,
            'openid': openid,
            'nickname': nickname or f'用户{len(MOCK_USERS) + 1}',
            'avatar_url': avatar_url,
            'is_admin': 0,
            'member_type': 'free',
            'member_expire_time': None,
            'total_chars_generated': 0,
            'created_at': datetime.now()
        }
        MOCK_USERS[openid] = mock_user
        return mock_user
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 查找用户
        cursor.execute("SELECT * FROM users WHERE openid = %s", (openid,))
        user = cursor.fetchone()
        
        if user:
            # 更新用户信息（如果有新的昵称或头像）
            if nickname or avatar_url:
                update_fields = []
                update_values = []
                if nickname:
                    update_fields.append("nickname = %s")
                    update_values.append(nickname)
                if avatar_url:
                    update_fields.append("avatar_url = %s")
                    update_values.append(avatar_url)
                update_values.append(openid)
                
                cursor.execute(
                    f"UPDATE users SET {', '.join(update_fields)} WHERE openid = %s",
                    tuple(update_values)
                )
                conn.commit()
            
            return user
        else:
            # 创建新用户
            cursor.execute(
                """INSERT INTO users (openid, nickname, avatar_url, member_type) 
                   VALUES (%s, %s, %s, 'free')""",
                (openid, nickname, avatar_url)
            )
            conn.commit()
            
            # 获取新创建的用户
            cursor.execute("SELECT * FROM users WHERE openid = %s", (openid,))
            return cursor.fetchone()
            
    except Exception as e:
        logger.error(f"获取/创建用户失败: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def check_user_membership(user):
    """
    检查用户会员状态
    返回: (is_vip, member_type, days_remaining)
    """
    if not user:
        return False, 'guest', 0
    
    member_type = user.get('member_type', 'free')
    expire_time = user.get('member_expire_time')
    
    # 管理员始终是VIP
    if user.get('is_admin'):
        return True, 'admin', 99999
    
    if member_type == 'free' or not expire_time:
        return False, 'free', 0
    
    now = datetime.now()
    if expire_time > now:
        days_remaining = (expire_time - now).days
        return True, member_type, days_remaining
    else:
        # 会员已过期，更新为免费用户
        # 本地测试模式
        if LOCAL_TEST_MODE:
            if user.get('openid') in MOCK_USERS:
                MOCK_USERS[user['openid']]['member_type'] = 'free'
            return False, 'free', 0
        
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET member_type = 'free' WHERE id = %s",
                    (user['id'],)
                )
                conn.commit()
                cursor.close()
                conn.close()
        except Exception as e:
            logger.error(f"更新过期会员状态失败: {e}")
        
        return False, 'free', 0


def get_packages():
    """
    获取所有启用的套餐
    """
    # 默认套餐（用于数据库不可用时）
    default_packages = [
        {'id': 1, 'name': '月卡', 'type': 'monthly', 'price': 9.90, 'duration_days': 30, 'description': '30天会员'},
        {'id': 2, 'name': '季卡', 'type': 'quarterly', 'price': 19.90, 'duration_days': 90, 'description': '90天会员'},
        {'id': 3, 'name': '年卡', 'type': 'yearly', 'price': 49.90, 'duration_days': 365, 'description': '365天会员'}
    ]
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT id, name, type, price, duration_days, description FROM packages WHERE is_active = 1"
        )
        packages = cursor.fetchall()
        
        # 将 Decimal 转换为 float
        for pkg in packages:
            pkg['price'] = float(pkg['price'])
        
        return packages if packages else default_packages
        
    except Exception as e:
        logger.error(f"获取套餐列表失败: {e}")
        return default_packages
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_order(user_id, package_id):
    """
    创建订单
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 获取套餐信息
        cursor.execute("SELECT * FROM packages WHERE id = %s AND is_active = 1", (package_id,))
        package = cursor.fetchone()
        
        if not package:
            return None, "套餐不存在"
        
        # 生成订单号
        order_no = f"HW{int(time.time() * 1000)}{uuid.uuid4().hex[:8].upper()}"
        
        # 创建订单
        cursor.execute(
            """INSERT INTO orders (order_no, user_id, package_id, amount, status) 
               VALUES (%s, %s, %s, %s, 'pending')""",
            (order_no, user_id, package_id, package['price'])
        )
        conn.commit()
        
        return {
            "order_no": order_no,
            "amount": float(package['price']),
            "package_name": package['name'],
            "duration_days": package['duration_days']
        }, None
        
    except Exception as e:
        logger.error(f"创建订单失败: {e}")
        return None, str(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def complete_order(order_no, wx_transaction_id=None):
    """
    完成订单并更新用户会员状态
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 获取订单信息
        cursor.execute(
            """SELECT o.*, p.type, p.duration_days 
               FROM orders o 
               JOIN packages p ON o.package_id = p.id 
               WHERE o.order_no = %s AND o.status = 'pending'""",
            (order_no,)
        )
        order = cursor.fetchone()
        
        if not order:
            return False, "订单不存在或已处理"
        
        # 更新订单状态
        cursor.execute(
            """UPDATE orders SET status = 'paid', wx_transaction_id = %s, paid_at = NOW() 
               WHERE order_no = %s""",
            (wx_transaction_id, order_no)
        )
        
        # 计算会员到期时间
        cursor.execute("SELECT member_expire_time FROM users WHERE id = %s", (order['user_id'],))
        user = cursor.fetchone()
        
        current_expire = user.get('member_expire_time')
        now = datetime.now()
        
        if current_expire and current_expire > now:
            # 续费：在当前到期时间基础上延长
            new_expire = current_expire + timedelta(days=order['duration_days'])
        else:
            # 新开通：从现在开始计算
            new_expire = now + timedelta(days=order['duration_days'])
        
        # 更新用户会员状态
        cursor.execute(
            """UPDATE users SET member_type = %s, member_expire_time = %s 
               WHERE id = %s""",
            (order['type'], new_expire, order['user_id'])
        )
        
        conn.commit()
        return True, "订单完成"
        
    except Exception as e:
        logger.error(f"完成订单失败: {e}")
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def log_usage(user_id, openid, action_type, char_count, has_watermark):
    """
    记录使用日志
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO usage_logs (user_id, openid, action_type, char_count, has_watermark) 
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, openid, action_type, char_count, has_watermark)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"记录使用日志失败: {e}")


def add_watermark_to_image(image, watermark_text=None):
    """
    给图片添加斜向重复水印
    水印会在整个图片上斜着重复出现
    """
    from PIL import Image, ImageDraw, ImageFont
    import math
    
    if watermark_text is None:
        watermark_text = APP_NAME

    # 转换为RGBA以便处理透明度
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # 创建一个透明的水印层
    txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    
    # 设置字体大小为图片宽度的1/15
    font_size = int(image.width / 15)
    if font_size < 20: font_size = 20
    
    font = None
    try:
        # 尝试查找字体文件
        font_path = None
        # 优先寻找支持中文的字体
        font_dirs = ["./font_assets", "../font_assets", "."]
        
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        font_dirs.append(os.path.join(current_dir, "font_assets"))
        
        for d in font_dirs:
            if os.path.exists(d):
                # 优先查找常见的中文字体文件名
                for f in os.listdir(d):
                    if f.lower().endswith(('.ttf', '.otf')):
                        font_path = os.path.join(d, f)
                        # 找到一个就停止
                        break
            if font_path: break
            
        if font_path:
            logger.info(f"Using watermark font: {font_path}")
            font = ImageFont.truetype(font_path, font_size)
        else:
            logger.warning("No font file found for watermark, using default.")
            font = ImageFont.load_default()
    except Exception as e:
        logger.error(f"Failed to load font for watermark: {e}")
        font = ImageFont.load_default()

    # 如果使用的是默认字体（通常不支持中文），将水印文本改为英文，确保能显示
    # ImageFont.load_default() 返回的对象通常没有 path 属性，或者名字是 "ImageFont"
    is_default_font = False
    try:
        if not hasattr(font, 'path') and not hasattr(font, 'font'):
             is_default_font = True
    except:
        is_default_font = True
        
    # 简单判断：如果加载失败或者是默认字体，且文本包含中文，则追加英文或替换
    if is_default_font:
        # 默认字体不支持中文，强制使用英文
        watermark_text = "Preview Mode"

    # 计算水印文本大小
    try:
        left, top, right, bottom = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = right - left
        text_height = bottom - top
    except AttributeError:
        # 旧版Pillow兼容
        text_width, text_height = draw.textsize(watermark_text, font=font)
    
    # 水印颜色 (灰色，半透明)
    fill_color = (180, 180, 180, 80)
    
    # 旋转角度
    angle = 30
    
    # 创建单个水印图片并旋转
    # 留出足够空间防止旋转裁剪
    mark_width = int(text_width * 1.5)
    mark_height = int(text_height * 1.5)
    mark_img = Image.new('RGBA', (mark_width, mark_height), (0, 0, 0, 0))
    mark_draw = ImageDraw.Draw(mark_img)
    # 居中绘制
    mark_draw.text(((mark_width - text_width)/2, (mark_height - text_height)/2), 
                   watermark_text, font=font, fill=fill_color)
    
    rotated_mark = mark_img.rotate(angle, expand=1)
    rm_w, rm_h = rotated_mark.size
    
    # 铺满整个图片
    # 间距
    gap_x = int(rm_w * 1.5)
    gap_y = int(rm_h * 1.5)
    
    for y in range(-gap_y, image.height + gap_y, gap_y):
        for x in range(-gap_x, image.width + gap_x, gap_x):
            # 错位排列
            offset_x = (y // gap_y) * (gap_x // 2)
            pos_x = x + offset_x
            
            txt_layer.paste(rotated_mark, (pos_x, y), rotated_mark)
            
    # 合并图片
    watermarked = Image.alpha_composite(image, txt_layer)
    return watermarked.convert('RGB')


def add_watermark_to_images(images, watermark_text=None):
    """
    给多张图片添加水印
    """
    return [add_watermark_to_image(img, watermark_text) for img in images]


# ==================== 管理员功能 ====================

# 管理员openid列表（可以通过环境变量配置）
ADMIN_OPENIDS = os.getenv("ADMIN_OPENIDS", "").split(",")


def is_admin(openid):
    """
    检查用户是否是管理员
    """
    if openid in ADMIN_OPENIDS and openid:
        return True
    
    # 本地测试模式：检查模拟用户
    if LOCAL_TEST_MODE:
        if openid == TEST_ADMIN_OPENID:
            return True
        user = MOCK_USERS.get(openid)
        if user and user.get('is_admin'):
            return True
        return False
    
    # 也可以从数据库检查
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT is_admin FROM users WHERE openid = %s", (openid,))
        user = cursor.fetchone()
        if user and user.get('is_admin'):
            return True
    except Exception as e:
        logger.error(f"检查管理员权限失败: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return False


def set_user_admin(openid, is_admin_flag):
    """
    设置用户为管理员
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        if openid in MOCK_USERS:
            MOCK_USERS[openid]['is_admin'] = 1 if is_admin_flag else 0
            return True
        return False
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_admin = %s WHERE openid = %s",
            (1 if is_admin_flag else 0, openid)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"设置管理员失败: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def admin_grant_membership(target_openid, member_type, days):
    """
    管理员给用户开通会员（绕过付费）
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        if target_openid not in MOCK_USERS:
            return False, "用户不存在"
        
        user = MOCK_USERS[target_openid]
        now = datetime.now()
        current_expire = user.get('member_expire_time')
        
        if current_expire and current_expire > now:
            new_expire = current_expire + timedelta(days=days)
        else:
            new_expire = now + timedelta(days=days)
        
        MOCK_USERS[target_openid]['member_type'] = member_type
        MOCK_USERS[target_openid]['member_expire_time'] = new_expire
        
        return True, f"成功为用户开通{days}天{member_type}会员，到期时间：{new_expire.strftime('%Y-%m-%d %H:%M')}"
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return False, "数据库连接失败"
        cursor = conn.cursor(dictionary=True)
        
        # 查找目标用户
        cursor.execute("SELECT * FROM users WHERE openid = %s", (target_openid,))
        user = cursor.fetchone()
        
        if not user:
            return False, "用户不存在"
        
        # 计算会员到期时间
        now = datetime.now()
        current_expire = user.get('member_expire_time')
        
        if current_expire and current_expire > now:
            # 如果还有会员时间，则在现有基础上延长
            new_expire = current_expire + timedelta(days=days)
        else:
            # 否则从现在开始计算
            new_expire = now + timedelta(days=days)
        
        # 更新用户会员信息
        cursor.execute(
            """UPDATE users 
               SET member_type = %s, member_expire_time = %s 
               WHERE openid = %s""",
            (member_type, new_expire, target_openid)
        )
        conn.commit()
        
        return True, f"成功为用户开通{days}天{member_type}会员，到期时间：{new_expire.strftime('%Y-%m-%d %H:%M')}"
        
    except Exception as e:
        logger.error(f"管理员开通会员失败: {e}")
        return False, str(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_membership_statistics():
    """
    获取会员统计数据
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        member_counts = {}
        active_member_counts = {}
        for user in MOCK_USERS.values():
            mt = user.get('member_type', 'free')
            member_counts[mt] = member_counts.get(mt, 0) + 1
            if user.get('member_expire_time') and user['member_expire_time'] > datetime.now():
                if mt != 'free':
                    active_member_counts[mt] = active_member_counts.get(mt, 0) + 1
        
        return {
            'member_counts': member_counts,
            'active_member_counts': active_member_counts,
            'total_orders': 5,  # 模拟数据
            'total_revenue': 99.50,  # 模拟数据
            'recent_orders': [
                {'order_no': 'TEST001', 'amount': 9.90, 'status': 'paid', 'package_name': '月度会员', 'nickname': '测试用户1'},
                {'order_no': 'TEST002', 'amount': 19.90, 'status': 'paid', 'package_name': '季度会员', 'nickname': '测试用户2'},
            ],
            'total_users': len(MOCK_USERS)
        }
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return {
                'member_counts': {},
                'active_member_counts': {},
                'total_orders': 0,
                'total_revenue': 0,
                'recent_orders': [],
                'total_users': 0,
                'error': '数据库未连接'
            }
        cursor = conn.cursor(dictionary=True)
        
        # 获取各类会员数量
        cursor.execute("""
            SELECT 
                member_type,
                COUNT(*) as count
            FROM users 
            GROUP BY member_type
        """)
        member_counts = cursor.fetchall()
        
        # 获取有效会员数量（未过期）
        cursor.execute("""
            SELECT 
                member_type,
                COUNT(*) as count
            FROM users 
            WHERE member_expire_time > NOW() AND member_type != 'free'
            GROUP BY member_type
        """)
        active_member_counts = cursor.fetchall()
        
        # 获取总订单数和总收入
        cursor.execute("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(amount) as total_revenue
            FROM orders 
            WHERE status = 'paid'
        """)
        order_stats = cursor.fetchone()
        
        # 获取最近的订单
        cursor.execute("""
            SELECT 
                o.order_no,
                o.amount,
                o.status,
                o.created_at,
                o.paid_at,
                p.name as package_name,
                u.nickname,
                u.openid
            FROM orders o
            LEFT JOIN packages p ON o.package_id = p.id
            LEFT JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 50
        """)
        recent_orders = cursor.fetchall()
        
        # 获取用户总数
        cursor.execute("SELECT COUNT(*) as total FROM users")
        user_count = cursor.fetchone()
        
        return {
            'member_counts': {item['member_type']: item['count'] for item in member_counts},
            'active_member_counts': {item['member_type']: item['count'] for item in active_member_counts},
            'total_orders': order_stats['total_orders'] if order_stats else 0,
            'total_revenue': float(order_stats['total_revenue']) if order_stats and order_stats['total_revenue'] else 0,
            'recent_orders': recent_orders,
            'total_users': user_count['total'] if user_count else 0
        }
        
    except Exception as e:
        logger.error(f"获取会员统计失败: {e}")
        return {
            'member_counts': {},
            'active_member_counts': {},
            'total_orders': 0,
            'total_revenue': 0,
            'recent_orders': [],
            'total_users': 0,
            'error': str(e)
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def search_users(keyword, limit=20):
    """
    搜索用户
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        results = []
        for user in MOCK_USERS.values():
            if keyword.lower() in user.get('openid', '').lower() or keyword.lower() in user.get('nickname', '').lower():
                results.append(user)
                if len(results) >= limit:
                    break
        return results
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                id, openid, nickname, avatar_url, is_admin,
                member_type, member_expire_time, created_at
            FROM users 
            WHERE openid LIKE %s OR nickname LIKE %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (f"%{keyword}%", f"%{keyword}%", limit))
        
        users = cursor.fetchall()
        return users
        
    except Exception as e:
        logger.error(f"搜索用户失败: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_all_users(page=1, page_size=20):
    """
    获取所有用户列表
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        users = list(MOCK_USERS.values())
        total = len(users)
        start = (page - 1) * page_size
        end = start + page_size
        return {
            'users': users[start:end],
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return {'users': [], 'total': 0, 'page': 1, 'page_size': page_size, 'total_pages': 0}
        cursor = conn.cursor(dictionary=True)
        
        offset = (page - 1) * page_size
        
        cursor.execute("""
            SELECT 
                id, openid, nickname, avatar_url, is_admin,
                member_type, member_expire_time, total_chars_generated, created_at
            FROM users 
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (page_size, offset))
        
        users = cursor.fetchall()
        
        # 获取总数
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total = cursor.fetchone()['total']
        
        return {
            'users': users,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return {'users': [], 'total': 0, 'page': 1, 'page_size': page_size, 'total_pages': 0}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
