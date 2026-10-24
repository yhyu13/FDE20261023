# Research and Decisions

## 已有事实

- prompt2 的核心批评是职责与流程，不是缺少功能页；因此不继续扩张全局菜单。
- 旧 demo 的 spec 明确真实权限/审批不在范围。本次新增“前端演示状态机”，仍不承诺真实安全权限。
- 素材只读调研与角色工作流批评已交两个内部子任务并行；引用核验结果写入 HTML 来源卡和本文件后续小节。
- Playwright Python 官方文档经 Context7 核对：sync API、Chromium、new_context、page.goto；测试走 file:// + offline context，不必启动服务器。

## Decision: 渐进式多角色工作台

六种模拟身份分别有专属首页与命令白名单，DRI 控制总流程；拒绝“只换标题不换操作”的替代方案。

## Decision: 双审→品牌→DRI

审批属于版本，不属于选题。拒绝“总览一键全部通过”和“DRI 超级权限”，否则无法证明分工。

## Decision: 文本 HTML 内嵌图片

用户要求图片又要求单文件断网；缩小后的题目图片以内嵌 data URI 呈现，仅供本地参考，未获对外授权时不能用于放行正文。拒绝远端热链与伪造车型图。

## Boundaries

不用任意文本猜业务角色/成熟度；不用未核验模型输出当证据；不用享道 Robotaxi 规模证明申沃 RoboBus 运营。模板是预置模拟，不调用模型。
