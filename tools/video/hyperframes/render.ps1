<#
.SYNOPSIS
    在本机用 HyperFrames 渲染一支讲解片（默认走 Microsoft Edge）。

.DESCRIPTION
    封装四件事，顺序固定：
      1. 确认浏览器与 ffmpeg 就位（浏览器用 Edge，路径写进 HYPERFRAMES_BROWSER_PATH）
      2. 跑 hyperframes check，error 不清零就不往下走
      3. 跑 hyperframes render
      4. 用 ffprobe 核对成片时长、分辨率，跟 composition 根节点声明的 data-duration 对齐

    为什么要用 Edge：常规浏览器构建没有 HeadlessExperimental.beginFrame，
    引擎会退到截图采集路径（慢一些，但结果一样确定）。
    换 chrome-headless-shell 才走 beginFrame 快速路径。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools/video/hyperframes/render.ps1 `
        -ProjectDir tools/video/hyperframes/template -Output renders/demo.mp4
#>
[CmdletBinding()]
param(
    [string]$ProjectDir = "tools/video/hyperframes/template",
    [string]$Output = "renders/out.mp4",
    [ValidateSet("draft", "looks", "delivery")]
    [string]$Quality = "looks",
    [switch]$SkipCheck
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$project = if ([System.IO.Path]::IsPathRooted($ProjectDir)) { $ProjectDir } else { Join-Path $repo $ProjectDir }
$output = if ([System.IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $repo $Output }

function Fail($msg) { Write-Error $msg; exit 1 }

if (-not (Test-Path (Join-Path $project "index.html"))) { Fail "找不到 $project\index.html，先用 template 复制一份再改。" }

# 1. 浏览器
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edge)) { Fail "找不到 Microsoft Edge：$edge" }
$env:HYPERFRAMES_BROWSER_PATH = $edge
Write-Host "[1/4] 浏览器：$edge"

# 2. ffmpeg / ffprobe
$ffprobe = (Get-Command ffprobe -ErrorAction SilentlyContinue).Source
if (-not $ffprobe) { Fail "找不到 ffprobe，装 ffmpeg 或设 HYPERFRAMES_FFPROBE_PATH。" }
Write-Host "[1/4] ffprobe：$ffprobe"

# 3. check
if (-not $SkipCheck) {
    Write-Host "[2/4] hyperframes check ..."
    Push-Location $project
    try { & npx.cmd -y hyperframes@latest check --json | Out-File -Encoding utf8 "$project\.check.json" } finally { Pop-Location }
    $check = Get-Content "$project\.check.json" -Raw | ConvertFrom-Json
    $errors = 0
    foreach ($section in $check.PSObject.Properties) {
        $v = $section.Value
        if ($v -is [pscustomobject] -and $null -ne $v.errorCount) { $errors += [int]$v.errorCount }
    }
    if ($errors -gt 0) { Fail "check 报了 $errors 个 error，先修干净再渲。报告：$project\.check.json" }
    Write-Host "[2/4] check 通过。"
}

# 4. render
$outDir = Split-Path -Parent $output
if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
Write-Host "[3/4] hyperframes render（quality=$Quality）..."
Push-Location $project
try {
    & npx.cmd -y hyperframes@latest render --quality $Quality --output $output
    if ($LASTEXITCODE -ne 0) { Fail "render 失败，退出码 $LASTEXITCODE。" }
} finally { Pop-Location }

# 5. 核对
Write-Host "[4/4] ffprobe 核对..."
$html = Get-Content (Join-Path $project "index.html") -Raw
$m = [regex]::Match($html, 'data-duration="([\d\.]+)"')
$expected = if ($m.Success) { [double]$m.Groups[1].Value } else { $null }
$probe = & $ffprobe -v error -show_entries format=duration -show_entries stream=width,height,nb_frames -of json $output | ConvertFrom-Json
$actual = [double]$probe.format.duration
$stream = $probe.streams[0]
Write-Host ("      时长 {0}s（composition 声明 {1}s）· {2}x{3} · {4} 帧 · {5:N0} 字节" -f `
    $actual, $expected, $stream.width, $stream.height, $stream.nb_frames, (Get-Item $output).Length)

if ($expected -and [Math]::Abs($actual - $expected) -gt 0.05) {
    Fail "成片时长 $actual s 与 composition 的 data-duration $expected s 对不上，别直接交。"
}
if ($stream.width -ne 1920 -or $stream.height -ne 1080) {
    Fail "分辨率是 $($stream.width)x$($stream.height)，不是 1920x1080。"
}
Write-Host "完成：$output"

