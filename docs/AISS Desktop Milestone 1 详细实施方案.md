# AISS Desktop Milestone 1 详细实施方案

> 更新时间：2026-04-29
>
> 本文是 [`图形化桌面产品开发方案.md`](./图形化桌面产品开发方案.md) 的第一阶段施工版，只聚焦 **Milestone 1：只读版 Session Explorer**。目标不是把所有桌面能力一次做完，而是尽快搭起一个真实可跑、可继续扩展的图形化基础层。

## 1. 本阶段目标

Milestone 1 只解决一件事：

**把当前以 CLI、schema 和 synthetic fixture 为主的项目，推进成一个“能读取真实本地会话、能按项目浏览、能看详情”的图形化产品雏形。**

这一阶段只做只读能力，不做高风险写操作。

本阶段明确包含：

- 建立 app-level catalog 的只读数据模型；
- 建立桌面产品需要的第一批 schema；
- 建立本地 App Service API；
- 建立正式前端骨架；
- 做第一版 Session Explorer / Session Detail / Project View；
- 用真实扫描数据驱动 UI；
- 用测试把 schema、API 和页面数据契约兜住。

本阶段明确不包含：

- native rename；
- native path rewrite；
- overlay 编辑；
- backend 配置写入；
- 自动同步；
- 桌面壳打包；
- Codex / Claude 原生互转；
- patch 自动应用。

换句话说，本阶段的交付物应该是：

**一个能看真实本地会话、能理解项目归属、能展示 handoff / excerpts / patch / sync 状态的本地图形化浏览器。**

## 2. 本阶段成功标准

Milestone 1 完成时，至少满足以下成功标准：

1. 应用可以扫描并展示本机 Codex / Claude 会话。
2. 用户可以按工具、项目、状态筛选会话。
3. 用户可以进入会话详情页，查看：
   - 基本信息
   - goal candidate / score / score reasons
   - selected excerpts / all excerpts
   - handoff
   - patch replay 建议
   - latest / sync 状态
4. 前端使用真实 API 数据，不再只靠 synthetic fixture。
5. synthetic fixture 仍保留，作为 UI 开发和契约测试输入。
6. schema、API 和 catalog 输出都有自动化测试。

## 3. 交付范围

本阶段交付范围可以拆成五块：

### 3.1 新 schema

新增 app-level desktop 数据契约。

### 3.2 新 API

新增本地服务接口，给 UI 提供结构化 JSON。

### 3.3 新前端骨架

新增正式前端工程，承接当前原型页和 fixture。

### 3.4 新测试

新增 catalog / API / UI fixture 契约测试。

### 3.5 目录演进

新增 `api/`、`catalog/`、`apps/web/` 等结构，但不推翻现有 CLI。

## 4. 设计原则

本阶段设计遵循五个原则。

### 4.1 Native Read-Only

Codex / Claude 原生会话文件在本阶段只读，不改写。

### 4.2 Reuse Existing Core

最大限度复用当前已有能力：

- adapters
- handoff rendering
- inspect compare metadata
- doctor / patch replay
- protocol schema
- public fixtures

### 4.3 API-First

GUI 不直接 shell out CLI 做主要数据读取，而是建立本地结构化 API。

### 4.4 Fixture-Compatible

新前端必须同时支持：

- 真实 API 数据；
- 现有 `docs/examples/public-sync-state/` synthetic fixture。

### 4.5 Additive Evolution

本阶段所有新增数据结构都应尽量 additive，避免未来 overlay / sync write path 接入时推翻重来。

## 5. 本阶段的系统形态

Milestone 1 推荐形成这样的开发形态：

```text
Native session files
        ↓
Current adapters / core
        ↓
Desktop catalog service
        ↓
Local JSON API
        ↓
Web frontend
```

这里的重点是新增两层：

- `Desktop catalog service`
- `Local JSON API`

它们会成为 GUI 产品后续所有能力的底座。

## 6. 需要新增的 schema

当前项目已经有：

