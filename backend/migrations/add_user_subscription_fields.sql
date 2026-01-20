-- 迁移脚本：为 users 表添加套餐订阅相关字段
-- 执行时间：2024-XX-XX
-- 说明：添加 current_plan_id、plan_expires_at、plan_quota_reset_at、is_unlimited 字段

-- 检查并添加 current_plan_id 字段
ALTER TABLE `users` 
ADD COLUMN IF NOT EXISTS `current_plan_id` VARCHAR(32) NULL 
COMMENT '当前套餐ID（如 basic_monthly）' 
AFTER `total_used`;

-- 检查并添加 plan_expires_at 字段
ALTER TABLE `users` 
ADD COLUMN IF NOT EXISTS `plan_expires_at` DATETIME NULL 
COMMENT '套餐到期时间' 
AFTER `current_plan_id`;

-- 检查并添加 plan_quota_reset_at 字段
ALTER TABLE `users` 
ADD COLUMN IF NOT EXISTS `plan_quota_reset_at` DATETIME NULL 
COMMENT '配额重置时间（月付每月重置，年付每年重置）' 
AFTER `plan_expires_at`;

-- 检查并添加 is_unlimited 字段
ALTER TABLE `users` 
ADD COLUMN IF NOT EXISTS `is_unlimited` BOOLEAN NOT NULL DEFAULT FALSE 
COMMENT '是否不限次数' 
AFTER `plan_quota_reset_at`;

-- 注意：如果 MySQL 版本不支持 IF NOT EXISTS，请先检查字段是否存在再执行：
-- SELECT COUNT(*) FROM information_schema.COLUMNS 
-- WHERE TABLE_SCHEMA = DATABASE() 
-- AND TABLE_NAME = 'users' 
-- AND COLUMN_NAME = 'current_plan_id';







