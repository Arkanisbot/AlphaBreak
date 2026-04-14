<#
.SYNOPSIS
    Deploy the SEO routes (programmatic ticker pages + comparison pages +
    sitemap + robots.txt) to the AlphaBreak EC2 production box.

.DESCRIPTION
    Thin SSH wrapper. The actual deploy logic lives in
    scripts/deploy-seo-routes.sh (version-controlled, LF-only, runnable
    standalone on the box). This script just:

      1. Discovers the SSH key
      2. git-pulls on the remote so the latest .sh is present
      3. Invokes the .sh script via bash

    Idempotent. Safe to re-run on every code change.

.PARAMETER PemPath
    Path to the SSH private key (.pem file).
    Auto-discovered from $HOME\.ssh\*.pem if not specified.

.PARAMETER RemoteHost
    EC2 hostname or IP. Default: alphabreak.vip

.PARAMETER RemoteUser
    SSH user. Default: ubuntu

.EXAMPLE
    .\deploy-seo-routes.ps1

.EXAMPLE
    .\deploy-seo-routes.ps1 -PemPath "C:\Users\nicho\.ssh\trading-db-key.pem"
#>

param(
    [string]$PemPath,
    [string]$RemoteHost = "alphabreak.vip",
    [string]$RemoteUser = "ubuntu"
)

$ErrorActionPreference = "Stop"

# ---- Discover the SSH key --------------------------------------------------
if (-not $PemPath) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $candidates = @(
        "$HOME\.ssh\trading-db-key.pem",
        "$HOME\.ssh\alphabreak.pem",
        "C:\.ssh\trading-db-key.pem",
        (Join-Path $scriptDir "docs\security\trading-db-key.pem")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $PemPath = $c; break }
    }
    if (-not $PemPath -and (Test-Path "$HOME\.ssh")) {
        $found = Get-ChildItem "$HOME\.ssh\*.pem" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $PemPath = $found.FullName }
    }
}

if (-not $PemPath -or -not (Test-Path $PemPath)) {
    Write-Host ""
    Write-Host "ERROR: SSH key not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Searched:" -ForegroundColor Yellow
    Write-Host "  $HOME\.ssh\*.pem"
    Write-Host "  C:\.ssh\*.pem"
    Write-Host "  docs\security\trading-db-key.pem"
    Write-Host ""
    Write-Host "Run with an explicit path:" -ForegroundColor Yellow
    Write-Host "  .\deploy-seo-routes.ps1 -PemPath `"C:\Users\nicho\.ssh\your-key.pem`""
    exit 1
}

try {
    $null = Get-Command ssh.exe -ErrorAction Stop
} catch {
    Write-Host ""
    Write-Host "ERROR: ssh.exe not found in PATH." -ForegroundColor Red
    Write-Host "Install the Windows OpenSSH client via:" -ForegroundColor Yellow
    Write-Host "  Settings > Apps > Optional Features > Add > OpenSSH Client" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "== AlphaBreak SEO Routes Deploy ==" -ForegroundColor Cyan
Write-Host ("  Key:  {0}" -f $PemPath)
Write-Host ("  Host: {0}@{1}" -f $RemoteUser, $RemoteHost)
Write-Host ""
Write-Host "Running remote deploy script..." -ForegroundColor Cyan
Write-Host ""

# Single ssh command: pull, then invoke the committed .sh file.
# Git's .gitattributes enforces LF endings on .sh files so bash won't choke
# on stray \r characters (the bug that broke the inline-heredoc version).
$remoteCmd = "set -e; cd `$HOME/AlphaBreak && git fetch --all && git pull --ff-only && bash scripts/deploy-seo-routes.sh"

& ssh.exe `
    -i $PemPath `
    -o "StrictHostKeyChecking=accept-new" `
    -o "ServerAliveInterval=30" `
    "${RemoteUser}@${RemoteHost}" `
    $remoteCmd

$sshExit = $LASTEXITCODE

Write-Host ""
if ($sshExit -eq 0) {
    Write-Host "== Deploy complete ==" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Browser-verify a couple of URLs:"
    Write-Host "       https://alphabreak.vip/stocks/AAPL"
    Write-Host "       https://alphabreak.vip/compare/tradingview"
    Write-Host "  2. Submit the sitemap to Google Search Console:"
    Write-Host "       https://search.google.com/search-console  ->  Sitemaps  ->  Add"
    Write-Host "       https://alphabreak.vip/sitemap.xml"
    Write-Host "  3. Use 'URL Inspection' to request immediate indexing on 5-10 ticker pages."
} else {
    Write-Host "== Deploy failed (exit code $sshExit) ==" -ForegroundColor Red
    Write-Host ""
    Write-Host "Debug:" -ForegroundColor Yellow
    Write-Host "  ssh -i `"$PemPath`" ${RemoteUser}@${RemoteHost}"
    Write-Host "  cd ~/AlphaBreak && bash -x scripts/deploy-seo-routes.sh"
    Write-Host ""
    Write-Host "Rollback (if nginx broke):" -ForegroundColor Yellow
    Write-Host "  On the box, find the latest backup:"
    Write-Host "    sudo ls -lt /etc/nginx/sites-available/*.bak.* 2>/dev/null | head -3"
    Write-Host "    sudo ls -lt /etc/nginx/conf.d/*.bak.* 2>/dev/null | head -3"
    Write-Host "  Then restore it:"
    Write-Host "    sudo cp /path/to/file.bak.<timestamp> /path/to/file"
    Write-Host "    sudo nginx -t && sudo systemctl reload nginx"
    exit $sshExit
}
