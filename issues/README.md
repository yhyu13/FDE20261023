# 本地 issue

GitHub 远程**已存在**：`yhyu13/FDE20261023`，**公开**（`gh` 已登录）。
> ✅ 这个远程**已获用户批准**：2026-10-23 用户明确要求上传到该仓，并选择保持公开。
> **改可见性、改名、删除都要先问人。**

仓内这个目录**继续保留**——本仓是离线优先的，断网也能把流程走完。
所以 issue 落在仓内这个目录里，一张 issue 一个 Markdown 文件：

```
issues/
├── README.md
├── feature-001-xxx.md      # 功能 / 需求
├── bug-001-xxx.md          # 缺陷
└── ...
```

## 怎么开一张

```powershell
uv run --group dev python tools/new_issue.py --Kind feature --Title "报价归集管线" --Slug quote-pipeline
uv run --group dev python tools/new_issue.py --Kind bug --Title "台账合计与分项和对不上" --Slug sum-mismatch
```

生成的文件里有 `⚠️ 待补` 的地方**必须填完**。issue 的内容会直接变成 spec 的输入。

## 迁到 GitHub

远程已在 `yhyu13/FDE20261023`，仓内文件可以直接搬过去：

```powershell
gh issue create --title "..." --body-file issues/feature-001-xxx.md
```

也可以继续留在仓内当"议题档案"，GitHub issue 只做跟踪。

**目录结构和字段是照着 `.github/ISSUE_TEMPLATE/` 写的**，所以迁移是逐字搬运，不用重写。
