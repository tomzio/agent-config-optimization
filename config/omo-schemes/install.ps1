<# 
.SYNOPSIS
    OpenCode/OmO 多模型路由配置一键安装脚本 (Windows PowerShell)
    支持 Windows 10/11 PowerShell 5.1+ / PowerShell 7+

.USAGE
    irm https://raw.githubusercontent.com/tomzio/agent-config-optimization/main/config/omo-schemes/install.ps1 | iex
#>

param(
    [string]$Repo = "tomzio/agent-config-optimization",
    [string]$Branch = "main",
    [string]$SchemesDir = "config/omo-schemes"
)

$ErrorActionPreference = "Stop"

# 颜色函数
function Write-Info { param([string]$msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Success { param([string]$msg) Write-Host "[SUCCESS] $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Error { param([string]$msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }

# 检查依赖
function Check-Deps {
    $missing = @()
    foreach ($cmd in @("curl", "python3", "git")) {
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
            $missing += $cmd
        }
    }
    if ($missing.Count -gt 0) {
        Write-Error "缺少依赖: $($missing -join ', ')"
        Write-Info "请先安装: $($missing -join ', ')"
        exit 1
    }
}

# 下载方案文件
function Download-Schemes {
    Write-Info "下载配置方案..."
    $baseUrl = "https://raw.githubusercontent.com/$Repo/$Branch/$SchemesDir"
    $files = @(
        "scheme1-free-first.jsonc",
        "scheme2-plan-first.jsonc",
        "scheme3-free-only.jsonc",
        "switch.py",
        "switch.bat",
        "test_switch.py",
        "validate_config.py",
        "quota-fallback-wrapper.js",
        "preflight-checker.py",
        "proxy-config.example.json",
        "README.md"
    )

    $installDir = "$env:USERPROFILE\.config\opencode\omo-schemes"
    if (-not (Test-Path $installDir)) {
        New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    }

    foreach ($file in $files) {
        Write-Info "下载: $file"
        $url = "$baseUrl/$file"
        $outPath = Join-Path $installDir $file
        try {
            Invoke-WebRequest -Uri $url -OutFile $outPath -UseBasicParsing
        } catch {
            Write-Error "下载失败: $file - $_"
            exit 1
        }
    }
    Write-Success "方案文件下载完成: $installDir"
    return $installDir
}

# 显示菜单
function Show-Menu {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  OpenCode/OmO 模型路由配置方案选择" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1) Scheme 1: 免费优先" -ForegroundColor White
    Write-Host "     免费(opencode) → coding-plan 套餐 → zhipuai GLM → deepseek(末位)" -ForegroundColor Gray
    Write-Host "     适用: 套餐额度紧张、想最大化免费模型、或免费模型网络更好" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2) Scheme 2: 套餐优先 + Provider 隔离 (推荐)" -ForegroundColor White
    Write-Host "     coding-plan(Ark独占) → deepseek官方(独立配额) → 免费 → zhipuai → deepseek(末位)" -ForegroundColor Gray
    Write-Host "     适用: 套餐充足、追求稳定、deepseek独立配额避免套餐耗尽影响" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  3) Scheme 3: 纯免费 (零成本)" -ForegroundColor White
    Write-Host "     仅用 opencode 免费模型，套餐/按量全不用" -ForegroundColor Gray
    Write-Host "     适用: 拒绝任何按量调用、压测免费上限、临时额度用尽" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  4) 仅下载文件，不切换配置" -ForegroundColor White
    Write-Host ""
    Write-Host "  q) 退出" -ForegroundColor White
    Write-Host ""
}

# 切换方案
function Switch-Scheme {
    param([string]$SchemeId, [string]$InstallDir)
    Write-Info "切换到方案 $SchemeId..."
    
    # 切换前进行配置格式验证
    if (-not (Validate-Config -SchemeId $SchemeId -InstallDir $InstallDir)) {
        Write-Error "配置格式验证失败，取消切换"
        return $false
    }
    
    python3 "$InstallDir/switch.py" switch $SchemeId
}

# 配置格式验证 - 调用独立验证脚本
function Validate-Config {
    param([string]$SchemeId, [string]$InstallDir)

    $slug = switch ($SchemeId) {
        '1' { 'free-first' }
        '2' { 'plan-first' }
        '3' { 'free-only' }
        default { $null }
    }
    if ($null -eq $slug) {
        Write-Error "未知方案 ID: $SchemeId"
        return $false
    }
    $schemeFile = "$InstallDir\scheme${SchemeId}-${slug}.jsonc"

    Write-Info "验证配置格式: $schemeFile"

    $result = python3 "$InstallDir\validate_config.py" $schemeFile
    if ($LASTEXITCODE -eq 0) {
        Write-Success "配置格式验证通过"
        return $true
    } else {
        Write-Error "配置格式验证失败"
        return $false
    }
}

# 验证安装
function Verify-Install {
    param([string]$InstallDir)
    Write-Info "验证安装..."
    python3 "$InstallDir/test_switch.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "测试失败，请检查安装"
        exit 1
    }
    Write-Success "安装验证通过"
}

# 主流程
Write-Host ""
Write-Info "OpenCode/OmO 多模型路由配置安装器"
Write-Info "仓库: https://github.com/$Repo"
Write-Host ""

Check-Deps
$installDir = Download-Schemes

# 创建 omo 目录
$omoDir = "$env:USERPROFILE\.omo"
if (-not (Test-Path "$omoDir\backups")) {
    New-Item -ItemType Directory -Path "$omoDir\backups" -Force | Out-Null
}

Verify-Install -InstallDir $installDir

# 交互式选择
# 兼容 irm | iex 场景：检测 stdin 是否被重定向，是则降级为「仅下载模式」
while ($true) {
    Show-Menu
    if ([Console]::IsInputRedirected) {
        Write-Warn "未检测到交互终端（irm | iex 场景）"
        Write-Info "已下载文件到: $installDir"
        Write-Info "请在 PowerShell 中重新运行安装以选择方案："
        Write-Info "  & $installDir\install.ps1"
        Write-Info "或手动切换: python3 $installDir\switch.py switch <1|2|3>"
        break
    }
    $choice = Read-Host "请选择方案 [1/2/3/4/q]"
    switch ($choice) {
        "1" { Switch-Scheme -SchemeId "1" -InstallDir $installDir; break }
        "2" { Switch-Scheme -SchemeId "2" -InstallDir $installDir; break }
        "3" { Switch-Scheme -SchemeId "3" -InstallDir $installDir; break }
        "4" {
            Write-Info "已下载文件到: $installDir"
            Write-Info "稍后可手动运行: python3 $installDir\switch.py switch <1|2|3>"
            break
        }
        "q" { Write-Info "已取消"; exit 0 }
        "Q" { Write-Info "已取消"; exit 0 }
        default { Write-Warn "无效选择，请重新输入" }
    }
}

Write-Host ""
Write-Success "安装完成！"
Write-Host ""
Write-Host "后续操作:"
Write-Host "  1. 重启 OpenCode 使配置生效"
Write-Host "  2. 验证: 在 OpenCode 中运行 /model 查看模型列表"
Write-Host "  3. 切换方案: python3 $installDir\switch.py switch <1|2|3>"
Write-Host "  4. 查看文档: $installDir\README.md"
Write-Host ""