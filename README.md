# 数值模型 -  idle_cultivation_numerical_model

## 项目概述

该项目是放置修仙放置游戏的数值模型，用于模拟和计算游戏中的各种数值参数，如升级所需经验、资源产出率、战斗平衡等。

## 主要功能

- 经验系统：计算不同等级所需的经验值
- 资源系统：模拟资源产出和消耗
- 战斗系统：计算伤害、防御和胜率
- 升级系统：计算属性成长和技能效果
- 平衡调整：通过参数调整实现游戏平衡

## 目录结构

```
idle_cultivation_numerical_model/
├── README.md          # 项目说明
├── .gitignore         # Git忽略文件
├── src/               # 源代码目录
│   ├── experience/    # 经验系统
│   ├── resource/      # 资源系统
│   ├── combat/        # 战斗系统
│   └── upgrade/       # 升级系统
└── tests/             # 测试目录
```

## 技术栈

- Python 3.10+
- NumPy (数值计算)
- Pandas (数据处理)
- Matplotlib (数据可视化)
- Pytest (单元测试)

## 开发流程

1. 定义数值模型参数
2. 实现核心计算逻辑
3. 运行测试验证结果
4. 调整参数优化平衡
5. 生成数据报告

## 贡献指南

1. 克隆仓库
2. 创建分支
3. 实现功能
4. 运行测试
5. 提交PR

## 联系信息

- 项目链接：[https://github.com/wcc11404/idle_cultivation_numerical_model](https://github.com/wcc11404/idle_cultivation_numerical_model)
