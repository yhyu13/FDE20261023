# Quickstart

1. 双击 `assets/day1024_sol_v1_v2/index.html`，选择身份进入（不是安全登录）。
2. 内容运营打开 T01，生成任一渠道模板并提交。
3. 技术审核与项目审核各确认 T01；品牌确认后 DRI 才能模拟放行。
4. 销售对 T01 录入结构化模拟反馈，DRI 采纳到下一轮。
5. 再编辑 T01，检查旧审核全部失效；缺证据 T03 不可提交。
6. 导出项目记录；刷新检查保存；重置只清本演示的数据。

自动验收：`uv run --group dev --with playwright python -m pytest tests/test_day1024_sol_roles.py -v`

全闸：`uv run --group dev --with playwright python tools/run_all_gates.py`

截图/浏览器补充验证：`python assets/day1024_sol_v1_v2/verify_demo.py`

本地运行不需要 Python，测试需要 Python Playwright 与 Chromium。浏览器证据不代表真实鉴权、真实模型生成或企业发布能力。
