$repos = @(
  @{name='Ardesco/driver-binary-downloader-maven-plugin'; commit='262d793db60cdc1b2a3ea064d0d9aee264fa2147'},
  @{name='rometools/rome';                                commit='6b4a7e89cbf67dab0be32e7517f3d8ae3c2b4d75'},
  @{name='mongobee/mongobee';                             commit='4e1ec5e381121fc9e5ad54881c84029114bafa52'},
  @{name='wilkinsona/spring-boot-sample-tomcat-jndi';    commit='7661dd2c9cadd8350b5b71958a4fda308a6cdb61'},
  @{name='meixuesong/aggregate-persistence';              commit='692371a515f0a645a03af97f17575c542f3307b3'},
  @{name='JakeWharton/RxReplayingShare';                  commit='6761db704876de6c8d7a5a08c330629a7c2957d0'},
  @{name='alexnederlof/Jasper-report-maven-plugin';       commit='a10d07b217c28da38b6399a8282a5a2cd33109c4'},
  @{name='awslabs/amazon-kinesis-client';                 commit='1ce6123a788c28c5c24d1783b590215b20b8a41c'},
  @{name='davidmoten/rxjava-file';                       commit='515b781521272e779e08988bb3006c6dc454ca39'},
  @{name='alimate/errors-spring-boot-starter';            commit='41d2b0466a0e7d5cfb3a7e6a7d801c28820c6525'},
  @{name='amaembo/huntbugs';                             commit='05e7ebd511c99e7d19bd194757e8d6e92732e125'},
  @{name='nurkiewicz/typeof';                            commit='2663851363d0bc887da4efe29b340dc1b9ae24ca'},
  @{name='twitter/joauth';                               commit='3aab711e746c155b1a0359c7abb928ffeca2280e'},
  @{name='bedatadriven/jackson-datatype-jts';             commit='df56dc9b3de8620024879bb979a2da3ec48c07b7'},
  @{name='zapr-oss/druidry';                             commit='9879ce8da55a90e952fbf1906dee7b1e8fd87fc0'}
)

$dest = 'D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data'
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$total = $repos.Count
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
