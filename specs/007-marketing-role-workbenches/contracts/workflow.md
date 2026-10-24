# UI and Command Contract

## Role matrix

| role | 首页 | 可写操作 | 不可做 |
|---|---|---|---|
| dri | 项目驾驶舱 | 排期、分派职能负责人、放行、采纳反馈 | 专业审核、改正文 |
| sales | 客户问题台 | 新问题、发布后反馈 | 排期、审核、放行 |
| content | 内容制作台 | 渠道模板、编辑/保存、提交审查 | 给自己签字、发布 |
| tech | 技术审核台 | 技术通过/退回 | 项目、品牌签字 |
| project | 项目核验台 | 项目通过/退回 | 技术、品牌签字 |
| brand | 品牌确认台 | 双审后品牌通过/退回 | 跳过双审、代 DRI 放行 |

共享只读：来源素材、已批准口径。每个角色只有一组主要导航；详细稿件以抽屉展示。

## Commands

`Demo.command(action, payload)` 返回 `{ok, message}`；未经授权或非法状态返回 ok=false 且项目实体不变。用于 UI 与反例自动化；不是安全 API。

- addQuestion({ask,audience,sourceIds}) sales
- planQuestion({questionId,week}) dri（内容负责人固定为 content 枚举）
- assign({topicId,week}) dri
- generate({topicId,channel}) content
- saveDraft({topicId,body,notes}) content
- submit({topicId}) content
- approve({topicId,decision,reason}) tech/project/brand（当前身份确定签字类型）
- release({topicId}) dri
- addFeedback({topicId,signal,question}) sales
- adoptFeedback({feedbackId}) dri
- reuseClaim({claimId,topicId}) content（历史签字不复制，新稿重新审批）

## Test seams and export

- `Demo.snapshot()`：JSON 副本，ready、role、questions、topics、claims、feedback、audit；只读返回，不暴露原 state 引用。
- `Demo.login(role)`：演示身份切换，拒绝非法枚举。
- `Demo.exportText()`：当前时间、模拟声明、topic/question/source/版本/签字/反馈/日志 Markdown；业务数字来自 state。
- `Demo.reset()`：仅在明确确认的本地重置弹窗中使用，不清理其他 key。
- 所有用户字符串用 textContent 或 HTML 转义；外链只接受 http(s)，target=_blank 加 rel=noopener noreferrer。
