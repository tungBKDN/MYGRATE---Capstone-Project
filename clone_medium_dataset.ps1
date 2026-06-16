$yamlPath = Join-Path $PSScriptRoot "medium_dataset.yaml"
$dest = Join-Path $PSScriptRoot "freshbrew_data"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

if (-not (Test-Path $yamlPath)) {
    Write-Error "medium_dataset.yaml not found!"
    exit 1
}

$content = Get-Content -Raw -Path $yamlPath
# Split by "- commit:" to get each repo block
$blocks = $content -split "(?ms)^-\s+commit:\s*"

$repos = @()
foreach ($block in $blocks) {
    if ([string]::IsNullOrWhiteSpace($block)) { continue }
    
    $commit = $null
    $repoName = $null
    
    # Extract commit
    if ($block -match "^([a-f0-9]+)") {
        $commit = $Matches[1]
    }
    
    # Extract repo_name
    if ($block -match "repo_name:\s*(\S+)") {
        $repoName = $Matches[1]
    }
    
    if ($commit -and $repoName) {
        $repos += [PSCustomObject]@{
            name = $repoName
            commit = $commit
        }
    }
}

$total = $repos.Count
Write-Host "Found $total repositories to clone."

$i = 0
foreach ($r in $repos) {
    $i++
    $folder = $r.name.Split('/')[-1]
    $target  = Join-Path $dest $folder
    Write-Host "`n[$i/$total] $($r.name)" -ForegroundColor Cyan

    if (Test-Path (Join-Path $target '.git')) {
        Write-Host "  [SKIP] Already cloned." -ForegroundColor Yellow
        continue
    }

    git clone --quiet "https://github.com/$($r.name).git" $target 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [FAIL] Clone failed." -ForegroundColor Red
        continue
    }

    Push-Location $target
    git checkout --quiet $r.commit 2>&1
    $co = $LASTEXITCODE
    Pop-Location

    if ($co -eq 0) {
        Write-Host "  [OK] @ $($r.commit.Substring(0,8))" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Checkout failed for commit $($r.commit)" -ForegroundColor Yellow
    }
}

Write-Host "`n=== Done. $i repos processed. ===" -ForegroundColor Green
