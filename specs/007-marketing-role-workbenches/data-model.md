# Data Model

## Enumerations

- role = dri | sales | content | tech | project | brand
- audience = 公交运营商 | 海外客户 | 行业伙伴
- channel = 公众号 | 官网 | 展会 | 销售推介
- stage = draft | review | changes | brand | ready | released
- decision = approve | return
- usage = reference | cleared（演示素材授权，不代表真实企业许可）

## Entities

- Source: id/title/publisher/date/url/location/maturity/audience/fact/boundary/verified。允许公开资料卡原件未复核，但不得冒充联网核实。
- Picture: id/title/data URI/local path/source/usage/boundary。
- Question: id/ask/audience/sourceIds/feedbackId；ask 长度 4–240，不执行其内容。
- Topic: id/questionId/title/audience/week/channel/sourceIds/pictureId/gaps；id 唯一。
- Revision: topicId/version/body/notes/stage/approvals/releasedVersion；审批只绑定当前版本。
- Approval: role/version/decision/reason/time。
- Claim: topicId/version/text/sourceIds/maturity/scope/time；历史快照不可被改稿覆写；旧版本标历史不可直接放行。
- Feedback: id/topicId/version/signal/question/adopted；signal 选枚举，question 是不驱动状态的备注。
- AuditEvent: sequence/time/role/topicId/version/action；仅本地演示日志，可被用户修改，不称不可篡改。

## Invariants

1. 每条 question 和 topic 只引用存在的 source；无 source 只能进入资料征集，不能 submit。
2. 每次实质改稿 version += 1，approvals 清空，releasedVersion 清空，stage=draft。
3. review 阶段技术/项目各签自己的版本；两者 approve 后 stage=brand。
4. brand approve 才 stage=ready；DRI 只能 ready→released，不替代专业签字。
5. 退回必须有原因，stage=changes；重复操作不增加实体。
6. 反馈只能引用 released 当前版本；adopt 只能一次，生成新 question 而非改写旧事实。
