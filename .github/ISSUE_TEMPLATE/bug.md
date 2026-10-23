name: 缺陷
description: 行为与预期不符、数据错了、结果不可信
title: "[BUG] "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        **先复现，再改。** 贴出实际输出与期望输出。
        改 bug 走 `superpowers:systematic-debugging`：先复现 → 看日志 → 查监控 → 查数据 → 定位根因 → 修 + 验。

  - type: textarea
    id: repro
    attributes:
      label: 复现步骤
      description: 别人照着做能复现吗？写清输入、命令、动作
    validations:
      required: true

  - type: textarea
    id: actual
    attributes:
      label: 实际结果
      description: 贴输出，别描述
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: 期望结果
    validations:
      required: true

  - type: dropdown
    id: kind
    attributes:
      label: 这属于哪一类
      options:
        - 检索/召回不准
        - 数据结构化错了（字段错位、口径错）
        - 数字算错
        - 事实编造（生成了不存在的参数/来源）
        - 绕过了人工确认台
        - 环境/部署问题
        - 不确定
    validations:
      required: true

  - type: textarea
    id: impact
    attributes:
      label: 影响面
      description: 影响哪道题、哪个企业场景、有没有已经发出去/签字的东西
    validations:
      required: true

  - type: checkboxes
    id: discipline
    attributes:
      label: 纪律确认
      options:
        - label: 这个问题属于"事实不可信"类（编造/算错/没溯源）——我按红线处理，不降级为"小 bug"
        - label: 我没有在工作树里直接改别人的分支
