-- ============================================================
-- AI代码覆盖率看板 - MySQL 数据库初始化脚本
-- 使用方式: mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS `kaohe` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `kaohe`;

-- -----------------------------------------------------------
-- 1. 项目表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `projects`;
CREATE TABLE `projects` (
    `id`            INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    `name`          VARCHAR(128) NOT NULL                COMMENT '项目名称',
    `repo_url`      VARCHAR(512) NOT NULL                COMMENT '仓库地址',
    `auth_type`     VARCHAR(32)  DEFAULT 'token'         COMMENT '认证类型: token/password',
    `auth_token`    VARCHAR(512) DEFAULT NULL             COMMENT '访问令牌',
    `auth_username` VARCHAR(128) DEFAULT NULL             COMMENT '用户名',
    `auth_password` VARCHAR(512) DEFAULT NULL             COMMENT '密码',
    `local_path`    VARCHAR(512) DEFAULT NULL             COMMENT '本地仓库路径',
    `branch`        VARCHAR(128) DEFAULT 'main'          COMMENT '默认分支',
    `status`        VARCHAR(32)  DEFAULT 'pending'       COMMENT '状态: pending/cloning/ready/error',
    `error_message` TEXT         DEFAULT NULL             COMMENT '错误信息',
    `last_scan_at`  DATETIME     DEFAULT NULL             COMMENT '最后扫描时间',
    `created_at`    DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted`    TINYINT(1)   DEFAULT 0               COMMENT '软删除标记: 0=正常 1=已删除',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目表';

-- -----------------------------------------------------------
-- 2. 成员表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `members`;
CREATE TABLE `members` (
    `id`         INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    `name`       VARCHAR(128) NOT NULL                COMMENT '成员姓名',
    `email`      VARCHAR(128) DEFAULT NULL             COMMENT '邮箱',
    `is_manual`  TINYINT(1)   DEFAULT 0               COMMENT '是否手动添加: 0=自动提取 1=手动',
    `created_at` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` TINYINT(1)   DEFAULT 0               COMMENT '软删除标记: 0=正常 1=已删除',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成员表';

-- -----------------------------------------------------------
-- 3. 覆盖率记录表（已废弃，由 commit_ai_status 直接聚合替代）
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `coverage_records`;
CREATE TABLE `coverage_records` (
    `id`            INT     NOT NULL AUTO_INCREMENT COMMENT '主键',
    `project_id`    INT     NOT NULL                COMMENT '项目ID',
    `member_id`     INT     NOT NULL                COMMENT '成员ID',
    `date`          DATE    NOT NULL                COMMENT '统计日期',
    `ai_lines`      INT     DEFAULT 0               COMMENT 'AI生成代码行数',
    `total_lines`   INT     DEFAULT 0               COMMENT '总代码行数',
    `coverage_rate` DOUBLE  DEFAULT 0.0             COMMENT 'AI代码覆盖率(%)',
    `created_at`    DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_coverage_project_member_date` (`project_id`, `member_id`, `date`),
    KEY `ix_coverage_date` (`date`),
    KEY `ix_coverage_project` (`project_id`),
    KEY `ix_coverage_member` (`member_id`),
    CONSTRAINT `fk_coverage_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_coverage_member`  FOREIGN KEY (`member_id`)  REFERENCES `members` (`id`)  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='覆盖率记录表（已废弃）';

-- -----------------------------------------------------------
-- 4. 扫描任务表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `scan_tasks`;
CREATE TABLE `scan_tasks` (
    `id`              INT         NOT NULL AUTO_INCREMENT COMMENT '主键',
    `project_id`      INT         NOT NULL                COMMENT '项目ID',
    `scan_type`       VARCHAR(32) DEFAULT 'manual'        COMMENT '扫描类型: manual/scheduled',
    `status`          VARCHAR(32) DEFAULT 'pending'       COMMENT '状态: pending/running/completed/failed',
    `progress`        INT         DEFAULT 0               COMMENT '进度百分比 0-100',
    `current_phase`   VARCHAR(64) DEFAULT NULL             COMMENT '当前阶段描述',
    `total_files`     INT         DEFAULT 0               COMMENT '总文件数',
    `scanned_files`   INT         DEFAULT 0               COMMENT '已扫描文件数',
    `total_commits`   INT         DEFAULT 0               COMMENT '总提交数',
    `checked_commits` INT         DEFAULT 0               COMMENT '已检查提交数',
    `message`         TEXT        DEFAULT NULL             COMMENT '消息/错误信息',
    `started_at`      DATETIME    DEFAULT NULL             COMMENT '开始时间',
    `completed_at`    DATETIME    DEFAULT NULL             COMMENT '完成时间',
    `created_at`      DATETIME    DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `ix_scan_project` (`project_id`),
    KEY `ix_scan_status` (`status`),
    CONSTRAINT `fk_scan_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='扫描任务表';

-- -----------------------------------------------------------
-- 5. 系统配置表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `system_configs`;
CREATE TABLE `system_configs` (
    `id`          INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    `key`         VARCHAR(128) NOT NULL                COMMENT '配置键',
    `value`       TEXT         DEFAULT NULL             COMMENT '配置值',
    `description` VARCHAR(256) DEFAULT NULL             COMMENT '配置说明',
    `created_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_config_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- -----------------------------------------------------------
-- 6. 提交AI状态缓存表（增强版）
--    每条记录对应一次 git commit，聚合该提交下所有 AI 会话的数据
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `commit_ai_status`;
CREATE TABLE `commit_ai_status` (
    `id`               INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    `project_id`       INT          NOT NULL                COMMENT '项目ID',
    `member_id`        INT          DEFAULT NULL             COMMENT '成员ID',
    `commit_sha`       VARCHAR(40)  NOT NULL                COMMENT '提交SHA',
    `commit_message`   VARCHAR(512) DEFAULT NULL             COMMENT '提交消息(首行)',
    `is_ai`            TINYINT(1)   DEFAULT 0               COMMENT '是否包含AI辅助: 0=否 1=是',
    `ai_session_count` INT          DEFAULT 0               COMMENT 'AI会话数',
    `primary_tool`     VARCHAR(64)  DEFAULT NULL             COMMENT '主要AI工具(cursor/claude-code等)',
    `author_name`      VARCHAR(128) DEFAULT NULL             COMMENT '提交作者',
    `author_email`     VARCHAR(128) DEFAULT NULL             COMMENT '作者邮箱',
    `committed_at`     DATETIME     DEFAULT NULL             COMMENT '提交时间',
    `commit_date`      DATE         DEFAULT NULL             COMMENT '提交日期(冗余字段便于聚合)',
    `lines_added`      INT          DEFAULT 0               COMMENT '该提交新增行数(git统计)',
    `lines_deleted`    INT          DEFAULT 0               COMMENT '该提交删除行数(git统计)',
    `total_lines`      INT          DEFAULT 0               COMMENT '该提交总变更行数(新增+删除)',
    `ai_lines_added`   INT          DEFAULT 0               COMMENT 'AI贡献新增行数(accepted+overridden)',
    `ai_lines_deleted` INT          DEFAULT 0               COMMENT 'AI贡献删除行数',
    `accepted_lines`   INT          DEFAULT 0               COMMENT 'AI代码被人类原样保留的行数',
    `overridden_lines` INT          DEFAULT 0               COMMENT 'AI代码被人类修改的行数',
    `accepted_rate`    DOUBLE       DEFAULT NULL             COMMENT 'AI代码接受率: accepted/(accepted+overridden)',
    `created_at`       DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_project_commit` (`project_id`, `commit_sha`),
    KEY `ix_commit_ai_is_ai` (`is_ai`),
    KEY `ix_commit_ai_committed_at` (`project_id`, `committed_at`),
    KEY `ix_commit_ai_member` (`member_id`),
    KEY `ix_commit_ai_project_member_date` (`project_id`, `member_id`, `commit_date`),
    KEY `ix_commit_ai_tool` (`primary_tool`),
    CONSTRAINT `fk_commit_ai_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_commit_ai_member`  FOREIGN KEY (`member_id`)  REFERENCES `members` (`id`)  ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='提交AI状态缓存表';

-- -----------------------------------------------------------
-- 7. AI会话明细表（新增）
--    每条记录对应一次 git-ai prompt session，提供最细粒度的AI使用数据
--    数据来源: git-ai search --commit <sha> --json
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `ai_prompt_sessions`;
CREATE TABLE `ai_prompt_sessions` (
    `id`               INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    `project_id`       INT          NOT NULL                COMMENT '项目ID',
    `commit_sha`       VARCHAR(40)  DEFAULT NULL             COMMENT '关联提交SHA',
    `prompt_id`        VARCHAR(64)  NOT NULL                COMMENT 'git-ai 会话ID',
    `tool`             VARCHAR(64)  DEFAULT NULL             COMMENT 'AI工具: cursor/claude-code/copilot等',
    `model`            VARCHAR(128) DEFAULT NULL             COMMENT 'AI模型: claude-sonnet-4/gpt-4等',
    `human_author`     VARCHAR(128) DEFAULT NULL             COMMENT '使用者(git作者)',
    `member_id`        INT          DEFAULT NULL             COMMENT '成员ID',
    `total_additions`  INT          DEFAULT 0               COMMENT '会话涉及的新增行数',
    `total_deletions`  INT          DEFAULT 0               COMMENT '会话涉及的删除行数',
    `accepted_lines`   INT          DEFAULT 0               COMMENT 'AI代码被保留的行数',
    `overridden_lines` INT          DEFAULT 0               COMMENT 'AI代码被修改的行数',
    `accepted_rate`    DOUBLE       DEFAULT NULL             COMMENT '接受率: accepted/(accepted+overridden)',
    `session_start`    DATETIME     DEFAULT NULL             COMMENT '会话开始时间',
    `session_end`      DATETIME     DEFAULT NULL             COMMENT '会话结束时间',
    `session_date`     DATE         DEFAULT NULL             COMMENT '会话日期(便于聚合)',
    `created_at`       DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_project_prompt` (`project_id`, `prompt_id`),
    KEY `ix_prompt_project_commit` (`project_id`, `commit_sha`),
    KEY `ix_prompt_tool` (`tool`),
    KEY `ix_prompt_model` (`model`),
    KEY `ix_prompt_member` (`member_id`),
    KEY `ix_prompt_date` (`session_date`),
    KEY `ix_prompt_member_date` (`member_id`, `session_date`),
    CONSTRAINT `fk_prompt_project` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_prompt_member`  FOREIGN KEY (`member_id`)  REFERENCES `members` (`id`)  ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI会话明细表';

-- -----------------------------------------------------------
-- 初始化默认配置
-- -----------------------------------------------------------
INSERT INTO `system_configs` (`key`, `value`, `description`) VALUES
    ('scan_enabled',       'true', '是否启用定时扫描'),
    ('scan_hour',          '2',    '定时扫描小时 (0-23)'),
    ('scan_minute',        '0',    '定时扫描分钟 (0-59)'),
    ('scan_interval_days', '1',    '扫描间隔天数');

-- -----------------------------------------------------------
-- 增量迁移：仅升级已有数据库时执行（新库已包含上述字段，可跳过）
-- -----------------------------------------------------------
-- ALTER TABLE `commit_ai_status` ADD COLUMN `commit_message`   VARCHAR(512) DEFAULT NULL COMMENT '提交消息(首行)' AFTER `commit_sha`;
-- ALTER TABLE `commit_ai_status` ADD COLUMN `primary_tool`     VARCHAR(64)  DEFAULT NULL COMMENT '主要AI工具' AFTER `ai_session_count`;
-- ALTER TABLE `commit_ai_status` ADD COLUMN `accepted_lines`   INT DEFAULT 0 COMMENT 'AI代码被保留的行数' AFTER `ai_lines_deleted`;
-- ALTER TABLE `commit_ai_status` ADD COLUMN `overridden_lines` INT DEFAULT 0 COMMENT 'AI代码被修改的行数' AFTER `accepted_lines`;
-- ALTER TABLE `commit_ai_status` ADD COLUMN `accepted_rate`    DOUBLE DEFAULT NULL COMMENT 'AI代码接受率' AFTER `overridden_lines`;
-- ALTER TABLE `commit_ai_status` ADD KEY `ix_commit_ai_tool` (`primary_tool`);
--
-- 回填已有数据: 对旧记录将 ai_lines_added 视为 accepted_lines
-- UPDATE `commit_ai_status` SET `accepted_lines` = `ai_lines_added`, `accepted_rate` = 1.0
--     WHERE `is_ai` = 1 AND `accepted_lines` = 0 AND `ai_lines_added` > 0;
