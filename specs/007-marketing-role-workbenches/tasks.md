# Tasks: 分角色营销协作台

**Input**: 本目录 spec / plan / research / data-model / contracts。

## Phase 1: Setup

- [x] T001 确认新增 AC 并创建 `specs/007-marketing-role-workbenches/spec.md`。
- [x] T002 执行 spec-kit setup-plan / setup-tasks，填写本目录设计文件。

## Phase 2: Foundational

- [ ] T003 在 `tests/test_day1024_sol_roles.py` 写 FR-001–011 测试并运行，确认成品缺失导致失败。
- [ ] T004 在 `assets/day1024_sol_v1_v2/index.html` 实现共享命令守卫、状态与只读测试接口。

## Phase 3: US1 职责分离

- [ ] T005 [US1] 在 `assets/day1024_sol_v1_v2/index.html` 实现六身份入口、专属首页/导航、越权拒绝；运行 FR-001/002。

## Phase 4: US2 可信选题

- [ ] T006 [US2] 在 `assets/day1024_sol_v1_v2/index.html` 写来源、客户问题、图片、日历与四渠道模板；运行 FR-003/004/005。

## Phase 5: US3 版本审批

- [ ] T007 [US3] 在 `assets/day1024_sol_v1_v2/index.html` 实现双审/退回/品牌/DRI、修改失效与口径快照；运行 FR-006/007/008。

## Phase 6: US4 反馈与交付

- [ ] T008 [US4] 在 `assets/day1024_sol_v1_v2/index.html` 实现反馈采纳、持久化、导出、存储错误；运行 FR-009/010/011。

## Phase 7: Polish

- [ ] T009 在 `assets/day1024_sol_v1_v2/verify_demo.py` 实现截图与完整 UI 走查，查看桌面/窄屏截图并修正。
- [ ] T010 在 `assets/day1024_sol_v1_v2/validation.md` 记录真实红绿结果、全闸退出码、来源边界与未做事项。

## Scope correction: 企业任务1/2先行

- [ ] T011 [US5] 在 `tests/test_day1024_sol_business.py` 写 FR-012–015 并确认失败，再补资料输入、标注、职责确认、版本依赖失效。
- [ ] T012 [US6] 在 `tests/test_day1024_sol_business.py` 写 FR-016–019 并确认失败，再补规则建议、反例拒绝、人工确认与 DRI 交接。
- [ ] T013 在 `assets/day1024_sol_v1_v2/verify_demo.py` 加入新增资料到选题的真实 UI 验证及截图。

T011→T012→T013→T009→T010；原审批流作为后续交接，不代替企业前两条业务任务。

## Dependencies & Parallel Execution

T001→T002→T003→T004→T005→T006→T007→T008→T009→T010。

并行仅用于只读事实调研与角色流程批评，均不写工作树；所有 HTML 编辑串行。MVP 是 US1，但最终交付必须包含 US2–US4 的单条纵切闭环。
