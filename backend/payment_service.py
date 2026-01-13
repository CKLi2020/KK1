"""
Ping++ 支付服务
支持微信支付、支付宝支付
"""
import os
from datetime import datetime
import hashlib
import random
import string

# Ping++ 配置
PINGPP_API_KEY = os.getenv('PINGPP_API_KEY', 'sk_test_your_api_key_here')  # 请在 .env 中配置
PINGPP_APP_ID = os.getenv('PINGPP_APP_ID', 'app_your_app_id_here')  # 请在 .env 中配置

# 本地测试模式
LOCAL_TEST_MODE = os.getenv('LOCAL_TEST_MODE', 'true').lower() == 'true'

# 条件导入 pingpp（仅在非测试模式下）
if not LOCAL_TEST_MODE:
    try:
        import pingpp
        pingpp.api_key = PINGPP_API_KEY
    except ImportError:
        print("Warning: pingpp module not available, using test mode")
        LOCAL_TEST_MODE = True


def generate_order_no():
    """生成订单号"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"LS{timestamp}{random_str}"


def create_payment_charge(order_no, amount, channel, subject, body, client_ip, extra=None):
    """
    创建 Ping++ 支付凭据
    
    Args:
        order_no: 订单号
        amount: 金额（单位：分）
        channel: 支付渠道 ('wx_pub_qr' - 微信扫码, 'alipay_qr' - 支付宝扫码, 
                           'wx_wap' - 微信H5, 'alipay_wap' - 支付宝H5)
        subject: 商品标题
        body: 商品描述
        client_ip: 客户端IP
        extra: 额外参数
        
    Returns:
        dict: Ping++ Charge 对象
    """
    if LOCAL_TEST_MODE:
        # 本地测试模式：返回模拟数据
        return create_mock_charge(order_no, amount, channel, subject)
    
    try:
        import pingpp  # 延迟导入
        # 创建 Charge
        charge = pingpp.Charge.create(
            order_no=order_no,
            app=dict(id=PINGPP_APP_ID),
            channel=channel,
            amount=amount,
            client_ip=client_ip,
            currency='cny',
            subject=subject,
            body=body,
            extra=extra or {}
        )
        
        return {
            'id': charge.id,
            'object': charge.object,
            'created': charge.created,
            'livemode': charge.livemode,
            'paid': charge.paid,
            'refunded': charge.refunded,
            'app': charge.app,
            'channel': charge.channel,
            'order_no': charge.order_no,
            'client_ip': charge.client_ip,
            'amount': charge.amount,
            'amount_settle': charge.amount_settle,
            'currency': charge.currency,
            'subject': charge.subject,
            'body': charge.body,
            'extra': charge.extra,
            'time_paid': charge.time_paid,
            'time_expire': charge.time_expire,
            'time_settle': charge.time_settle,
            'transaction_no': charge.transaction_no,
            'refunds': charge.refunds,
            'amount_refunded': charge.amount_refunded,
            'failure_code': charge.failure_code,
            'failure_msg': charge.failure_msg,
            'metadata': charge.metadata,
            'credential': charge.credential,
            'description': charge.description
        }
        
    except Exception as e:
        print(f"创建支付凭据失败: {str(e)}")
        raise


def create_mock_charge(order_no, amount, channel, subject):
    """
    创建模拟支付凭据（测试用）
    """
    # 生成模拟的二维码内容
    qr_code_url = f"https://qr.alipay.com/mock_{order_no}" if 'alipay' in channel else f"weixin://wxpay/bizpayurl?pr=mock_{order_no}"
    
    # 根据渠道返回不同的凭据
    credential = {}
    if channel in ['wx_pub_qr', 'wx_pub']:
        # 微信扫码支付
        credential = {
            'wx_pub_qr': {
                'code_url': qr_code_url
            }
        }
    elif channel == 'alipay_qr':
        # 支付宝扫码支付
        credential = {
            'alipay_qr': {
                'qr_code': qr_code_url
            }
        }
    elif channel == 'wx_wap':
        # 微信H5支付
        credential = {
            'wx_wap': {
                'mweb_url': f"https://wx.tenpay.com/cgi-bin/mmpayweb-bin/checkmweb?prepay_id=mock_{order_no}"
            }
        }
    elif channel == 'alipay_wap':
        # 支付宝手机网站支付
        credential = {
            'alipay_wap': {
                '_url': f"https://mapi.alipay.com/gateway.do?mock_order={order_no}"
            }
        }
    
    return {
        'id': f'ch_mock_{order_no}',
        'object': 'charge',
        'created': int(datetime.now().timestamp()),
        'livemode': False,
        'paid': False,
        'refunded': False,
        'app': PINGPP_APP_ID,
        'channel': channel,
        'order_no': order_no,
        'client_ip': '127.0.0.1',
        'amount': amount,
        'amount_settle': amount,
        'currency': 'cny',
        'subject': subject,
        'body': subject,
        'extra': {},
        'time_paid': None,
        'time_expire': int(datetime.now().timestamp()) + 3600,  # 1小时后过期
        'time_settle': None,
        'transaction_no': None,
        'refunds': {'object': 'list', 'url': '/v1/charges/ch_mock/refunds', 'has_more': False, 'data': []},
        'amount_refunded': 0,
        'failure_code': None,
        'failure_msg': None,
        'metadata': {},
        'credential': credential,
        'description': None
    }


def retrieve_charge(charge_id):
    """
    查询支付凭据
    
    Args:
        charge_id: Charge ID
        
    Returns:
        dict: Charge 对象
    """
    if LOCAL_TEST_MODE:
        # 本地测试模式：返回模拟数据（模拟已支付）
        return {
            'id': charge_id,
            'object': 'charge',
            'paid': True,  # 测试模式下直接返回已支付
            'order_no': charge_id.replace('ch_mock_', ''),
            'amount': 100,
            'transaction_no': f'mock_txn_{datetime.now().timestamp()}'
        }
    
    try:
        import pingpp  # 延迟导入
        charge = pingpp.Charge.retrieve(charge_id)
        return charge
    except Exception as e:
        print(f"查询支付凭据失败: {str(e)}")
        raise


def verify_webhook_signature(raw_data, signature):
    """
    验证 Ping++ Webhook 签名
    
    Args:
        raw_data: 原始请求体（bytes）
        signature: Ping++ 签名
        
    Returns:
        bool: 签名是否有效
    """
    if LOCAL_TEST_MODE:
        return True  # 测试模式跳过验证
    
    try:
        import pingpp  # 延迟导入
        public_key_path = os.getenv('PINGPP_PUBLIC_KEY_PATH', 'pingpp_public_key.pem')
        return pingpp.verify_signature(raw_data, signature, public_key_path)
    except Exception as e:
        print(f"验证签名失败: {str(e)}")
        return False


def get_payment_channels():
    """
    获取支持的支付渠道
    
    Returns:
        list: 支付渠道列表
    """
    return [
        {
            'id': 'wx_pub_qr',
            'name': '微信扫码支付',
            'type': 'qr_code',
            'description': 'PC端扫码支付',
            'icon': 'wechat'
        },
        {
            'id': 'alipay_qr',
            'name': '支付宝扫码支付',
            'type': 'qr_code',
            'description': 'PC端扫码支付',
            'icon': 'alipay'
        },
        {
            'id': 'wx_wap',
            'name': '微信H5支付',
            'type': 'redirect',
            'description': '手机浏览器跳转支付',
            'icon': 'wechat'
        },
        {
            'id': 'alipay_wap',
            'name': '支付宝手机网站支付',
            'type': 'redirect',
            'description': '手机浏览器跳转支付',
            'icon': 'alipay'
        }
    ]


def format_amount_to_cents(yuan_amount):
    """
    将元转换为分
    
    Args:
        yuan_amount: 金额（元）
        
    Returns:
        int: 金额（分）
    """
    return int(float(yuan_amount) * 100)
