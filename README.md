# 境界数值模型

## 项目目标

本项目用于评估“玩家从炼气一层修炼到最高层”的时间合理性，并提供本地化配置编辑工具。

当前版本已从单文件工具整理为统一本地入口，访问地址：
- `http://localhost:8501`

核心特性：
- 保留原有页面职责：修炼建模、战斗建模、境界配置、历练区域配置、敌人模板配置、丹方配置、术法配置
- 保留现有数据文件格式与保存语义，只写本项目 `data/*.json`
- 继续复用 `src/io/*` 与 `src/model/*` 作为数值逻辑真值
- 支持一键启动，后端同时托管前端静态页面与本地 API

## 数据来源

- `data/realms.json`：初始由服务端 `idle_cultivation_server/app/game/content/cultivation/realms.json` 拷贝
- `data/recipes.json`：初始由服务端 `idle_cultivation_server/app/game/content/alchemy/recipes.json` 拷贝
- `data/areas.json`：初始由服务端 `idle_cultivation_server/app/game/content/lianli/areas.json` 拷贝
- `data/enemies.json`：初始由服务端 `idle_cultivation_server/app/game/content/lianli/enemies.json` 拷贝
- `data/spells.json`：初始由服务端 `idle_cultivation_server/app/game/content/spell/spells.json` 拷贝

## 目录说明

```text
idle_cultivation_numerical_model/
├── backend/
│   ├── app.py                # 本地服务入口
│   └── service.py            # 对现有 io/model 的本地接口包装层
├── data/
├── docs/
├── src/
│   ├── io/
│   └── model/
├── web/
│   ├── src/                  # 页面与组件
│   └── dist/                 # 构建产物，由本地服务托管
└── restart.sh                # 一键启动入口
```

## 开发运行

首次运行：

```bash
cd /Users/hsams/Documents/idle_cultivation_project/idle_cultivation_numerical_model
bash restart.sh
```

启动后访问：

```text
http://localhost:8501
```

`restart.sh` 会负责：
- 创建/复用 `venv`
- 安装 Python 依赖
- 安装前端依赖
- 构建前端页面
- 启动本地服务并托管页面

本地页面资源默认关闭缓存，便于改完代码后直接刷新浏览器查看最新结果。

## 测试

```bash
./venv/bin/python -m pytest tests/test_backend_api.py tests/test_data_sync.py tests/test_realm_generator.py tests/test_material_and_time_model.py
```

## 当前说明

- 当前仓库已完成本地统一入口迁移，不再保留旧页面实现。
- `src/io/*` 与 `src/model/*` 继续作为数值逻辑真值保留。
- 术法配置页继续保留：
  - 灵气：`2-4` 一套递推倍率、`5+` 一套递推倍率
  - 熟练度：`2-4` 一套递推倍率、`5+` 一套递推倍率
  - `attribute_bonus` / `effect` 手动编辑
