param(
  [Parameter(Mandatory = $true)] [string] $Source,
  [Parameter(Mandatory = $true)] [string] $Converter,
  [string] $ProjectRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

function Fail($msg) { Write-Host "FAILED: $msg" -ForegroundColor Red; exit 1 }
function Ok($msg)   { Write-Host "OK: $msg" -ForegroundColor Green }

$target = Join-Path $ProjectRoot "public\models\avatar.glb"
if (-not (Test-Path $target))     { Fail "Cannot find $target. Run this from the avatar-engine folder." }
if (-not (Test-Path $Source))     { Fail "Source not found: $Source" }
if (-not (Test-Path $Converter))  { Fail "Converter not found: $Converter" }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $ProjectRoot "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$backup = Join-Path $backupDir "avatar-$stamp.glb"
Copy-Item $target $backup
Ok "Backed up current avatar to $backup"

$work = Join-Path $env:TEMP "signbridge-avatar-$stamp"
New-Item -ItemType Directory -Force -Path $work | Out-Null

if ($Source.ToLower().EndsWith(".zip")) {
  Expand-Archive -Path $Source -DestinationPath $work -Force
} else {
  Copy-Item (Join-Path (Split-Path $Source) "*") $work -Recurse -Force
}

$fbx = Get-ChildItem -Path $work -Filter *.fbx -Recurse | Select-Object -First 1
if (-not $fbx) { Fail "No .fbx file found in $Source" }
Ok "Using FBX: $($fbx.FullName)"

$outBase = Join-Path $work "avatar-new"
& $Converter --binary --input $fbx.FullName --output $outBase
if ($LASTEXITCODE -ne 0) { Fail "FBX2glTF exited with code $LASTEXITCODE" }

$newGlb = "$outBase.glb"
if (-not (Test-Path $newGlb)) { Fail "Conversion produced no GLB at $newGlb" }
if ((Get-Item $newGlb).Length -lt 10000) { Fail "Converted GLB is suspiciously small" }
Ok ("Converted to GLB ({0:N1} MB)" -f ((Get-Item $newGlb).Length / 1MB))

$bytes = [System.IO.File]::ReadAllBytes($newGlb)
if ([System.Text.Encoding]::ASCII.GetString($bytes, 0, 4) -ne "glTF") { Fail "Output is not a valid GLB" }

$jsonLen = [BitConverter]::ToUInt32($bytes, 12)
$json = [System.Text.Encoding]::UTF8.GetString($bytes, 20, $jsonLen) | ConvertFrom-Json

$imageCount = @($json.images).Count
if ($imageCount -lt 1) { Fail "No textures embedded. Re-download from Mixamo 'With Skin' and keep the textures next to the FBX." }
Ok "$imageCount texture image(s) embedded"

if (@($json.skins).Count -lt 1) { Fail "No skin found. The model is not rigged." }
Ok "Rig found ($(@($json.skins).Count) skin)"

$names = @($json.nodes | ForEach-Object { $_.name })
$required = @("Hips","Spine","Spine1","Spine2","Neck","Head",
              "LeftShoulder","LeftArm","LeftForeArm","LeftHand",
              "RightShoulder","RightArm","RightForeArm","RightHand")
foreach ($side in @("Left","Right")) {
  foreach ($finger in @("Thumb","Index","Middle","Ring","Pinky")) {
    foreach ($i in 1..3) { $required += "$side" + "Hand" + "$finger$i" }
  }
}

$missing = @()
foreach ($bone in $required) {
  if (-not ($names -contains "mixamorig:$bone" -or $names -contains "mixamorig$bone")) { $missing += $bone }
}
if ($missing.Count -gt 0) { Fail ("Missing Mixamo bones: " + ($missing -join ", ")) }
$boneCount = @($names | Where-Object { $_ -like "mixamorig*" }).Count
Ok "All required Mixamo bones present ($boneCount mixamorig bones total)"

Copy-Item $newGlb $target -Force
Ok "Installed new avatar to $target"

Write-Host ""
Write-Host "Restore the old avatar with:" -ForegroundColor Cyan
Write-Host "  Copy-Item `"$backup`" `"$target`" -Force"
Write-Host "Next: npm run dev, hard refresh (Ctrl+Shift+R), type 'i love you', click Generate." -ForegroundColor Cyan
