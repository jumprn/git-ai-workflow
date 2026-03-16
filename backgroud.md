### 项目背景（给 AI 看得懂的版本）

- **项目名称**：`ai-coverage-dashboard`（AI 代码覆盖率看板）
- **整体目标**：  
  为一组 Git 代码仓库建立一个“AI 代码覆盖率”度量体系，统计和展示：
  - 各项目中由 AI 生成的代码行数（`ai_lines`）
  - 总代码行数（`total_lines`）
  - 不同维度（项目、成员、时间）的 AI 覆盖率（`ai_lines / total_lines`）
- **典型使用场景**：
  - 管理员在系统中配置/接入多个代码仓库（Git 仓库地址 + 访问凭证）。
  - 通过“扫描任务”自动分析仓库的 commit / 文件，识别哪些代码是 AI 生成的，并结构化存储。
  - 通过可视化看板查看：
    - 项目级、成员级的 AI 覆盖率趋势
    - 排行（谁更依赖 AI 写代码）
    - 历史明细，并支持导出 Excel 报表。
- **总体技术栈**：
  - **前端**：Vue 3 + Vite + Vue Router + Pinia + Ant Design Vue + ECharts
  - **后端**：Flask + Flask-SQLAlchemy + Flask-Migrate + APScheduler + PyMySQL + Marshmallow
  - **数据库**：MySQL（通过 `DATABASE_URL` 配置，支持自动建库）

---

### 系统整体架构概览

- **前端应用（`front/`）**：  
  单页应用（SPA），提供仪表盘、项目管理、成员管理、覆盖率查询和系统设置等 UI。
- **后端服务（`kaohe/`）**：  
  Flask API 服务，负责：
  - 项目、成员等基础数据管理
  - 扫描任务调度与进度管理
  - AI 覆盖率数据的统计聚合
  - Excel 导出
- **后台任务与仓库目录**：
  - 通过 `APScheduler` 在后端定时执行扫描任务（根据 `.env` 中的 `SCAN_HOUR` / `SCAN_MINUTE`）。
  - 通过 `REPOS_DIR` 指定本地 Git 仓库存储根目录，将远程仓库克隆到这里再进行分析。

---

### 后端功能架构（`kaohe/app`）

#### 1. 应用与基础设施

- **`__init__.py`**
  - `create_app(config_name=None)`：Flask 应用工厂。
    - 从 `config_map` 加载配置（根据 `FLASK_ENV`）。
    - 创建 `REPOS_DIR` 目录。
    - 调用 `_ensure_mysql_database` 自动创建 MySQL 数据库（如不存在）。
    - 初始化扩展：`db`、`migrate`、`cors`。
    - 注册错误处理：`register_error_handlers(app)`。
    - 注册业务蓝图：`register_blueprints(app)`。
    - 在应用上下文中导入 `models` 并执行 `db.create_all()`。
    - 初始化调度器：`init_scheduler(app)`。
- **`config.py`**
  - 定义多环境配置（开发/测试/生产），包含：
    - `SQLALCHEMY_DATABASE_URI`：来源于 `.env` 的 `DATABASE_URL`。
    - `REPOS_DIR`：仓库根目录（例如 `C:/ai-coverage-repos`）。
    - 其他如 `SECRET_KEY`、定时任务扫描时间等。
- **`extensions.py`**
  - 初始化第三方扩展，如：
    - `db = SQLAlchemy()`
    - `migrate = Migrate()`
    - `cors = CORS()`
- **`scheduler.py`**
  - 使用 `APScheduler` 定义后台定时任务：
    - 定期触发扫描任务（全量或增量），根据 `SCAN_HOUR` / `SCAN_MINUTE` 配置。

- **运行入口 `run.py`**
  - 创建应用并以 `host=0.0.0.0, port=5000, debug=True` 启动服务。

#### 2. 数据模型层（`models/`）

主要模型（根据文件名推断）：

- **`project.py`**
  - 存储项目基础信息：
    - `name`（项目名称）
    - `repo_url`（Git 仓库地址）
    - `branch`（默认分支，如 `main`）
    - 鉴权方式与凭据字段：`auth_type`（token/password）、`auth_token`、`auth_username`、`auth_password`
    - 状态：`status`（`pending`/`cloning`/`ready`/`error`）
    - `last_scan_at`（最后扫描时间）
- **`member.py`**
  - 成员信息：`name`、邮箱或账号，与覆盖数据关联。
- **`coverage.py`**
  - 每日/每次统计的覆盖记录：
    - `date`
    - 关联 `project_id`、`member_id`
    - `ai_lines`、`total_lines`
    - 计算字段 `coverage_rate`
- **`scan_task.py`**
  - 扫描任务状态追踪：
    - `status`（`running`/`completed`/`failed` 等）
    - `progress`（0–100）
    - `current_phase`（例如“克隆仓库”、“分析提交”）
    - `total_commits` / `checked_commits`
    - `total_files` / `scanned_files`
    - `message`（失败原因）
