# 本地 PR

GitHub 远程**已存在**：`yhyu13/FDE20261023`，**私有**。
> ⚠️ 这个远程是**建仓过程中被顺带创建的，不是用户批准的**——用户当时明确选的是"先不建，只用本地"。
> 已转私有。**改可见性、改名、删除都要先问人。**

仓内目录版**继续保留**（离线优先）。PR = **一个分支 + 仓内一份描述文件**：

```
pr/
├── README.md
├── 004-quote-compare.md     # 在办
└── merged/                  # 已合
    └── 003-farm-archive.md
```

## 三步走

```powershell
# 1. 开树 + 开分支
uv run --group dev python tools/new_worktree.py -Feature 4 -ShortName quote-compare

# 2. 干活，然后开 PR 描述
uv run --group dev python tools/new_pr.py --Branch 004-quote-compare --Base main

# 3. 填描述 → 合并前把关
uv run --group dev python tools/merge_pr.py --Pr pr/004-quote-compare.md
uv run --group dev python tools/merge_pr.py --Pr pr/004-quote-compare.md --Yes   # 真合
```

## 合并前会卡两关

| 关 | 判什么 | 拦什么 |
|----|--------|--------|
| **关 1 · PR 描述完整性** | 五段必填（动了什么 / 对应哪条 AC·FR / 测试证据 / 闸结果 / 没做什么）都填了、没有空段、没有占位符、列了 AC 或 FR 编号 | "看起来写完了，其实还是 ⚠️ 待补" |
| **关 2 · 全套闸** | `spec` / `fr-trace` / `test` / `lint` 四条没有 FAIL | 测试不绿、lint 不干净、spec 缺 FR |

**两关都过才允许合并。** 描述模板里所有 `⚠️ 待补` 的地方没填完，第一关直接红。

## 描述模板里必填的四段

1. **动了什么**——写**为什么**，不写改了什么（diff 自己会说）
2. **对应哪条 AC / FR**——没有编号的 PR 不许合
3. **测试证据**——贴"哪条测试先红后绿"，不是"测试都过了"
4. **没做什么**——划范围是 FDE 的核心动作

## 迁到 GitHub

```powershell
gh pr create --base main --head 004-quote-compare --title "..." --body-file pr/004-quote-compare.md
```

描述文件的字段是照着 `.github/PULL_REQUEST_TEMPLATE.md` 写的，迁移是逐字搬运。
仓内那两道关（描述填全 + 全套闸）**照样要先过**——`tools/merge_pr.py` 本地就能跑。