- `manifest.schema.json`
- `inspect-output.schema.json`
- `latest-pointer.schema.json`
- `ui-bundle.schema.json`

Milestone 1 还需要新增 4 份 schema。

## 6.1 `session-catalog.schema.json`

用途：

- 描述会话总览页的数据结构；
- 作为 `GET /sessions` 和 `GET /sessions/{id}` 的基础契约；
- 支撑前端列表、筛选、搜索和详情跳转。

建议放在：

- `docs/schemas/session-catalog.schema.json`

建议顶层结构：

```json
{
  "schema_version": "0.1.0",
  "generated_at": "2026-04-29T10:00:00Z",
  "sessions": [],
  "projects": [],
  "summary": {}
}
```

建议字段：

### `sessions[]`

- `session_key`
- `tool`
- `native_session_id`
- `source_kind`
- `title`
- `native_title`
- `project_id`
- `project_label`
- `updated_at`
- `transcript_path`
- `cwd`
- `score`
- `score_reasons`
- `goal_candidate`
- `excerpt_count`
- `total_excerpt_count`
- `total_user_count`
- `total_assistant_count`
- `latest_state`
- `has_handoff`
- `has_patch`
- `patch_replay_state`
- `status_flags`

### `projects[]`

- `project_id`
- `display_name`
- `session_count`
- `tool_counts`
- `latest_updated_at`
- `roots`

### `summary`

- `total_sessions`
- `total_projects`
- `tool_counts`
- `status_counts`

## 6.2 `session-detail.schema.json`

用途：

- 描述详情页完整载荷；
- 作为 `GET /sessions/{id}` 的主契约。

建议放在：

- `docs/schemas/session-detail.schema.json`

建议顶层结构：

```json
{
  "schema_version": "0.1.0",
  "session": {},
  "manifest": null,
  "inspect": null,
  "handoff": null,
  "patch_replay": null,
  "provenance": {}
}
```

建议字段：

### `session`

以 `session-catalog` 里的单条 session 为基础，再加：

- `raw_message_count`
- `selected_excerpt_count`
- `all_excerpt_count`
- `device_id`
- `provider_profile`

### `manifest`

- 可为空；
- 若存在，要求符合已有 `manifest.schema.json`。

### `inspect`

- 可为空；
- 若存在，要求符合已有 `inspect-output.schema.json` 的某个 tool 子集。

### `handoff`

- `path`
- `title`
- `markdown`
- `summary` 可为空

### `patch_replay`

- 若存在，复用现有 `ui-bundle` 中的 `patch_replay` 结构。

### `provenance`

明确哪些块是：

- `source-of-truth`
- `derived`
- `missing`

注意：这里是 API 的显式返回块，不是 protocol artifact 本身的必填字段。

## 6.3 `project-catalog.schema.json`

用途：

- 描述项目视图的数据结构；
- 支撑 `GET /projects` 和 `GET /projects/{id}`。

建议放在：

- `docs/schemas/project-catalog.schema.json`

建议字段：

- `project_id`
- `display_name`
- `roots`
- `git_remote`
- `branch`
- `head`
- `session_count`
- `active_tools`
- `latest_snapshot_ids`
- `latest_conflicts`
- `sessions`
- `recommended_session_key`

## 6.4 `desktop-ui-bundle.schema.json`

用途：

- 给正式前端一个“一次加载就能跑起来”的聚合输入；
- 兼容现有 `sample-ui-bundle*.json` 思路；
- 用于 UI 开发、故事板、回归测试。

建议放在：

- `docs/schemas/desktop-ui-bundle.schema.json`

这个 schema 本质上是桌面版的 bootstrap payload，建议内嵌：

- `session_catalog`
- `project_catalog`
- `selected_session_detail`
- `view_state`

它不是后端长期唯一输出，但会非常适合前端联调和视觉回归。

## 7. API 设计

Milestone 1 的 API 不求大全，但必须稳定、够前端用。

建议实现成本最低、最容易本地跑的方案：