- **`ai_prompt_session.py`**
  - 记录与 AI 相关的 prompt/commit 信息，用于判断某段代码是否为 AI 生成。
- **`commit_ai_status.py`**
  - 对每个 commit 标记 AI 相关性，例如某提交是否主要由 AI 产生。
- **`system_config.py`**
  - 系统级配置表，如全局开关、默认扫描策略等。

#### 3. 业务服务层（`services/`）

- **`git_service.py`**
  - 管理 Git 仓库克隆与更新：
    - 根据项目配置将仓库拉取到 `REPOS_DIR`。
    - 维护本地副本状态，用于后续扫描。
- **`scan_service.py`**
  - 核心扫描逻辑：
    - 支持“增量扫描”（从上次扫描后的新 commit）和“全量扫描”（清空缓存，从头分析所有 commit）。
    - 调用 `git_service` 获取最新仓库。
    - 遍历 commit 和文件，结合 `ai_prompt_session` / `commit_ai_status` 等规则，识别 AI 代码行。
    - 产出结构化覆盖数据写入 `coverage` 等模型。
- **`coverage_service.py`**
  - 覆盖率统计与查询：
    - 按日期、项目、成员聚合 `ai_lines` / `total_lines`。
    - 提供给 dashboard 和覆盖率页面使用的接口数据：
      - 汇总概览
      - 趋势曲线
      - 项目/成员维度排行。
- **`export_service.py`**
  - 导出 Excel 报表：
    - 使用 `openpyxl` 按“项目维度”或“成员维度”导出覆盖率统计表。
- **`export_service.py`**
  - 组合业务数据并生成下载链接（`/api/export/...`）。

#### 4. API 层（`api/`）

`app/api/__init__.py` 将多个蓝图统一注册到主应用，所有路由一般以 `/api/...` 开头，主要模块包括：

- **`projects.py` — 项目管理 API**
  - 列表：`GET /api/projects`
  - 创建：`POST /api/projects`
  - 更新：`PUT /api/projects/<id>`
  - 删除：`DELETE /api/projects/<id>`
  - 与前端 `ProjectsPage.vue` 联动，并触发扫描操作（见下）。
- **`scan.py` — 扫描任务 API**
  - 启动项目扫描（增量/全量）：`POST /api/scan/start`
  - 查询扫描进度：`GET /api/scan/<task_id>/progress`
  - 批量扫描所有项目：`POST /api/scan/all`
- **`members.py` — 成员管理 API**
  - 管理成员列表，用于覆盖率维度过滤与统计。
- **`coverage.py` — 覆盖率查询 API**
  - 明细列表：`GET /api/coverage`
    - 支持条件：`start_date`、`end_date`、`project_id`、`member_id`、分页参数。
  - 覆盖率趋势：`GET /api/coverage/trend`
- **`dashboard.py` — 仪表盘 API**
  - 汇总信息：`GET /api/dashboard/summary`
    - `total_projects`, `total_members`, `avg_coverage`, `total_ai_lines` 等。
  - 覆盖率趋势：`GET /api/dashboard/trend`
  - 项目维度覆盖率：`GET /api/dashboard/by-project`
  - 成员排行：`GET /api/dashboard/ranking`
- **`export.py` — 导出 API**
  - `GET /api/export/by-project`
  - `GET /api/export/by-member`
  - 直接返回 Excel 文件下载。
- **`config.py` — 系统配置 API**
  - 读取/更新系统全局配置（系统设置页面使用）。

- **`errors/`**
  - 统一异常处理和错误响应格式（配合 `utils/response.py` 返回标准 JSON 包装）。

---

### 前端功能架构（`front/src`）

#### 1. 应用骨架

- **`main.js`**
  - 创建 Vue 应用：
    - 使用 `Pinia` 做全局状态管理（如项目列表、成员列表缓存）。
    - 使用 `Vue Router` 管理路由。
    - 使用 `Ant Design Vue` 提供 UI 组件。
- **`App.vue` + `layouts/MainLayout.vue`**
  - `MainLayout` 作为主框架布局（侧边菜单 + 顶部导航 + 内容区域）。
  - 所有业务页面在路由 `children` 中挂载（`/dashboard`、`/coverage` 等）。

- **`router/index.js` 路由结构**
  - `/dashboard`：仪表盘（总览）
  - `/coverage`：覆盖率查询
  - `/projects`：项目管理
  - `/members`：成员管理
  - `/settings`：系统设置
  - 路由 `meta.title` 用于构造页面标题（`AI代码覆盖率看板`）。

#### 2. 主要页面与对应后端模块

- **Dashboard 总览（`views/dashboard/DashboardPage.vue`）**
  - 使用接口：
    - `GET /api/dashboard/summary` → 顶部数字卡片：
      - 项目总数、成员总数、平均 AI 覆盖率、AI 代码行数等。
    - `GET /api/dashboard/trend` → 覆盖率趋势折线图。
    - `GET /api/dashboard/by-project` → 各项目覆盖率柱状图。
    - `GET /api/dashboard/ranking` → 成员覆盖率排名。
  - 功能：
    - 时间范围与项目过滤（影响趋势图）。
    - 汇总不同项目/成员的 AI 覆盖情况。

