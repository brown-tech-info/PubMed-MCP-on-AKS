<#
.SYNOPSIS
    Setup script for PubMed Azure Container Apps API deployment
.DESCRIPTION
    This script creates all necessary files for deploying the PubMed MCP server as an Azure Container App
.EXAMPLE
    .\setup-pubmed-api.ps1
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$WorkspacePath = (Get-Location).Path,
    
    [Parameter(Mandatory=$false)]
    [string]$PubMedApiKey = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Email = ""
)

Write-Host "🚀 Setting up PubMed Azure Container Apps API..." -ForegroundColor Green
Write-Host "📁 Workspace: $WorkspacePath" -ForegroundColor Cyan

# Create project structure
$folders = @("src", "config", "scripts")
foreach ($folder in $folders) {
    $folderPath = Join-Path $WorkspacePath $folder
    if (!(Test-Path $folderPath)) {
        New-Item -ItemType Directory -Path $folderPath -Force | Out-Null
        Write-Host "✅ Created folder: $folder" -ForegroundColor Green
    }
}

# Function to create files
function New-ProjectFile {
    param(
        [string]$FilePath,
        [string]$Content,
        [string]$Description
    )
    
    $fullPath = Join-Path $WorkspacePath $FilePath
    Set-Content -Path $fullPath -Value $Content -Encoding UTF8
    Write-Host "✅ Created: $FilePath - $Description" -ForegroundColor Green
}

Write-Host "`n📄 Creating project files..." -ForegroundColor Yellow

# 1. Create requirements.txt
$requirementsContent = @"
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
httpx==0.25.0
xmltodict==0.13.0
python-dotenv==1.0.0
mcp==1.0.0
"@

New-ProjectFile -FilePath "requirements.txt" -Content $requirementsContent -Description "Python dependencies"

# 2. Create .env.example
$envExampleContent = @"
# PubMed API Configuration
PUBMED_API_KEY=your_pubmed_api_key_here
PUBMED_EMAIL=your_email@domain.com
PUBMED_TOOL_NAME=AzurePubMedAPI

# Application Configuration
PORT=8000
"@

New-ProjectFile -FilePath ".env.example" -Content $envExampleContent -Description "Environment variables template"

# 3. Create actual .env file if values provided
if ($PubMedApiKey -and $Email) {
    $envContent = @"
# PubMed API Configuration
PUBMED_API_KEY=$PubMedApiKey
PUBMED_EMAIL=$Email
PUBMED_TOOL_NAME=AzurePubMedAPI

# Application Configuration
PORT=8000
"@
    New-ProjectFile -FilePath ".env" -Content $envContent -Description "Environment variables (configured)"
}

# 4. Create Dockerfile
$dockerfileContent = @"
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "app.py"]
"@

New-ProjectFile -FilePath "Dockerfile" -Content $dockerfileContent -Description "Docker container configuration"

# 5. Create .dockerignore
$dockerignoreContent = @"
.env
.git
.gitignore
README.md
.vscode
.pytest_cache
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.DS_Store
.venv
"@

New-ProjectFile -FilePath ".dockerignore" -Content $dockerignoreContent -Description "Docker ignore file"

# 6. Create .gitignore
$gitignoreContent = @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Azure
.azure/

# Logs
*.log
logs/

# Database
*.db
*.sqlite3

# Secrets
*.pem
*.key
secrets.json
"@

New-ProjectFile -FilePath ".gitignore" -Content $gitignoreContent -Description "Git ignore file"

Write-Host "`n📝 Creating README.md..." -ForegroundColor Yellow

# 7. Create README.md
$readmeContent = @"
# PubMed Research API

A FastAPI-based REST API wrapper for the PubMed MCP server, designed for deployment on Azure Container Apps and integration with Azure Foundry Agents.

## Features

- 🔍 **Search PubMed** - Search for scientific publications
- 📄 **Publication Details** - Get detailed information about specific papers
- 🔗 **Similar Articles** - Find related research papers
- 📊 **OpenAPI 3.0** - Auto-generated API documentation
- 🚀 **Azure Ready** - Optimized for Azure Container Apps
- 🤖 **AI Agent Ready** - Perfect for Azure Foundry integration

## Quick Start

### Local Development

1. **Clone and setup**:
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Copy environment template
   cp .env.example .env
   # Edit .env with your PubMed API credentials
   ```

2. **Run locally**:
   ```bash
   python app.py
   ```

3. **Access API**:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - OpenAPI Spec: http://localhost:8000/openapi.json

### Azure Deployment

1. **Run deployment script**:
   ```powershell
   .\scripts\deploy-azure.ps1 -SubscriptionId "your-id" -ResourceGroupName "pubmed-api-rg"
   ```

## API Endpoints

### POST /search
Search PubMed publications
```json
{
  "query": "machine learning medicine",
  "max_results": 10,
  "sort": "relevance",
  "date_range": "2020:2024"
}
```

### POST /publication
Get publication details
```json
{
  "pmid": "12345678"
}
```

### POST /similar
Find similar articles
```json
{
  "pmid": "12345678",
  "max_results": 10
}
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PUBMED_API_KEY` | Your PubMed API key | No |
| `PUBMED_EMAIL` | Your email for API identification | Yes |
| `PUBMED_TOOL_NAME` | Tool name for API requests | No |
| `PORT` | Server port (default: 8000) | No |

## Azure Foundry Integration

This API provides OpenAPI 3.0 specifications that can be directly imported into Azure Foundry Agents. The API endpoints are designed to work seamlessly with AI agents for research assistance.

## Support

For issues and questions, please check the documentation or create an issue in the repository.
"@

New-ProjectFile -FilePath "README.md" -Content $readmeContent -Description "Project documentation"

# Create next steps instructions
Write-Host "`n🎉 Setup completed successfully!" -ForegroundColor Green
Write-Host "`n📋 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Run: .\setup-pubmed-api.ps1 -PubMedApiKey 'your-key' -Email 'your-email'" -ForegroundColor Cyan
Write-Host "2. I'll create the Python files in the next step" -ForegroundColor Cyan
Write-Host "3. Then we'll create the Azure deployment scripts" -ForegroundColor Cyan

Write-Host "`n📁 Files created in: $WorkspacePath" -ForegroundColor Green
Write-Host "✅ Project structure ready!" -ForegroundColor Green