- Python 内置 HTTP server 或轻量 WSGI/ASGI 层；
- 只做本地监听；
- 返回 JSON；
- 暂不做鉴权；
- 暂不做跨机访问。

## 7.1 API 路径建议

### Health / Meta

- `GET /api/health`
- `GET /api/meta`

### Sessions

- `GET /api/sessions`
- `GET /api/sessions/{session_key}`
- `POST /api/sessions/rescan`

### Projects

- `GET /api/projects`
- `GET /api/projects/{project_id}`

### Fixtures / Dev

- `GET /api/dev/fixture-index`
- `GET /api/dev/fixture/{name}`

这一组接口足够支撑 Milestone 1。

## 7.2 `GET /api/sessions`

用途：

- Session Library 列表；
- 搜索、筛选、排序；
- Dashboard 最近会话。

请求参数建议：

- `tool=codex|claude|all`
- `project_id=<id>`
- `status=dirty|conflict|patch|warning|all`
- `q=<text>`
- `sort=updated_at|score|title`
- `order=asc|desc`
- `limit=<n>`

返回：

- 符合 `session-catalog.schema.json`

## 7.3 `GET /api/sessions/{session_key}`

用途：

- Session Detail 页面；
- 详情页 tab 数据加载。

建议支持 query：

- `include=manifest,inspect,handoff,patch_replay`

返回：

- 符合 `session-detail.schema.json`

建议行为：

- 没有 snapshot 时，`manifest` / `handoff` / `patch_replay` 可以为空；
- 但 `session` 基础块仍然返回；
- `inspect` 至少返回当前选中的 compare 视图数据。

## 7.4 `POST /api/sessions/rescan`

用途：

- 手动刷新本地索引。

请求体建议：

```json
{
  "tools": ["codex", "claude"]
}
```

返回建议：

```json
{
  "ok": true,
  "rescanned_tools": ["codex", "claude"],
  "session_count": 42,
  "project_count": 7,
  "generated_at": "2026-04-29T10:00:00Z"
}
```

## 7.5 `GET /api/projects`

用途：

- Project View 列表；
- Dashboard 最近项目。

返回：

- 符合 `project-catalog.schema.json` 的集合载荷。

## 7.6 `GET /api/projects/{project_id}`

用途：

- Project Detail 页面。

建议包含：

- 项目基本信息；
- 该项目相关 sessions；
- 当前推荐 session；
- 当前 latest pointer 状态；
- 当前 patch / dirty / conflict 聚合提示。

## 8. Catalog 生成逻辑

Milestone 1 需要一个新的内部服务层，用来把当前散落的 core 能力组织成 GUI 友好的数据。

建议新增模块：

- `src/aiss/catalog.py`
- `src/aiss/api.py`

## 8.1 `catalog.py` 职责

负责：

- 扫描 Codex / Claude contexts；
- 统一生成 `session_key`；
- 聚合 project 视图；
- 尝试关联本地 `.ai-session-sync/latest/*`；
- 尝试关联 manifest / handoff / patch_replay；
- 产出 session list、project list、session detail。

### `session_key` 建议

推荐规则：

```text
<tool>:<source_kind>:<native_session_id_or_transcript_hash>
```

示例：

```text
codex:transcript:session-123
claude:transcript:session-claude
claude:history:sha1-abc123
```

要求：

- 稳定；
- 可跨页面引用；
- 不依赖 UI 顺序。

## 8.2 catalog 的三种数据来源

Milestone 1 的 catalog 主要会融合三类来源：

### Source A：native contexts

来自 adapters 的扫描结果。

### Source B：project sync state

来自 `.ai-session-sync/`：

- latest
- manifest
- handoff
- patch

### Source C：derived desktop view model

例如：

- status flags
- project summary
- recommended session
- patch replay summary

要明确区分哪些是 source-of-truth，哪些是 derived。

## 8.3 推荐的 catalog 生成策略

### Step 1

先扫描所有 native contexts。

### Step 2

按 `cwd` / project root / git remote 尝试归类到 project。

### Step 3

