<#
.SYNOPSIS
    Fix dependency conflicts in requirements.txt
.DESCRIPTION
    Updates package versions to resolve conflicts between FastAPI and MCP
#>

Write-Host "🔧 Fixing dependency conflicts..." -ForegroundColor Yellow

# Updated requirements with compatible versions
$updatedRequirements = @"
fastapi==0.109.0
uvicorn[standard]==0.25.0
pydantic==2.5.3
httpx==0.26.0
xmltodict==0.13.0
python-dotenv==1.0.0
mcp==1.0.0
"@

# Backup original requirements
if (Test-Path "requirements.txt") {
    Copy-Item "requirements.txt" "requirements.txt.backup"
    Write-Host "📋 Backed up original requirements.txt" -ForegroundColor Green
}

# Write updated requirements
Set-Content -Path "requirements.txt" -Value $updatedRequirements
Write-Host "✅ Updated requirements.txt with compatible versions" -ForegroundColor Green

Write-Host "`n📦 Updated packages:" -ForegroundColor Cyan
Write-Host "   • FastAPI: 0.104.1 → 0.109.0" -ForegroundColor White
Write-Host "   • Uvicorn: 0.24.0 → 0.25.0" -ForegroundColor White
Write-Host "   • Pydantic: 2.5.0 → 2.5.3" -ForegroundColor White
Write-Host "   • HTTPx: 0.25.0 → 0.26.0" -ForegroundColor White

Write-Host "`n🚀 Now try installing again:" -ForegroundColor Yellow
Write-Host "   pip install -r requirements.txt" -ForegroundColor White