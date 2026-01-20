-- 为 sign_forms 表添加 creator_session_id 字段
-- 用于从 USER_TOKENS 获取最新的 refresh_token，避免使用已被刷新过的旧 token

ALTER TABLE `sign_forms` 
ADD COLUMN `creator_session_id` VARCHAR(64) NULL 
COMMENT '创建者的 session_id（用于从 USER_TOKENS 获取最新的 refresh_token）' 
AFTER `created_by`;

-- 为 creator_session_id 添加索引（可选，如果经常需要根据 session_id 查询）
-- CREATE INDEX `idx_creator_session_id` ON `sign_forms` (`creator_session_id`);

