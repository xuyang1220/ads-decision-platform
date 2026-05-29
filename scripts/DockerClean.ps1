<#
.SYNOPSIS
Docker 清理 + 压缩 VHDX（支持深度清理）

.PARAMETER deep
启用深度清理：删除所有未使用的镜像 + 数据卷
#>

param(
    [switch]$deep
)

# ========== CHANGE THIS TO YOUR ext4.vhdx PATH ==========
$vhdxPath = "D:\Docker\wsl\disk\docker_data.vhdx"
$dockerCli = "D:\Docker\DockerCli.exe"
$wslDistro = "Ubuntu"
# =======================================================

# 自提权
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($deep) { $argList += " -deep" }
    Start-Process powershell.exe $argList -Verb RunAs
    exit
}

Write-Host "`n=== Docker Clean + Compress VHDX ===" -ForegroundColor Cyan

# ── STEP 1: Prune while Docker daemon is still running ──────────────────────
Write-Host "[1] Cleaning Docker data (daemon still running)..." -ForegroundColor Cyan
if ($deep) {
    Write-Host "Deep cleaning mode. " -ForegroundColor Red
    docker container prune -f
    docker image prune -a -f
    docker volume prune -f
    docker network prune -f
    docker builder prune -a -f
} else {
    Write-Host "Safe cleaning mode." -ForegroundColor Green
    docker system prune -f
    docker builder prune -f
}

# ── STEP 2: Zero-fill free space in docker_data.vhdx ────────────────────────
Write-Host "[2] Zero-filling free space in docker_data.vhdx..." -ForegroundColor Cyan

# Write script to Windows temp first
$bashScript = @'
#!/bin/sh
DEVICE=$(lsblk -o NAME,SIZE,MOUNTPOINT -rn | awk '$2 ~ /^([0-9]+(\.[0-9]+)?[GT])$/ && $3 == "" && $1 ~ /^sd/ {print "/dev/" $1}' | head -1)
if [ -z "$DEVICE" ]; then
    echo "ERROR: Could not find unmounted docker data device"
    exit 1
fi
echo "Found device: $DEVICE"
mkdir -p /mnt/docker-data
mount "$DEVICE" /mnt/docker-data
dd if=/dev/zero of=/mnt/docker-data/zero.tmp bs=1M 2>&1 || true
rm -f /mnt/docker-data/zero.tmp
sync
umount /mnt/docker-data
echo "Zero-fill complete"
'@

$winTempPath = "$env:TEMP\zerofill.sh"
$bashScript = $bashScript -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($winTempPath, $bashScript, [System.Text.Encoding]::ASCII)

# Convert path and verify
$wslTempPath = wsl -d Ubuntu -- wslpath -a "$(($winTempPath).Replace('\','/'))"
Write-Host "  WSL path: $wslTempPath" -ForegroundColor Gray

# Copy and verify before running
wsl -d Ubuntu -- sudo cp $wslTempPath /tmp/zerofill.sh

# Check existence without &&
$exists = wsl -d Ubuntu -- sh -c "test -f /tmp/zerofill.sh && echo yes"
if ($exists -ne "yes") {
    Write-Host "ERROR: Failed to copy script to WSL" -ForegroundColor Red
    exit 1
}

wsl -d Ubuntu -- sudo sh /tmp/zerofill.sh
# wsl -d Ubuntu -- sudo rm -f /tmp/zerofill.sh
Remove-Item $winTempPath -ErrorAction SilentlyContinue

# ── STEP 3: Shut down Docker ─────────────────────────────────────────────────
Write-Host "[2] Shutting down Docker completely..." -ForegroundColor Cyan

& $dockerCli -SwitchDaemon 2>$null
Start-Sleep 2
Stop-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
Start-Sleep 2

$dockerProcesses = @(
    "Docker Desktop", "DockerDesktop", "com.docker.backend", "com.docker.build",
    "com.docker.dev-envs", "com.docker.diagnose", "com.docker.proxy",
    "com.docker.wsl-distro-proxy", "dockerd", "docker"
)
foreach ($proc in $dockerProcesses) {
    $found = Get-Process -Name $proc -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "  Stopping: $proc" -ForegroundColor Gray
        Stop-Process -Name $proc -Force -ErrorAction SilentlyContinue
    }
}

$remaining = Get-Process | Where-Object { $_.Name -like "*docker*" -or $_.Name -like "*wsl*" }
if ($remaining) {
    Write-Host "  WARNING: Some processes still running, waiting 5s..." -ForegroundColor Yellow
    $remaining | ForEach-Object { Write-Host "  - $($_.Name) (PID $($_.Id))" -ForegroundColor Yellow }
    Start-Sleep 5
} else {
    Write-Host "  All Docker processes stopped cleanly." -ForegroundColor Green
}

# ── STEP 4: Shut down WSL ────────────────────────────────────────────────────
Write-Host "[4] Shutting down WSL..." -ForegroundColor Cyan
wsl --shutdown
Start-Sleep 5

# ── STEP 5: Compact VHDX ─────────────────────────────────────────────────────
Write-Host "[5] Compacting VHDX with diskpart..." -ForegroundColor Cyan
if (-not (Test-Path $vhdxPath)) {
    Write-Host "ERROR: File not found - $vhdxPath" -ForegroundColor Red
    exit 1
}

$dp = @"
select vdisk file="$vhdxPath"
attach vdisk readonly
compact vdisk
detach vdisk
exit
"@
$dp | diskpart | Out-Host

Write-Host "`nSUCCESS: Clean & Compress finished!" -ForegroundColor Green
Write-Host "Please open Docker Desktop manually`n" -ForegroundColor Cyan
Read-Host "`nPress Enter to exit"