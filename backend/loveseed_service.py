"""
相思豆服务模块
处理订单、相思豆的生成和验证
"""
import os
import random
import string
import mysql.connector
import logging
from datetime import datetime, timedelta
from payment_service import (
    create_payment_charge, 
    retrieve_charge, 
    format_amount_to_cents,
    generate_order_no as generate_payment_order_no
)

logger = logging.getLogger(__name__)

# 本地测试模式
LOCAL_TEST_MODE = os.getenv("LOCAL_TEST_MODE", "true").lower() == "true"

# 模拟数据（本地测试用）
MOCK_LOVESEED_CODES = {
    # 测试用相思豆
    '123456': {
        'loveseed_code': '123456',
        'order_id': 0,
        'package_id': 3,
        'total_downloads': 20,
        'remaining_downloads': 20,
        'status': 'active',
        'created_at': datetime.now()
    }
}
MOCK_ORDERS = {}


def get_db_connection():
    """获取数据库连接"""
    if LOCAL_TEST_MODE:
        return None
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "mydatabase"),
        charset='utf8mb4'
    )


def generate_order_number():
    """生成唯一的订单号"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(random.choices(string.digits, k=6))
    return f"ORD{timestamp}{random_suffix}"


def create_loveseed_order(package_id, amount):
    """
    创建订单并生成相思豆（支持混合模式：按次数和按时间）
    
    Args:
        package_id: 套餐ID
        amount: 支付金额
    
    Returns:
        dict: 包含订单信息和相思豆的字典
    """
    order_no = generate_order_number()
    loveseed_code = order_no[-6:]  # 订单号后6位作为相思豆
    
    # 本地测试模式
    if LOCAL_TEST_MODE:
        # 模拟套餐信息（混合模式）
        package_info = {
            # 按次数套餐
            1: {'billing_type': 'count', 'download_count': 2, 'duration_days': 0, 'name': '体验套餐'},
            2: {'billing_type': 'count', 'download_count': 8, 'duration_days': 0, 'name': '基础套餐'},
            3: {'billing_type': 'count', 'download_count': 20, 'duration_days': 0, 'name': '热门套餐'},
            4: {'billing_type': 'count', 'download_count': 35, 'duration_days': 0, 'name': '超值套餐'},
            5: {'billing_type': 'count', 'download_count': 70, 'duration_days': 0, 'name': '尊享套餐'},
            # 按时间套餐（有效期内无限次）
            6: {'billing_type': 'duration', 'download_count': 999999, 'duration_days': 30, 'name': '包月套餐'},
            7: {'billing_type': 'duration', 'download_count': 999999, 'duration_days': 90, 'name': '季度套餐'},
            8: {'billing_type': 'duration', 'download_count': 999999, 'duration_days': 365, 'name': '包年套餐'},
        }
        
        pkg = package_info.get(package_id, {'billing_type': 'count', 'download_count': 20, 'duration_days': 0, 'name': '热门套餐'})
        
        # 创建模拟订单
        order = {
            'id': len(MOCK_ORDERS) + 1,
            'order_no': order_no,
            'package_id': package_id,
            'amount': amount,
            'status': 'paid',
            'paid_at': datetime.now()
        }
        MOCK_ORDERS[order_no] = order
        
        # 计算到期时间（按时间套餐）
        expire_time = None
        if pkg['billing_type'] == 'duration':
            expire_time = datetime.now() + timedelta(days=pkg['duration_days'])
        
        # 创建模拟相思豆
        loveseed = {
            'loveseed_code': loveseed_code,
            'order_id': order['id'],
            'package_id': package_id,
            'billing_type': pkg['billing_type'],
            'total_downloads': pkg['download_count'],
            'remaining_downloads': pkg['download_count'],
            'duration_days': pkg.get('duration_days', 0),
            'expire_time': expire_time,
            'status': 'active',
            'created_at': datetime.now()
        }
        MOCK_LOVESEED_CODES[loveseed_code] = loveseed
        
        logger.info(f"本地测试: 创建订单 {order_no}, 相思豆 {loveseed_code}, 类型 {pkg['billing_type']}, 次数 {pkg['download_count']}, 天数 {pkg['duration_days']}")
        
        return {
            'order_no': order_no,
            'loveseed_code': loveseed_code,
            'package_name': pkg['name'],
            'billing_type': pkg['billing_type'],
            'download_count': pkg['download_count'],
            'duration_days': pkg.get('duration_days', 0),
            'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S') if expire_time else None,
            'amount': amount
        }
    
    # 数据库模式
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 获取套餐信息
        cursor.execute("SELECT * FROM packages WHERE id = %s", (package_id,))
        package = cursor.fetchone()
        
        if not package:
            raise ValueError(f"套餐不存在: {package_id}")
        
        # 创建订单
        cursor.execute(
            """INSERT INTO orders (order_no, package_id, amount, status, paid_at) 
               VALUES (%s, %s, %s, 'paid', NOW())""",
            (order_no, package_id, amount)
        )
        order_id = cursor.lastrowid
        
        # 计算到期时间（按时间套餐）
        expire_time = None
        if package['billing_type'] == 'duration':
            expire_time = datetime.now() + timedelta(days=package['duration_days'])
        
        # 创建相思豆
        cursor.execute(
            """INSERT INTO loveseed_codes 
               (loveseed_code, order_id, package_id, billing_type, total_downloads, remaining_downloads, expire_time, status) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')""",
            (loveseed_code, order_id, package_id, package['billing_type'], 
             package['download_count'], package['download_count'], expire_time)
        )
        
        conn.commit()
        
        logger.info(f"创建订单 {order_no}, 相思豆 {loveseed_code}, 类型 {package['billing_type']}, 次数 {package['download_count']}, 天数 {package.get('duration_days', 0)}")
        
        return {
            'order_no': order_no,
            'loveseed_code': loveseed_code,
            'package_name': package['name'],
            'billing_type': package['billing_type'],
            'download_count': package['download_count'],
            'duration_days': package.get('duration_days', 0),
            'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S') if expire_time else None,
            'amount': amount
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"创建订单失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def verify_loveseed_code(loveseed_code):
    """
    验证相思豆是否有效（混合模式：按次数和按时间）
    
    Args:
        loveseed_code: 相思豆（6位数字）
    
    Returns:
        dict: 相思豆信息，如果无效则返回 None
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        loveseed = MOCK_LOVESEED_CODES.get(loveseed_code)
        if not loveseed or loveseed['status'] != 'active':
            return None
        
        # 检查计费类型
        billing_type = loveseed.get('billing_type', 'count')
        
        if billing_type == 'duration':
            # 按时间：检查是否过期
            expire_time = loveseed.get('expire_time')
            if expire_time and datetime.now() > expire_time:
                loveseed['status'] = 'expired'
                logger.info(f"本地测试: 相思豆 {loveseed_code} 已过期")
                return None
            return {
                'loveseed_code': loveseed_code,
                'billing_type': 'duration',
                'remaining_downloads': 999999,  # 时间套餐无限次
                'total_downloads': 999999,
                'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S') if expire_time else None,
                'status': loveseed['status']
            }
        else:
            # 按次数：检查剩余次数
            if loveseed['remaining_downloads'] <= 0:
                return None
            return {
                'loveseed_code': loveseed_code,
                'billing_type': 'count',
                'remaining_downloads': loveseed['remaining_downloads'],
                'total_downloads': loveseed['total_downloads'],
                'expire_time': None,
                'status': loveseed['status']
            }
    
    # 数据库模式
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            """SELECT * FROM loveseed_codes 
               WHERE loveseed_code = %s AND status = 'active'""",
            (loveseed_code,)
        )
        loveseed = cursor.fetchone()
        
        if not loveseed:
            return None
        
        billing_type = loveseed.get('billing_type', 'count')
        
        if billing_type == 'duration':
            # 按时间：检查是否过期
            expire_time = loveseed.get('expire_time')
            if expire_time and datetime.now() > expire_time:
                # 更新为过期状态
                cursor.execute(
                    "UPDATE loveseed_codes SET status = 'expired' WHERE loveseed_code = %s",
                    (loveseed_code,)
                )
                conn.commit()
                logger.info(f"相思豆 {loveseed_code} 已过期")
                return None
            
            loveseed['expire_time'] = expire_time.strftime('%Y-%m-%d %H:%M:%S') if expire_time else None
            return loveseed
        else:
            # 按次数：检查剩余次数
            if loveseed['remaining_downloads'] <= 0:
                return None
            return loveseed
        
    except Exception as e:
        logger.error(f"验证相思豆失败: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def consume_loveseed_download(loveseed_code, openid=None, action_type='generate_image', char_count=0):
    """
    消费一次下载次数（混合模式：按次数和按时间）
    按时间套餐：只检查过期，不减少次数
    按次数套餐：减少一次次数
    
    Args:
        loveseed_code: 相思豆
        openid: 用户openid（可选）
        action_type: 操作类型 ('generate_image' 或 'generate_pdf')
        char_count: 字数
    
    Returns:
        dict: 更新后的相思豆信息，失败返回 None
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        loveseed = MOCK_LOVESEED_CODES.get(loveseed_code)
        if not loveseed or loveseed['status'] != 'active':
            return None
        
        billing_type = loveseed.get('billing_type', 'count')
        
        if billing_type == 'duration':
            # 按时间：检查过期，不减少次数
            expire_time = loveseed.get('expire_time')
            if expire_time and datetime.now() > expire_time:
                loveseed['status'] = 'expired'
                logger.info(f"本地测试: 相思豆 {loveseed_code} 已过期")
                return None
            
            logger.info(f"本地测试: 消费相思豆 {loveseed_code} (按时间), 不减少次数")
            
            return {
                'loveseed_code': loveseed_code,
                'billing_type': 'duration',
                'remaining_downloads': 999999,
                'total_downloads': 999999,
                'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S') if expire_time else None,
                'status': loveseed['status']
            }
        else:
            # 按次数：减少次数
            if loveseed['remaining_downloads'] <= 0:
                return None
            
            # 减少下载次数
            loveseed['remaining_downloads'] -= 1
            
            # 如果用尽，更新状态
            if loveseed['remaining_downloads'] == 0:
                loveseed['status'] = 'exhausted'
            
            logger.info(f"本地测试: 消费相思豆 {loveseed_code} (按次数), 剩余 {loveseed['remaining_downloads']} 次")
            
            return {
                'loveseed_code': loveseed_code,
                'billing_type': 'count',
                'remaining_downloads': loveseed['remaining_downloads'],
                'total_downloads': loveseed['total_downloads'],
                'expire_time': None,
                'status': loveseed['status']
            }
    
    # 数据库模式
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 验证相思豆
        cursor.execute(
            """SELECT * FROM loveseed_codes 
               WHERE loveseed_code = %s AND status = 'active'""",
            (loveseed_code,)
        )
        loveseed = cursor.fetchone()
        
        if not loveseed:
            return None
            
        billing_type = loveseed.get('billing_type', 'count')
        
        if billing_type == 'duration':
            # 按时间：检查是否过期
            expire_time = loveseed.get('expire_time')
            if expire_time and datetime.now() > expire_time:
                # 更新为过期状态
                cursor.execute(
                    "UPDATE loveseed_codes SET status = 'expired' WHERE loveseed_code = %s",
                    (loveseed_code,)
                )
                conn.commit()
                logger.info(f"相思豆 {loveseed_code} 已过期")
                return None
                
            # 记录下载日志
            cursor.execute(
                """INSERT INTO download_logs 
                   (loveseed_code, openid, action_type, char_count) 
                   VALUES (%s, %s, %s, %s)""",
                (loveseed_code, openid, action_type, char_count)
            )
            conn.commit()
            
            logger.info(f"消费相思豆 {loveseed_code} (按时间), 不减少次数")
            
            return {
                'loveseed_code': loveseed_code,
                'billing_type': 'duration',
                'remaining_downloads': loveseed['remaining_downloads'],
                'total_downloads': loveseed['total_downloads'],
                'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S') if expire_time else None,
                'status': loveseed['status']
            }
        else:
            # 按次数：检查剩余次数
            if loveseed['remaining_downloads'] <= 0:
                return None
        
            # 减少下载次数
            new_remaining = loveseed['remaining_downloads'] - 1
            new_status = 'exhausted' if new_remaining == 0 else 'active'
            
            cursor.execute(
                """UPDATE loveseed_codes 
                   SET remaining_downloads = %s, status = %s 
                   WHERE loveseed_code = %s""",
                (new_remaining, new_status, loveseed_code)
            )
            
            # 记录下载日志
            cursor.execute(
                """INSERT INTO download_logs 
                   (loveseed_code, openid, action_type, char_count) 
                   VALUES (%s, %s, %s, %s)""",
                (loveseed_code, openid, action_type, char_count)
            )
            
            conn.commit()
            
            logger.info(f"消费相思豆 {loveseed_code}, 剩余 {new_remaining} 次")
            
            return {
                'loveseed_code': loveseed_code,
                'billing_type': 'count',
                'remaining_downloads': new_remaining,
                'total_downloads': loveseed['total_downloads'],
                'status': new_status
            }
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"消费下载次数失败: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_all_packages():
    """
    获取所有可用套餐
    
    Returns:
        list: 套餐列表
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        return [
            {'id': 1, 'name': '体验套餐', 'type': 'trial', 'price': 2.99, 'download_count': 2, 'unit_price': 1.50, 'description': '包含2次使用次数（单价¥1.50）', 'badge_text': '', 'badge_color': ''},
            {'id': 2, 'name': '基础套餐', 'type': 'basic', 'price': 4.99, 'download_count': 8, 'unit_price': 0.62, 'description': '包含8次使用次数（单价¥0.62）', 'badge_text': '', 'badge_color': ''},
            {'id': 3, 'name': '热门套餐', 'type': 'hot', 'price': 8.99, 'download_count': 20, 'unit_price': 0.45, 'description': '包含20次使用次数（单价¥0.45）', 'badge_text': '', 'badge_color': ''},
            {'id': 4, 'name': '超值套餐', 'type': 'value', 'price': 11.90, 'download_count': 35, 'unit_price': 0.34, 'description': '包含35次使用次数（单价¥0.34）', 'badge_text': '', 'badge_color': ''},
            {'id': 5, 'name': '尊享套餐', 'type': 'premium', 'price': 17.00, 'download_count': 70, 'unit_price': 0.24, 'description': '包含70次使用次数（单价¥0.24）', 'badge_text': '', 'badge_color': ''},
            {'id': 6, 'name': '包月套餐', 'type': 'monthly', 'price': 29.90, 'download_count': 999, 'unit_price': 0.03, 'description': '月内畅享使用（每日低至¥1.00）', 'badge_text': '最热', 'badge_color': 'blue'},
            {'id': 7, 'name': '季度套餐', 'type': 'quarterly', 'price': 69.90, 'download_count': 2997, 'unit_price': 0.02, 'description': '三个月内畅享使用（每日低至¥0.78）', 'badge_text': '限量', 'badge_color': 'pink'},
            {'id': 8, 'name': '包年套餐', 'type': 'yearly', 'price': 199.90, 'download_count': 9999, 'unit_price': 0.02, 'description': '一年内畅享使用（每日低至¥0.55）', 'badge_text': '最值', 'badge_color': 'yellow'},
        ]
    
    # 数据库模式
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM packages WHERE is_active = 1 ORDER BY id")
        packages = cursor.fetchall()
        
        return packages
        
    except Exception as e:
        logger.error(f"获取套餐列表失败: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_payment_order(package_id, channel, client_ip):
    """
    创建支付订单（使用 Ping++ 支付）
    
    Args:
        package_id: 套餐ID
        channel: 支付渠道 ('wx_pub_qr', 'alipay_qr', 'wx_wap', 'alipay_wap')
        client_ip: 客户端IP
    
    Returns:
        dict: 支付凭据信息
    """
    # 获取套餐信息
    packages = get_all_packages()
    package = next((p for p in packages if p['id'] == package_id), None)
    
    if not package:
        raise ValueError(f"套餐不存在: {package_id}")
    
    # 生成订单号
    order_no = generate_payment_order_no()
    
    # 转换金额为分
    amount_cents = format_amount_to_cents(package['price'])
    
    # 创建支付凭据
    subject = f"一纸相思手写坊 - {package['name']}"
    body = f"{package['description']}"
    
    charge = create_payment_charge(
        order_no=order_no,
        amount=amount_cents,
        channel=channel,
        subject=subject,
        body=body,
        client_ip=client_ip,
        extra={
            'package_id': package_id,
            'package_name': package['name'],
            'download_count': package['download_count']
        }
    )
    
    # 保存订单信息（待支付状态）
    if LOCAL_TEST_MODE:
        MOCK_ORDERS[order_no] = {
            'id': len(MOCK_ORDERS) + 1,
            'order_no': order_no,
            'package_id': package_id,
            'amount': package['price'],
            'status': 'pending',
            'charge_id': charge['id'],
            'created_at': datetime.now()
        }
    
    return {
        'charge': charge,
        'order_no': order_no,
        'package': package
    }


def handle_payment_success(order_no):
    """
    处理支付成功回调
    
    Args:
        order_no: 订单号
    
    Returns:
        dict: 相思豆信息
    """
    if LOCAL_TEST_MODE:
        # 本地测试模式
        order = MOCK_ORDERS.get(order_no)
        if not order:
            raise ValueError(f"订单不存在: {order_no}")
        
        if order['status'] == 'paid':
            # 已经支付，返回现有相思豆
            loveseed_code = order_no[-6:]
            loveseed = MOCK_LOVESEED_CODES.get(loveseed_code)
            if loveseed:
                return {
                    'order_no': order_no,
                    'loveseed_code': loveseed_code,
                    'billing_type': loveseed.get('billing_type', 'count'),
                    'download_count': loveseed['total_downloads'],
                    'duration_days': loveseed.get('duration_days', 0),
                    'expire_time': loveseed['expire_time'].strftime('%Y-%m-%d %H:%M:%S') if loveseed.get('expire_time') else None,
                    'status': 'success'
                }
        
        # 生成相思豆
        result = create_loveseed_order(order['package_id'], order['amount'])
        
        # 更新订单状态
        order['status'] = 'paid'
        order['paid_at'] = datetime.now()
        
        return {
            'order_no': order_no,
            'loveseed_code': result['loveseed_code'],
            'billing_type': result['billing_type'],
            'download_count': result['download_count'],
            'duration_days': result.get('duration_days', 0),
            'expire_time': result.get('expire_time'),
            'package_name': result['package_name'],
            'status': 'success'
        }
    
    # 数据库模式
    # TODO: 实现数据库逻辑
    pass


def get_all_orders_admin():
    """
    获取所有订单列表（管理员功能）
    
    Returns:
        list: 订单列表，包含相思豆码信息
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        result = []
        for order_no, order in MOCK_ORDERS.items():
            loveseed_code = order_no[-6:]
            loveseed = MOCK_LOVESEED_CODES.get(loveseed_code, {})
            result.append({
                'order_no': order_no,
                'package_id': order.get('package_id'),
                'amount': order.get('amount'),
                'status': order.get('status'),
                'paid_at': order.get('paid_at').strftime('%Y-%m-%d %H:%M:%S') if order.get('paid_at') else None,
                'created_at': order.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if order.get('created_at') else None,
                'loveseed_code': loveseed_code,
                'total_downloads': loveseed.get('total_downloads', 0),
                'remaining_downloads': loveseed.get('remaining_downloads', 0),
                'loveseed_status': loveseed.get('status', 'unknown')
            })
        return sorted(result, key=lambda x: x['created_at'] or '', reverse=True)
    
    # 数据库模式
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            """SELECT o.*, l.loveseed_code, l.total_downloads, l.remaining_downloads, 
                      l.status as loveseed_status
               FROM orders o
               LEFT JOIN loveseed_codes l ON o.id = l.order_id
               ORDER BY o.created_at DESC
               LIMIT 1000"""
        )
        orders = cursor.fetchall()
        
        # 格式化日期
        for order in orders:
            if order.get('paid_at'):
                order['paid_at'] = order['paid_at'].strftime('%Y-%m-%d %H:%M:%S')
            if order.get('created_at'):
                order['created_at'] = order['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return orders
        
    except Exception as e:
        logger.error(f"获取订单列表失败: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_all_loveseed_codes_admin():
    """
    获取所有相思豆码列表（管理员功能）
    
    Returns:
        list: 相思豆码列表
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        result = []
        for code, loveseed in MOCK_LOVESEED_CODES.items():
            result.append({
                'loveseed_code': code,
                'order_id': loveseed.get('order_id'),
                'package_id': loveseed.get('package_id'),
                'total_downloads': loveseed.get('total_downloads'),
                'remaining_downloads': loveseed.get('remaining_downloads'),
                'status': loveseed.get('status'),
                'created_at': loveseed.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if loveseed.get('created_at') else None
            })
        return sorted(result, key=lambda x: x['created_at'] or '', reverse=True)
    
    # 数据库模式
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            """SELECT * FROM loveseed_codes 
               ORDER BY created_at DESC
               LIMIT 1000"""
        )
        codes = cursor.fetchall()
        
        # 格式化日期
        for code in codes:
            if code.get('created_at'):
                code['created_at'] = code['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if code.get('updated_at'):
                code['updated_at'] = code['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return codes
        
    except Exception as e:
        logger.error(f"获取相思豆码列表失败: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_loveseed_code_manual(loveseed_code, download_count, package_id=None):
    """
    手动创建相思豆码（管理员功能）
    
    Args:
        loveseed_code: 6位相思豆码
        download_count: 下载次数
        package_id: 套餐ID（可选）
    
    Returns:
        dict: 成功返回相思豆码信息，失败返回 None
    """
    # 验证相思豆码格式
    if not loveseed_code or len(loveseed_code) != 6 or not loveseed_code.isdigit():
        logger.error("相思豆码必须是6位数字")
        return None
    
    # 本地测试模式
    if LOCAL_TEST_MODE:
        # 检查是否已存在
        if loveseed_code in MOCK_LOVESEED_CODES:
            logger.error(f"相思豆码已存在: {loveseed_code}")
            return None
        
        loveseed = {
            'loveseed_code': loveseed_code,
            'order_id': 0,  # 手动创建的没有订单
            'package_id': package_id or 0,
            'total_downloads': download_count,
            'remaining_downloads': download_count,
            'status': 'active',
            'created_at': datetime.now()
        }
        MOCK_LOVESEED_CODES[loveseed_code] = loveseed
        
        logger.info(f"本地测试: 手动创建相思豆码 {loveseed_code}, 次数 {download_count}")
        return loveseed
    
    # 数据库模式
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 检查是否已存在
        cursor.execute("SELECT * FROM loveseed_codes WHERE loveseed_code = %s", (loveseed_code,))
        existing = cursor.fetchone()
        if existing:
            logger.error(f"相思豆码已存在: {loveseed_code}")
            return None
        
        # 选择一个有效套餐（避免 packages 外键失败）
        resolved_package_id = int(package_id) if package_id is not None else int(os.getenv("DEFAULT_MANUAL_PACKAGE_ID", "3"))

        # 为手动相思豆创建一条订单记录（避免 orders/loveseed_codes 的外键失败）
        manual_order_no = f"MANUAL{datetime.now().strftime('%Y%m%d%H%M%S')}{loveseed_code}"
        cursor.execute(
            """INSERT INTO orders (order_no, package_id, amount, status, paid_at)
               VALUES (%s, %s, %s, 'paid', NOW())""",
            (manual_order_no, resolved_package_id, 0)
        )
        order_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO loveseed_codes
               (loveseed_code, order_id, package_id, billing_type, total_downloads, remaining_downloads, status)
               VALUES (%s, %s, %s, 'count', %s, %s, 'active')""",
            (loveseed_code, order_id, resolved_package_id, download_count, download_count)
        )
        
        conn.commit()
        
        logger.info(f"手动创建相思豆码 {loveseed_code}, 次数 {download_count}")
        
        return {
            'loveseed_code': loveseed_code,
            'order_id': order_id,
            'order_no': manual_order_no,
            'package_id': resolved_package_id,
            'total_downloads': download_count,
            'remaining_downloads': download_count,
            'status': 'active'
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"手动创建相思豆码失败: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def delete_loveseed_code_admin(loveseed_code):
    """
    删除相思豆码（管理员功能）
    
    Args:
        loveseed_code: 相思豆码
    
    Returns:
        bool: 成功返回 True，失败返回 False
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        if loveseed_code in MOCK_LOVESEED_CODES:
            del MOCK_LOVESEED_CODES[loveseed_code]
            logger.info(f"本地测试: 删除相思豆码 {loveseed_code}")
            return True
        return False
    
    # 数据库模式
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM loveseed_codes WHERE loveseed_code = %s", (loveseed_code,))
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"删除相思豆码 {loveseed_code}")
            return True
        return False
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"删除相思豆码失败: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_loveseed_downloads_admin(loveseed_code, new_downloads):
    """
    更新相思豆码的剩余次数（管理员功能）
    
    Args:
        loveseed_code: 相思豆码
        new_downloads: 新的剩余次数
    
    Returns:
        bool: 成功返回 True，失败返回 False
    """
    # 本地测试模式
    if LOCAL_TEST_MODE:
        if loveseed_code in MOCK_LOVESEED_CODES:
            MOCK_LOVESEED_CODES[loveseed_code]['remaining_downloads'] = new_downloads
            MOCK_LOVESEED_CODES[loveseed_code]['status'] = 'exhausted' if new_downloads == 0 else 'active'
            logger.info(f"本地测试: 更新相思豆码 {loveseed_code} 剩余次数为 {new_downloads}")
            return True
        return False
    
    # 数据库模式
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        new_status = 'exhausted' if new_downloads == 0 else 'active'
        
        cursor.execute(
            """UPDATE loveseed_codes 
               SET remaining_downloads = %s, status = %s 
               WHERE loveseed_code = %s""",
            (new_downloads, new_status, loveseed_code)
        )
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"更新相思豆码 {loveseed_code} 剩余次数为 {new_downloads}")
            return True
        return False
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"更新相思豆码次数失败: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def check_payment_status(charge_id):
    """
    查询支付状态
    
    Args:
        charge_id: Ping++ Charge ID
    
    Returns:
        dict: 支付状态信息
    """
    charge = retrieve_charge(charge_id)
    
    return {
        'charge_id': charge_id,
        'paid': charge.get('paid', False),
        'order_no': charge.get('order_no', ''),
        'amount': charge.get('amount', 0),
        'transaction_no': charge.get('transaction_no', '')
    }
