CREATE SCHEMA IF NOT EXISTS common_project;

use common_project;

CREATE TABLE `user` (
	`user_id`	int	NOT NULL	COMMENT 'auto increment',
	`email`	varchar(50)	NOT NULL	COMMENT '사용자 이메일, 실질적으로 로그인 시 사용되는 정보',
	`password`	varchar(50)	NOT NULL	COMMENT '사용자 비밀번호',
	`warehouse_id`	int	NOT NULL	COMMENT '소속 물류 창고 인덱스 외래키',
	`user_name`	varchar(50)	NOT NULL	COMMENT '사용자 이름',
	`phone_number`	varchar(50)	NULL	COMMENT '사용자 연락처'
);

CREATE TABLE `company` (
	`company_id`	int	NOT NULL	COMMENT 'auto increment',
	`company_name`	varchar(50)	NOT NULL	COMMENT '회사 이름'
);

CREATE TABLE `warehouse` (
	`warehouse_id`	int	NOT NULL	COMMENT 'auto increment',
	`warehouse_name`	varchar(50)	NOT NULL	COMMENT '물류 창고 이름, 중복 가능',
	`warehouse_code`	varchar(50)	NOT NULL	COMMENT '물류 창고 유일 식별 코드, 유니크',
	`company_id`	int	NOT NULL	COMMENT '소속 회사 인덱스 외래키'
);

CREATE TABLE `agv` (
	`agv_id`	int	NOT NULL	COMMENT 'auto increment',
	`agv_code`	varchar(50)	NOT NULL	COMMENT 'AGV 유일 식별 코드',
	`warehouse_id`	int	NOT NULL	COMMENT '소속 물류 창고 인덱스 외래키',
	`agv_model`	varchar(50)	NOT NULL
);

CREATE TABLE `agv_log` (
	`log_id`	int	NOT NULL	COMMENT 'auto_increment',
	`log_code`	int	NOT NULL	COMMENT '로그 식별 넘버',
	`location_x`	float	NOT NULL	COMMENT 'x좌표',
	`location_y`	float	NOT NULL	COMMENT 'y좌표',
	`efficiency`	float	NOT NULL	COMMENT '이동 효율성',
	`state`	varchar(50)	NOT NULL	COMMENT '상태',
	`significant`	varchar(100)	NULL	COMMENT 'nullable',
	`log_time`	datetime	NOT NULL	DEFAULT now(),
	`agv_id`	int	NOT NULL	COMMENT 'auto increment'
);

ALTER TABLE `user` ADD CONSTRAINT `PK_USER` PRIMARY KEY (
	`user_id`
);

ALTER TABLE `company` ADD CONSTRAINT `PK_COMPANY` PRIMARY KEY (
	`company_id`
);

ALTER TABLE `warehouse` ADD CONSTRAINT `PK_WAREHOUSE` PRIMARY KEY (
	`warehouse_id`
);

ALTER TABLE `agv` ADD CONSTRAINT `PK_AGV` PRIMARY KEY (
	`agv_id`
);

ALTER TABLE `agv_log` ADD CONSTRAINT `PK_AGV_LOG` PRIMARY KEY (
	`log_id`
);

ALTER TABLE common_project.agv 
ADD COLUMN agv_footnote VARCHAR(255) NULL DEFAULT NULL AFTER agv_model;

