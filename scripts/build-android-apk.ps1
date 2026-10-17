param(
    [Parameter(Mandatory = $true)]
    [string]$ApiUrl,
    [string]$BuildRoot = 'C:\mc11'
)

$ErrorActionPreference = 'Stop'
$apiUri = [uri]$ApiUrl
if (-not $apiUri.IsAbsoluteUri -or $apiUri.Scheme -ne 'https' -or
    $apiUri.UserInfo -or $apiUri.Query -or $apiUri.Fragment) {
    throw 'Informe uma URL HTTPS pública da API, sem credenciais, query ou fragmento.'
}

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$mobileRoot = Join-Path $repoRoot 'apps\mobile'
$buildRoot = [IO.Path]::GetFullPath($BuildRoot)
$outputDir = Join-Path $repoRoot 'output'
$apkOutput = Join-Path $outputDir 'Rautto-teste.apk'

if ($buildRoot -eq [IO.Path]::GetPathRoot($buildRoot) -or
    $buildRoot.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar,
                           [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Use uma pasta temporária curta fora do repositório, como C:\mc11.'
}
if (Test-Path -LiteralPath $buildRoot) {
    if (Get-ChildItem -LiteralPath $buildRoot -Force | Select-Object -First 1) {
        throw "A pasta temporária não está vazia: $buildRoot"
    }
}

if (-not $env:JAVA_HOME) {
    $env:JAVA_HOME = 'C:\Program Files\Android\Android Studio\jbr'
}
if (-not $env:ANDROID_HOME) {
    $env:ANDROID_HOME = Join-Path $env:LOCALAPPDATA 'Android\Sdk'
}
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:GRADLE_USER_HOME = Join-Path $buildRoot '.gradle'
$env:EXPO_PUBLIC_API_URL = $apiUri.GetLeftPart([UriPartial]::Path).TrimEnd('/')
$env:NODE_ENV = 'production'

foreach ($required in @((Join-Path $env:JAVA_HOME 'bin\java.exe'),
                        (Join-Path $env:ANDROID_HOME 'platform-tools\adb.exe'))) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Ferramenta Android não encontrada: $required"
    }
}

New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
foreach ($name in @('package.json', 'pnpm-lock.yaml', 'app.json', 'index.ts', 'App.tsx', 'tsconfig.json')) {
    Copy-Item -LiteralPath (Join-Path $mobileRoot $name) -Destination $buildRoot
}
foreach ($name in @('assets', 'src')) {
    Copy-Item -LiteralPath (Join-Path $mobileRoot $name) -Destination $buildRoot -Recurse
}
Set-Content -LiteralPath (Join-Path $buildRoot 'pnpm-workspace.yaml') -Value 'nodeLinker: hoisted' -Encoding utf8

Push-Location $buildRoot
try {
    & pnpm install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências.' }
    & node node_modules/expo/bin/cli prebuild --platform android --no-install
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar projeto Android.' }

    Push-Location (Join-Path $buildRoot 'android')
    try {
        & .\gradlew.bat :app:assembleRelease --no-daemon
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar APK.' }
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}

$builtApk = Join-Path $buildRoot 'android\app\build\outputs\apk\release\app-release.apk'
if (-not (Test-Path -LiteralPath $builtApk)) { throw 'APK não encontrado após o build.' }
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
Copy-Item -LiteralPath $builtApk -Destination $apkOutput -Force
Write-Output "APK: $apkOutput"
Write-Output "SHA-256: $((Get-FileHash -LiteralPath $apkOutput -Algorithm SHA256).Hash)"
