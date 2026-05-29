<#
.SYNOPSIS
Docker 清理 + 压缩 VHDX（支持深度清理）

.PARAMETER deep
启用深度清理：删除所有未使用的镜像 + 数据卷
#>

param(
    [switch]$deep
)

# ========== CHANGE THIS TO YOUR vhdx PATH ==========
$vhdxPath = "D:\Docker\wsl\disk\docker_data.vhdx"
# =======================================================

# 自提权：如果不是管理员，自动新开管理员窗口运行
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "`n=== Docker Clean + Compress VHDX (Diskpart) ===" -ForegroundColor Cyan

Write-Host "[1] Shutting down Docker completely..." -ForegroundColor Cyan

# 1. Graceful shutdown via CLI first
& "D:\Docker\DockerCli.exe" -SwitchDaemon 2>$null
Start-Sleep 2

# 2. Stop Docker Desktop service gracefully
Stop-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
Start-Sleep 2

# 3. Kill all Docker-related processes (order matters)
$dockerProcesses = @(
    "Docker Desktop",
    "DockerDesktop",
    "com.docker.backend",
    "com.docker.build",
    "com.docker.dev-envs",
    "com.docker.diagnose",
    "com.docker.proxy",
    "com.docker.wsl-distro-proxy",
    "dockerd",
    "docker"
)

foreach ($proc in $dockerProcesses) {
    $found = Get-Process -Name $proc -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "  Stopping: $proc" -ForegroundColor Gray
        Stop-Process -Name $proc -Force -ErrorAction SilentlyContinue
    }
}

# 4. Verify nothing Docker-related is still running
$remaining = Get-Process | Where-Object { $_.Name -like "*docker*" -or $_.Name -like "*wsl*" }
if ($remaining) {
    Write-Host "WARNING: Some processes still running:" -ForegroundColor Yellow
    $remaining | ForEach-Object { Write-Host "  - $($_.Name) (PID $($_.Id))" -ForegroundColor Yellow }
    Write-Host "Waiting 5 more seconds..." -ForegroundColor Yellow
    Start-Sleep 5
    Stop-Process -Name { $_.Name -like "*docker*" } -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "  All Docker processes stopped cleanly." -ForegroundColor Green
}

# After Docker is fully shut down and before wsl --shutdown:

# 1. Run all prune commands while daemon is still accessible
Write-Host "[2] Deep cleaning Docker data..." -ForegroundColor Cyan
if ($deep) {
    Write-Host "[2-1] 深度清理模式：删除所有未使用镜像、容器、卷、缓存" -ForegroundColor Red
    docker container prune -f
    docker image prune -a -f
    docker volume prune -f
    docker network prune -f
    docker builder prune -a -f
}
else {
    Write-Host "[2-1] 安全清理模式：仅清理无用容器、悬空镜像、缓存" -ForegroundColor Green
    docker system prune -f
    docker builder prune -f
}

# 2. Zero-fill free space inside the ext4 filesystem (THIS is the key step)
Write-Host "[2-2] Zero-filling free space in docker_data.vhdx..." -ForegroundColor Cyan

$script = @"
DEVICE=`$(lsblk -o NAME,SIZE,MOUNTPOINT -rn | awk '`$2 ~ /^([0-9]+(\.[0-9]+)?[GT])`$/ && `$3 == "" && `$1 ~ /^sd/ {print "/dev/" `$1}' | head -1)
if [ -z "`$DEVICE" ]; then
    echo "ERROR: Could not find unmounted docker data device"
    exit 1
fi
echo "Found device: `$DEVICE"
mkdir -p /mnt/docker-data
mount "`$DEVICE" /mnt/docker-data
dd if=/dev/zero of=/mnt/docker-data/zero.tmp bs=1M 2>&1 || true
rm -f /mnt/docker-data/zero.tmp
sync
umount /mnt/docker-data
echo "Zero-fill complete"
"@

# Write script to a temp file in WSL and execute it
$script | wsl -d Ubuntu -- sudo tee /tmp/zerofill.sh | Out-Null
wsl -d Ubuntu -- sudo sh /tmp/zerofill.sh
wsl -d Ubuntu -- sudo rm -f /tmp/zerofill.sh

# 3. NOW shut down WSL
Write-Host "[2-3] Shutting down WSL..." -ForegroundColor Cyan
wsl --shutdown
Start-Sleep 5

# 4. Compact with diskpart (zeros created above make this effective)
Write-Host "[2-4] Compressing virtual disk with diskpart..." -ForegroundColor Cyan
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