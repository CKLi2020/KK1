CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    openid VARCHAR(64) UNIQUE NOT NULL COMMENT '微信用户唯一标识',
    nickname VARCHAR(100) DEFAULT '' COMMENT '用户昵称',
    avatar_url VARCHAR(500) DEFAULT '' COMMENT '用户头像URL',
    is_admin TINYINT(1) DEFAULT 0 COMMENT '是否是管理员',
    member_type ENUM('free', 'monthly', 'quarterly', 'yearly') DEFAULT 'free' COMMENT '会员类型',
    member_expire_time DATETIME DEFAULT NULL COMMENT '会员到期时间',
    total_chars_generated INT DEFAULT 0 COMMENT '累计生成字数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_openid (openid),
    INDEX idx_member_type (member_type),
    INDEX idx_is_admin (is_admin)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 套餐定义表（混合模式：支持按次数和按时间）
CREATE TABLE IF NOT EXISTS packages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL COMMENT '套餐名称',
    type VARCHAR(50) NOT NULL COMMENT '套餐类型',
    price DECIMAL(10, 2) NOT NULL COMMENT '价格（元）',
    billing_type ENUM('count', 'duration') DEFAULT 'count' COMMENT '计费类型：count=按次数, duration=按时间',
    download_count INT NOT NULL DEFAULT 0 COMMENT '下载次数（按次数套餐有效）',
    duration_days INT NOT NULL DEFAULT 0 COMMENT '有效天数（按时间套餐有效）',
    unit_price DECIMAL(10, 3) NOT NULL COMMENT '单价（元/次）',
    description VARCHAR(255) DEFAULT '' COMMENT '套餐描述',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    badge_text VARCHAR(20) DEFAULT '' COMMENT '角标文字',
    badge_color VARCHAR(20) DEFAULT '' COMMENT '角标颜色',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='套餐定义表';

-- 初始化套餐数据（混合模式：按次数 + 按时间）
INSERT INTO packages (name, type, price, billing_type, download_count, duration_days, unit_price, description, badge_text, badge_color) VALUES
-- 按次数套餐
('体验套餐', 'trial', 0.99, 'count', 2, 0, 0.50, '包含2次使用次数（单价¥0.50）', '', ''),
('基础套餐', 'basic', 2.88, 'count', 8, 0, 0.36, '包含8次使用次数（单价¥0.36）', '', ''),
('热门套餐', 'hot', 6.00, 'count', 20, 0, 0.30, '包含20次使用次数（单价¥0.30）', '', ''),
('超值套餐', 'value', 9.00, 'count', 35, 0, 0.26, '包含35次使用次数（单价¥0.26）', '', ''),
('尊享套餐', 'premium', 15.0, 'count', 70, 0, 0.21, '包含70次使用次数（单价¥0.21）', '', ''),
-- 按时间套餐（有效期内无限次使用）
('包月套餐', 'monthly', 29.00, 'duration', 999999, 30, 0.03, '30天内无限次使用（每日低至¥0.97）', '最热', 'blue'),
('季度套餐', 'quarterly', 66.00, 'duration', 999999, 90, 0.02, '90天内无限次使用（每日低至¥0.73）', '限量', 'pink'),
('包年套餐', 'yearly', 199.0, 'duration', 999999, 365, 0.02, '365天内无限次使用（每日低至¥0.55）', '最值', 'yellow');

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(64) UNIQUE NOT NULL COMMENT '订单号',
    user_id INT DEFAULT NULL COMMENT '用户ID（可为空，支付页面不需要登录）',
    package_id INT NOT NULL COMMENT '套餐ID',
    amount DECIMAL(10, 2) NOT NULL COMMENT '支付金额',
    status ENUM('pending', 'paid', 'cancelled', 'refunded') DEFAULT 'pending' COMMENT '订单状态',
    wx_transaction_id VARCHAR(64) DEFAULT NULL COMMENT '微信支付交易号',
    paid_at DATETIME DEFAULT NULL COMMENT '支付时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order_no (order_no),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    FOREIGN KEY (package_id) REFERENCES packages(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- 相思豆表（核心功能表 - 支持混合模式）
CREATE TABLE IF NOT EXISTS loveseed_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loveseed_code VARCHAR(6) UNIQUE NOT NULL COMMENT '相思豆（订单号后6位）',
    order_id INT NOT NULL COMMENT '关联订单ID',
    package_id INT NOT NULL COMMENT '套餐ID',
    billing_type ENUM('count', 'duration') DEFAULT 'count' COMMENT '计费类型：count=按次数, duration=按时间',
    total_downloads INT NOT NULL COMMENT '总下载次数（按次数套餐有效）',
    remaining_downloads INT NOT NULL COMMENT '剩余下载次数（按次数套餐有效）',
    expire_time DATETIME DEFAULT NULL COMMENT '到期时间（按时间套餐有效）',
    status ENUM('active', 'exhausted', 'expired') DEFAULT 'active' COMMENT '状态：活跃/用尽/过期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_loveseed_code (loveseed_code),
    INDEX idx_order_id (order_id),
    INDEX idx_status (status),
    INDEX idx_expire_time (expire_time),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (package_id) REFERENCES packages(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='相思豆表';

-- 下载记录表（记录每次使用相思豆的下载）
CREATE TABLE IF NOT EXISTS download_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loveseed_code VARCHAR(6) NOT NULL COMMENT '相思豆',
    openid VARCHAR(64) DEFAULT NULL COMMENT '用户openid',
    action_type ENUM('generate_image', 'generate_pdf') NOT NULL COMMENT '操作类型',
    char_count INT NOT NULL COMMENT '字数',
    file_size_kb INT DEFAULT 0 COMMENT '文件大小（KB）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '下载时间',
    INDEX idx_loveseed_code (loveseed_code),
    INDEX idx_openid (openid),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='下载记录表';

-- 使用记录表（可选，用于统计）
CREATE TABLE IF NOT EXISTS usage_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT DEFAULT NULL COMMENT '用户ID，未登录为NULL',
    openid VARCHAR(64) DEFAULT NULL COMMENT '用户openid',
    action_type ENUM('preview', 'generate_image', 'generate_pdf') NOT NULL COMMENT '操作类型',
    char_count INT NOT NULL COMMENT '字数',
    has_watermark TINYINT(1) DEFAULT 1 COMMENT '是否有水印',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='使用记录表';

-- 保留旧表（可删除）
CREATE TABLE IF NOT EXISTS user_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE, 
    password VARCHAR(255), 
    image BLOB,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