若当前项目目录下存在 `.ai-session-sync/`，关联：

- latest pointer
- manifest
- handoff
- patch replay

### Step 4

生成面向 UI 的 summary 字段：

- `status_flags`
- `patch_replay_state`
- `latest_state`
- `has_handoff`

### Step 5

输出 catalog 和 detail payload。

## 9. 前端页面结构

Milestone 1 不做很多页面，重点做好 3 个。

## 9.1 Session Library

目标：

- 第一屏就能看到所有会话；
- 支持快速筛选；
- 支持跳转详情。

建议布局：

- 顶部 toolbar
- 左侧 filter rail
- 右侧 session table / list

### 顶部 toolbar

包含：

- tool segmented control
- 搜索框
- rescan 按钮
- fixture / live mode 切换（开发期）

### 左侧 filter rail

包含：

- 项目列表
- 状态过滤
- 时间排序

### 右侧会话列表

每项展示：

- 标题
- tool
- 项目
- 更新时间
- goal candidate
- score
- dirty / patch / conflict / warning 徽标

## 9.2 Session Detail

目标：

- 让用户真正看懂一个会话，而不是只看到一条摘要。

建议布局：

- 顶部 summary bar
- 中间 tabs
- 右侧 context panel（可选）

建议 tabs：

- `Overview`
- `Excerpts`
- `Handoff`
- `Patch`
- `Sync`

Milestone 1 先不做完整 Transcript tab 也可以，避免第一阶段 UI 过重。

### Overview

展示：

- title / native title
- session id
- transcript path
- project
- goal candidate
- score reasons
- counts

### Excerpts

直接复用当前 compare 视图设计：

- selected excerpts 面板
- all excerpts 面板
- selected vs trimmed 对照

### Handoff

展示：

- handoff markdown；
- import prompt 预览入口；
- 相关 artifact path。

### Patch

展示：

- patch 是否存在；
- state；
- plain apply / 3way / branch 建议；
- 推荐命令。

### Sync

展示：

- latest pointer 状态；
- manifest 路径；
- current snapshot id；
- conflict candidates；
- sidecar backend 简表。

## 9.3 Project View

目标：

- 让用户从“项目视角”而不是“会话视角”看交接状态。

建议布局：

- 项目头部 summary
- 会话列表
- 当前推荐 session detail preview

展示：

- git remote / branch / head
- sessions under project
- latest status
- patch / dirty / conflict 汇总

## 10. 前端技术形态建议

Milestone 1 建议直接建正式前端工程，而不是继续扩写单个 HTML 文件。

推荐：

- `apps/web/`
- TypeScript
- React
- Vite

原因：

- 与当前 fixture / schema / prototype 思路最兼容；
- 开发体验最好；
- 后面接桌面壳最顺。

## 10.1 现有原型资产如何迁移

当前：

- `docs/examples/public-sync-state/conflict-prototype.html`
- `conflict-prototype.css`
- `conflict-prototype.js`

建议迁移方式：

### 保留原型页

作为协议演示资产继续保留，不删除。

### 在 `apps/web/` 中重建组件

优先抽出：

- data source panel
- session list row
- latest conflict card
- compare timeline
- patch replay panel

### fixture loader 复用

开发期允许：

- 加载 `docs/examples/public-sync-state/*.json`
- 切换 live API / fixture API

这样可以保持前端开发的稳定节奏。

## 11. 测试方案

Milestone 1 至少要新增 4 组测试。

## 11.1 Schema contract tests

新增文件建议：

- `tests/test_desktop_schema_contracts.py`

校验：

- `session-catalog.schema.json`
- `session-detail.schema.json`
- `project-catalog.schema.json`
- `desktop-ui-bundle.schema.json`

也要校验 synthetic desktop fixtures。

## 11.2 Catalog generation tests

新增文件建议：

- `tests/test_catalog.py`

覆盖：

- Codex / Claude contexts 被正确聚合进 sessions；
- project grouping 正确；
- latest / manifest / handoff / patch_replay 能被关联；
- status_flags 生成正确；
- `session_key` 稳定。

