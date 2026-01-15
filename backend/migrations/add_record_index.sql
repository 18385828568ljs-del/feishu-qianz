-- 迁移脚本：为 sign_forms 表添加 record_index 字段
-- 执行时间：2024-01-XX
-- 说明：添加记录条索引字段，用于标识表单对应的记录条

-- 检查字段是否存在，如果不存在则添加
ALTER TABLE `sign_forms` 
ADD COLUMN IF NOT EXISTS `record_index` INT NOT NULL DEFAULT 1 COMMENT '记录条索引，默认为1（记录条1）' 
AFTER `creator_refresh_token`;

-- 注意：如果 MySQL 版本不支持 IF NOT EXISTS，请使用以下语句：
-- ALTER TABLE `sign_forms` 
-- ADD COLUMN `record_index` INT NOT NULL DEFAULT 1 COMMENT '记录条索引，默认为1（记录条1）' 
-- AFTER `creator_refresh_token`;

