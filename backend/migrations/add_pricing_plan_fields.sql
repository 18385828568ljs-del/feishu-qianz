-- 迁移脚本：为 pricing_plans 表添加月付/年付相关字段
-- 执行时间：2024-XX-XX
-- 说明：添加计费类型、月付/年付价格、不限次数等字段，支持固定套餐方案

-- 检查并添加 billing_type 字段
ALTER TABLE `pricing_plans` 
ADD COLUMN IF NOT EXISTS `billing_type` VARCHAR(16) NOT NULL DEFAULT 'monthly' 
COMMENT '计费类型：monthly 或 yearly' 
AFTER `description`;

-- 检查并添加 monthly_price 字段
ALTER TABLE `pricing_plans` 
ADD COLUMN IF NOT EXISTS `monthly_price` INT NULL 
COMMENT '月付价格（分），用于年付套餐显示节省' 
AFTER `billing_type`;

-- 检查并添加 yearly_price 字段
ALTER TABLE `pricing_plans` 
ADD COLUMN IF NOT EXISTS `yearly_price` INT NULL 
COMMENT '年付价格（分），用于月付套餐显示节省' 
AFTER `monthly_price`;

-- 检查并添加 unlimited 字段
ALTER TABLE `pricing_plans` 
ADD COLUMN IF NOT EXISTS `unlimited` BOOLEAN NOT NULL DEFAULT FALSE 
COMMENT '是否不限次数' 
AFTER `yearly_price`;

-- 检查并添加 save_percent 字段
ALTER TABLE `pricing_plans` 
ADD COLUMN IF NOT EXISTS `save_percent` INT NULL 
COMMENT '年付节省百分比（如24表示节省24%）' 
AFTER `unlimited`;

-- 修改 quota_count 字段允许 NULL（因为不限次数的套餐为 NULL）
ALTER TABLE `pricing_plans` 
MODIFY COLUMN `quota_count` INT NULL 
COMMENT '签名次数（NULL表示不限次数）';

-- 清理旧套餐数据（可选，系统会自动重新初始化固定套餐）
-- DELETE FROM `pricing_plans`;

-- 注意：如果 MySQL 版本不支持 IF NOT EXISTS，请先检查字段是否存在再执行：
-- SELECT COUNT(*) FROM information_schema.COLUMNS 
-- WHERE TABLE_SCHEMA = DATABASE() 
-- AND TABLE_NAME = 'pricing_plans' 
-- AND COLUMN_NAME = 'billing_type';