## 11.3 API tests

新增文件建议：

- `tests/test_api.py`

覆盖：

- `GET /api/health`
- `GET /api/sessions`
- `GET /api/sessions/{id}`
- `GET /api/projects`
- `POST /api/sessions/rescan`

重点不是 HTTP 框架，而是 JSON shape 和过滤行为。

## 11.4 Frontend contract / fixture tests

若前端工程落地，建议至少有：

- fixture load smoke test
- live payload parse smoke test
- selected/all excerpts compare join test
- provenance rendering test

前端测试文件可以放：

- `apps/web/src/__tests__/`

## 12. 需要新增的 synthetic desktop fixtures

Milestone 1 最好补一组专门面向桌面前端的样例，不要只复用现在偏 sync-state 的 bundle。

建议新增目录：

- `docs/examples/desktop/`

建议样例：

- `sample-session-catalog.json`
- `sample-session-detail-codex.json`
- `sample-session-detail-claude.json`
- `sample-project-catalog.json`
- `sample-desktop-ui-bundle.json`

建议继续补两个状态变体：

- `sample-session-detail-conflict.json`
- `sample-session-detail-dirty.json`

这样前端在 Milestone 1 就能同时看：

- 普通态
- dirty 态
- conflict 态

## 13. 目录改造建议

本阶段建议做增量式目录改造。

## 13.1 Python 侧

建议新增：

```text
src/aiss/
  api.py
  catalog.py
```

后续如有必要再拆：

- `src/aiss/catalog/`
- `src/aiss/api/`

Milestone 1 先不要过度模块化。

## 13.2 文档与 schema

建议新增：

```text
docs/
  schemas/
    session-catalog.schema.json
    session-detail.schema.json
    project-catalog.schema.json
    desktop-ui-bundle.schema.json
  examples/
    desktop/
      sample-session-catalog.json
      sample-session-detail-codex.json
      sample-session-detail-claude.json
      sample-project-catalog.json
      sample-desktop-ui-bundle.json
```

## 13.3 前端工程

建议新增：

```text
apps/
  web/
    package.json
    src/
    public/
```

Milestone 1 不需要 `apps/desktop/`。

## 13.4 测试

建议新增：

```text
tests/
  test_desktop_schema_contracts.py
  test_catalog.py
  test_api.py
```

## 14. 开发顺序建议

Milestone 1 我建议按下面顺序推进。

## Step 1：先定 schema

先做：

- session-catalog schema
- session-detail schema
- project-catalog schema
- desktop-ui-bundle schema

不先定 schema，后面的 API 和前端很容易来回漂。

## Step 2：再做 synthetic desktop fixtures

先让前端和测试有稳定输入。

## Step 3：实现 `catalog.py`

把当前 adapters / sync state / patch replay 聚成 GUI 需要的数据。

## Step 4：实现 `api.py`

先把本地 JSON API 跑起来。

## Step 5：建立前端工程

先用 fixture 跑通页面，再切 live API。

## Step 6：补测试

最后把：

- schema
- catalog
- api
- fixture

一起锁住。

## 15. Milestone 1 结束后的状态

Milestone 1 完成后，项目应当进入这样的状态：

- 已有正式前端工程；
- 已有本地 API；
- 已有真实 session list / detail 页面；
- 已有 app-level catalog 雏形；
- 已有桌面产品第一批 schema；
- 已有 desktop synthetic fixtures；
- 已有对应自动化测试。

这时项目虽然还没有“可编辑 overlay”和“桌面壳安装包”，但已经真正完成了从“CLI 工具”到“图形化产品底座”的过渡。

## 16. Milestone 1 之后最自然的下一步

Milestone 1 做完之后，最自然进入的就是 Milestone 2：

**Overlay 编辑层**

也就是把以下能力接上：

- display name override
- project binding override
- tags / notes / archive
- path remap rules

因为当只读浏览器搭起来以后，这些编辑能力就会成为用户最直接、最自然的下一层需求。