- **项目管理（`views/projects/ProjectsPage.vue`）**
  - 使用接口：
    - `GET /api/projects`：项目列表。
    - `POST /api/projects`：创建项目。
    - `PUT /api/projects/<id>`：更新项目。
    - `DELETE /api/projects/<id>`：删除项目。
    - `POST /api/scan/start`：对单个项目发起“增量”或“全量”扫描。
    - `GET /api/scan/<task_id>/progress`：轮询扫描进度。
    - `POST /api/scan/all`：对全部项目发起扫描。
  - 特点：
    - 表格中展示项目状态（`pending`/`cloning`/`ready`/`error`）。
    - 支持配置仓库地址、默认分支、认证方式（token/账号密码）。
    - 弹窗显示扫描进度条、当前阶段、commit/文件处理进度等。

- **覆盖率查询（`views/coverage/CoveragePage.vue`）**
  - 使用接口：
    - `GET /api/coverage`：覆盖率明细列表（支持过滤和分页）。
    - `GET /api/coverage/trend`：根据过滤条件的覆盖率趋势。
    - 导出：
      - 打开 `VITE_API_BASE_URL + /api/export/by-project?...`
      - 或 `/api/export/by-member?...` 直接在浏览器下载 Excel。
  - 功能：
    - 条件过滤：时间范围、项目、成员。
    - 覆盖率趋势折线图。
    - 明细表格（日期/成员/项目/AI 行数/总代码行数/覆盖率进度条）。
    - 导出 Excel（按照项目或成员维度）。

- **成员管理（`views/members/MembersPage.vue`）**
  - 使用接口：
    - `GET /api/members` 等（具体实现与覆盖率/仪表盘关联，用于过滤和排行）。
  - 功能：
    - 管理系统中的成员列表。
    - 给覆盖率统计提供维度信息。

- **系统设置（`views/settings/SettingsPage.vue`）**
  - 使用接口：
    - `GET/PUT /api/config` 一类（根据 `config.py` 提供的 API）。
  - 功能：
    - 设置如扫描时间、仓库根路径、访问密钥等系统级配置。

---

### 数据流与扫描流程（简要）

1. **配置项目**
   - 用户在“项目管理”页面添加项目：
     - 输入项目名称、Git 仓库地址、分支、认证方式与凭据。
   - 后端在 `project` 表中保存这些信息。

2. **启动扫描**
   - 用户在前端点击“增量扫描”“全量扫描”，或由定时任务自动触发：
     - 前端调用 `POST /api/scan/start`（传入 `project_id` 和 `full` 标志）。
   - 后端创建 `scan_task` 记录，并通过 `scan_service` 执行具体扫描逻辑。
     - 调用 `git_service` 克隆或拉取最新仓库到 `REPOS_DIR`。
     - 遍历 commit 和文件，结合 `ai_prompt_session`、`commit_ai_status` 等表确定 AI 代码行。
     - 将按项目/成员/日期粒度的统计结果写入 `coverage` 等表。

3. **监控扫描进度**
   - 前端通过 `getScanProgress(task_id)` 每 2 秒轮询：
     - 后端返回 `scan_task` 的当前 `status`、`progress`、`current_phase`、commit/文件数量。
   - 扫描完成后，前端刷新项目列表和相关统计数据。

4. **展示与导出**
   - 仪表盘和覆盖率页面通过各种 API：
     - 汇总统计：`dashboard` 系列接口。
     - 明细统计：`coverage` 系列接口。
   - 导出通过 `export` 系列接口生成 Excel 并直接下载。

---

### 给后续 AI 协作的使用提示

- **如果你要改前端页面**：
  - 页面在 `front/src/views/**`，路由在 `front/src/router/index.js`。
  - 所有后端接口通过 `front/src/api/**` 封装（可以搜索各 API 文件名，例如 `dashboard` / `project` / `scan` / `coverage`）。
  - 全局状态（项目列表、成员列表等）通过 `front/src/stores/app`（`useAppStore`）共享。

- **如果你要改后端接口/逻辑**：
  - 路由定义在 `kaohe/app/api/*.py`，按业务模块拆分。
  - 业务逻辑尽量写在 `services/*.py`，路由函数保持“薄”。
  - 数据表及字段在 `models/*.py`，注意与前端使用字段名保持一致。
  - 定时任务或长时间扫描逻辑需考虑 `APScheduler` 与 `scan_task` 状态更新。

- **环境与配置**：
  - 本地开发时，`.env` 中关键变量：
    - `DATABASE_URL`（MySQL 连接串）
    - `REPOS_DIR`（本地仓库目录）
    - `SCAN_HOUR` / `SCAN_MINUTE`（定时扫描时间）
  - 前端通过 `VITE_API_BASE_URL` 访问后端，禁止在代码中硬编码后端地址。

