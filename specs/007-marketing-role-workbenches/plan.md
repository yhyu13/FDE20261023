# Implementation Plan: 分角色营销协作台

**Branch**: `007-marketing-role-workbenches` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

## Summary

单 HTML、六角色工作台、共享状态机。默认身份选择页；DRI 首页以项目流转/阻断/责任为核心，职能首页以自己的待办为核心。材料与详情渐进展开，不把所有模块堆到首页。

## Technical Context

- 原生 HTML/CSS/JavaScript；无运行时依赖、CDN、远端字体或网络 API。
- 内联 JSON 作为证据与演示初始数据；题目图片缩小后以 data URI 内嵌，不创建入库二进制。
- localStorage 独立 key `sunwin.role-demo.v1`；版本和 schema 校验、拒绝损坏数据；存储异常显示仅会话模式。
- pytest + Playwright Python 作为交付验收层；Chromium file:// 离线 context、网络/控制台监听、桌面与 390px 截图。
- 所有命令集中经过角色白名单、枚举/引用校验与状态前置条件；UI 隐藏不是权限判定。
- UI 定位：克制、清晰的企业协作软件，不是营销落地页。暖白底、墨色侧栏、青绿主色、细线分隔、单任务焦点。

## Constitution Check

- 用户已确认新 AC；不改原六题。四个 L2 与机制/复用在 spec 中。
- 本次明确为单文件 mock，非生产 Python/Streamlit 架构；不接模型，不以模板冒充 AI。
- 先写 FR 同名测试并确认缺实现而失败，再实现；保留红绿输出摘要。
- 一人写工作树，两个内部子任务只读；不新建用户可见 Agent Manager 会话。
- 企业事实回链，低置信度和图片授权未确认阻断；模拟数据不宣称真实效果。
- 无用户提交授权，规格先落盘但不 commit；交付未提交文件，不执行远端动作。
- 实际 gate 只识别 `NNN-slug` 分支，故使用 `007-marketing-role-workbenches`，不改 gate 以迎合结果。

## Project Structure

```text
specs/007-marketing-role-workbenches/
  spec.md / plan.md / research.md / data-model.md / quickstart.md / tasks.md
  checklists/requirements.md
  contracts/workflow.md
assets/day1024_sol_v1_v2/
  index.html               # 唯一运行时交付
  verify_demo.py           # 独立浏览器证据/截图入口
  validation.md            # 验证结果与边界
tests/test_day1024_sol_roles.py
```

## Implementation Strategy

先以 T01 跑通完整纵切，再接入三类客群/四类渠道与材料详情。事实调研、现有 UI 批评只读并行；实现串行，避免 HTML 文件冲突。静态来源只在启动时加载，动态状态统一保存在 state 中；所有视图由同一 state 渲染。

### 2026-10-24 业务范围纠偏

资料从静态 SOURCES 改为有版本的 state.sources：新增/更新、原句建议、标签纠正、技术/项目/品牌逐步确认。来源变更会撤销下游当前审批并使关系过期，历史快照不覆盖。内容一级导航改为“内容制作台 / 资料收集与标注 / 场景与传播关系 / 来源与素材”；排期和批准口径降为首页辅助入口。

场景识别使用明确白名单与命中解释，不用自由文本决定业务状态。推荐只读当前可用资料的结构化能力与客群，成本类无可用测算返回缺口，未知类返回未匹配。关系需人工确认后交 DRI，记录 sourceVersions 与事实片段。演示不发任何网络请求，登记链接不冒充已抓取。

## Complexity Tracking

不引入框架、后端或复杂路由。状态机、版本和导出不可省，否则无法验证用户最核心的“分工明确、DRI 管总流程”。
