# 境界数值模型（Streamlit）

## 项目目标

本项目用于评估“玩家从炼气一层修炼到最高层”的时间合理性，当前一期仅覆盖境界模型。

核心特性：
- 支持在页面动态调参并实时重算
- 左侧四页布局：首页分析、境界配置、丹方配置、战斗建模
- 首页可预览未保存草稿配置的效果
- 炼气期手动编辑保留
- 筑基1层起自动生成后续层级数值
- 展示四类时间：层间灵气、层间材料、累计灵气、累计材料
- 保存只写本项目 `data/realms.json`，不反向修改服务端
- 战斗建模页支持普通历练区域收益分析（固定提速策略：每次死亡前最多30场、最多3次仿真、剩余血量比例外推）

## 数据来源

- `data/realms.json`：初始由服务端 `idle_cultivation_server/app/modules/cultivation/realms.json` 拷贝
- `data/recipes.json`：初始由服务端 `idle_cultivation_server/app/modules/alchemy/recipes.json` 拷贝
- `data/areas.json`：初始由服务端 `idle_cultivation_server/app/modules/lianli/areas.json` 拷贝
- `data/enemies.json`：初始由服务端 `idle_cultivation_server/app/modules/lianli/enemies.json` 拷贝

## 建模说明

- 建模范围与可调配置总表见：`docs/modeling_scope.md`

## 时间口径

- 层间耗时：小时
- 累计总耗时：天
- 显示格式：保留两位小数并去尾零（如 `12`、`12.5`、`12.34`）

## 开发运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 测试

```bash
python -m pytest tests
```

## 目录结构

```text
idle_cultivation_numerical_model/
├── app.py
├── data/
│   ├── realms.json
│   └── recipes.json
├── src/
│   ├── io/
│   ├── model/
│   └── ui/
└── tests/
```
