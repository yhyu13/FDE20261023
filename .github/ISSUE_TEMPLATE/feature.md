name: 功能 / 需求
description: 新增一类能力、改验收口径、或者把某道题的 spec 往前推一步
title: "[NNN] "
labels: ["feature"]
body:
  - type: markdown
    attributes:
      value: |
        **先确认三件事，再往下填**（AGENTS.md §7）：
        1. 这是不是要**先写 spec**？下列任一情况 → 先写 `specs/NNN-slug/spec.md` 并先提交：
           新增一类要落库的数据 / 改跨模块契约 / 动验收口径 / 「到底该做成什么样」本身有争议
        2. 这次改动落在三层拆解树的**哪一层**？L2 缺口编号 + L3 机制名
        3. 是不是**只有一个人**在做？如果要并行 → 开工作树，不要在同���棵树上打架

  - type: input
    id: l2
    attributes:
      label: L2 能力缺口
      description: 这次改动补的是哪条缺口？例：L2-2 工单与手册不连通
      placeholder: L2-N
    validations:
      required: true

  - type: input
    id: l3
    attributes:
      label: L3 机制
      description: 用哪条机制实现？例：工单本体（Ontology 三步法）
    validations:
      required: true

  - type: textarea
    id: problem
    attributes:
      label: 业务问题
      description: 用业务语言说清「谁的什么问题」，不要用技术词。附上现场证据（照片/工单号/日志）
    validations:
      required: true

  - type: textarea
    id: scope
    attributes:
      label: 范围
      description: 做什么 + **不做什么**
    validations:
      required: true

  - type: textarea
    id: ac
    attributes:
      label: 验收标准（AC）
      description: |
        每条 AC 必须可判定，且**必须有一条同名测试**（测试名以 `FR-xxx` 开头）。
        基线未知的写「Day1 实测」，不许先填一个好看的数。
        例：
        - FR-001：报价台账里每个数字都能点回原文件的页码与置信度
    validations:
      required: true

  - type: textarea
    id: reuse
    attributes:
      label: 同族复用
      description: 这个机制还能一并解决什么问题？须满足：同数据形态 + 同痛点 + 不换业务知识
    validations:
      required: true

  - type: textarea
    id: risks
    attributes:
      label: 风险与兜底
      description: 出错会怎样？怎么兜？涉及合规/安全的写清阻断点
    validations:
      required: true

  - type: checkboxes
    id: gates
    attributes:
      label: 闸
      options:
        - label: 我知道低置信度结果要走人工确认台，不会自动进主表
        - label: 我知道要签字的数字必须可溯源，LLM 不做算术
        - label: 本单不涉及打 tag / 部署公网 / 删数据 / 改验收标准（涉及请另开单并先问）
