# 本地 issue

远程 GitHub 仓**还没建**（本仓是离线优先的：`gh` 已登录但没建远程）。

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

## 将来建了远程怎么办

```powershell
gh repo create FDE训练营 --private --source . --push
```

建完之后，本目录的文件可以：

- 直接用 `gh issue create --title ... --body-file issues/feature-001-xxx.md` 迁过去；
- 或继续留在仓内当"议题档案"，GitHub issue 只做跟踪。

**目录结构和字段是照着 `.github/ISSUE_TEMPLATE/` 写的**，所以迁移是逐字搬运，不用重写。
