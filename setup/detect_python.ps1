function Get-PythonInfo {
    $python = Get-Command python -ErrorAction SilentlyContinue

    if (-not $python) {
        $python = Get-Command python3 -ErrorAction SilentlyContinue
    }

    if (-not $python) {
        Write-Host "[FAIL] Python not found"
        return $false
    }

    $version = & $python.Source --version 2>&1

    Write-Host "[PASS] Python detected"
    Write-Host "  Version : $version"
    Write-Host "  Command : $($python.Name)"
    Write-Host "  Path    : $($python.Source)"

    return $true
}

Get-PythonInfo