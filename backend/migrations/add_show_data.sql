-- 为 sign_forms 表添加 show_data 字段
-- 用于标记是否在表单中显示关联记录的数据

ALTER TABLE `sign_forms` 
ADD COLUMN `show_data` BOOLEAN NOT NULL DEFAULT FALSE 
COMMENT '是否在表单中显示关联记录的数据' 
AFTER `record_index`;

