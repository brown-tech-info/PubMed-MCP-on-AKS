<#
.SYNOPSIS
    Deploy PubMed Research API to Azure Container Apps
.DESCRIPTION
    Complete deployment script for Azure Container Apps with Container Registry
.EXAMPLE
    .\scripts\deploy-azure.ps1 -SubscriptionId "your-sub-id" -ResourceGroupName "pubmed-api-rg"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerAppName = "pubmed-research-api",
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerRegistryName = "pubmedregistry$(Get-Random -Minimum 100 -Maximum 999)",
    
    [Parameter(Mandatory=$false)]
    [string]$EnvironmentName = "pubmed-api-env",
    
    [Parameter(Mandatory=$false)]
    [string]$ImageTag = "latest"
)

Write-Host "🚀 Starting Azure Container Apps deployment..." -ForegroundColor Green
Write-Host "📋 Configuration:" -ForegroundColor Yellow
Write-Host "   Subscription: $SubscriptionId" -ForegroundColor White
Write-Host "   Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "   Location: $Location" -ForegroundColor White
Write-Host "   Container App: $ContainerAppName" -ForegroundColor White
Write-Host "   Registry: $ContainerRegistryName" -ForegroundColor White

# Check if .env file exists and load environment variables
$envFile = ".env"
if (Test-Path $envFile) {
    Write-Host "📄 Loading environment variables from .env..." -ForegroundColor Yellow
    
    $envVars = @{}
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            $envVars[$matches[1]] = $matches[2]
        }
    }
    
    $pubmedApiKey = $envVars["PUBMED_API_KEY"]
    $pubmedEmail = $envVars["PUBMED_EMAIL"]
    $pubmedToolName = $envVars["PUBMED_TOOL_NAME"]
    
    Write-Host "   ✅ API Key: $($pubmedApiKey.Substring(0,8))..." -ForegroundColor Green
    Write-Host "   ✅ Email: $pubmedEmail" -ForegroundColor Green
    Write-Host "   ✅ Tool Name: $pubmedToolName" -ForegroundColor Green
} else {
    Write-Host "⚠️ No .env file found. You'll need to set environment variables manually." -ForegroundColor Yellow
    $pubmedApiKey = Read-Host "Enter your PUBMED_API_KEY"
    $pubmedEmail = Read-Host "Enter your PUBMED_EMAIL"
    $pubmedToolName = "AzurePubMedAPI"
}

# Login to Azure (if not already logged in)
Write-Host "`n🔐 Checking Azure login..." -ForegroundColor Yellow
try {
    $currentSub = az account show --query id -o tsv 2>$null
    if ($currentSub -ne $SubscriptionId) {
        Write-Host "🔑 Logging into Azure..." -ForegroundColor Yellow
        az login
        az account set --subscription $SubscriptionId
    } else {
        Write-Host "✅ Already logged into correct subscription" -ForegroundColor Green
    }
} catch {
    Write-Host "🔑 Logging into Azure..." -ForegroundColor Yellow
    az login
    az account set --subscription $SubscriptionId
}

# Install Container Apps extension if needed
Write-Host "`n🔧 Ensuring Azure CLI extensions..." -ForegroundColor Yellow
az extension add --name containerapp --upgrade 2>$null
az provider register --namespace Microsoft.App 2>$null
az provider register --namespace Microsoft.OperationalInsights 2>$null

# Create resource group
Write-Host "`n📁 Creating resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location
Write-Host "✅ Resource group created/updated" -ForegroundColor Green

# Create Container Registry
Write-Host "`n🐳 Creating Azure Container Registry..." -ForegroundColor Yellow
az acr create --resource-group $ResourceGroupName --name $ContainerRegistryName --sku Basic --admin-enabled true --location $Location
Write-Host "✅ Container Registry created" -ForegroundColor Green

# Get ACR login server
$acrLoginServer = az acr show --name $ContainerRegistryName --resource-group $ResourceGroupName --query loginServer --output tsv
$imageName = "$acrLoginServer/pubmed-research-api:$ImageTag"

Write-Host "📦 Container image will be: $imageName" -ForegroundColor Cyan

# Build and push Docker image
Write-Host "`n🏗️ Building and pushing Docker image..." -ForegroundColor Yellow
Write-Host "This may take several minutes..." -ForegroundColor White

# Build using ACR Tasks (faster and more reliable than local builds)
az acr build --registry $ContainerRegistryName --image "pubmed-research-api:$ImageTag" .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker image built and pushed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    exit 1
}

# Create Container Apps environment
Write-Host "`n🌍 Creating Container Apps environment..." -ForegroundColor Yellow
az containerapp env create --name $EnvironmentName --resource-group $ResourceGroupName --location $Location
Write-Host "✅ Container Apps environment created" -ForegroundColor Green

# Get ACR credentials
$acrUsername = az acr credential show --name $ContainerRegistryName --query username --output tsv
$acrPassword = az acr credential show --name $ContainerRegistryName --query passwords[0].value --output tsv

# Deploy Container App
Write-Host "`n🚢 Deploying Container App..." -ForegroundColor Yellow

# Use proper PowerShell command construction instead of Invoke-Expression
az containerapp create `
  --name $ContainerAppName `
  --resource-group $ResourceGroupName `
  --environment $EnvironmentName `
  --image $imageName `
  --target-port 8000 `
  --ingress external `
  --registry-server $acrLoginServer `
  --registry-username $acrUsername `
  --registry-password $acrPassword `
  --env-vars "PORT=8000" "PUBMED_TOOL_NAME=$pubmedToolName" "PUBMED_API_KEY=secretref:pubmed-api-key" "PUBMED_EMAIL=secretref:pubmed-email" `
  --secrets "pubmed-api-key=$pubmedApiKey" "pubmed-email=$pubmedEmail" `
  --min-replicas 0 `
  --max-replicas 10 `
  --cpu 0.5 `
  --memory 1.0Gi

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container App deployed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Container App deployment failed" -ForegroundColor Red
    exit 1
}

# Get the application URL
Write-Host "`n🌐 Retrieving application URL..." -ForegroundColor Yellow
$appUrl = az containerapp show --name $ContainerAppName --resource-group $ResourceGroupName --query properties.configuration.ingress.fqdn --output tsv

Write-Host "`n🎉 Deployment completed successfully!" -ForegroundColor Green
Write-Host "📱 Application Details:" -ForegroundColor Cyan
Write-Host "   🌐 Application URL: https://$appUrl" -ForegroundColor White
Write-Host "   📖 API Documentation: https://$appUrl/docs" -ForegroundColor White
Write-Host "   🔄 OpenAPI Spec: https://$appUrl/openapi.json" -ForegroundColor White
Write-Host "   🏥 Health Check: https://$appUrl/health" -ForegroundColor White

# Test the deployment
Write-Host "`n🧪 Testing deployment..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "https://$appUrl/health" -Method Get -TimeoutSec 30
    if ($healthResponse.status -eq "healthy") {
        Write-Host "✅ Health check passed!" -ForegroundColor Green
        Write-Host "   Service: $($healthResponse.service)" -ForegroundColor White
        Write-Host "   Version: $($healthResponse.version)" -ForegroundColor White
    } else {
        Write-Host "⚠️ Health check returned unexpected status: $($healthResponse.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ Health check failed - the service may still be starting up" -ForegroundColor Yellow
    Write-Host "   Try again in a few minutes: https://$appUrl/health" -ForegroundColor White
}

Write-Host "`n📋 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Visit https://$appUrl/docs to explore the API" -ForegroundColor White
Write-Host "2. Use https://$appUrl/openapi.json for Azure Foundry integration" -ForegroundColor White
Write-Host "3. Test the API endpoints with your research queries" -ForegroundColor White

Write-Host "`n🔧 Management Commands:" -ForegroundColor Yellow
Write-Host "• View logs: az containerapp logs show --name $ContainerAppName --resource-group $ResourceGroupName --follow" -ForegroundColor White
Write-Host "• Scale app: az containerapp update --name $ContainerAppName --resource-group $ResourceGroupName --min-replicas 1" -ForegroundColor White
Write-Host "• Update app: az containerapp update --name $ContainerAppName --resource-group $ResourceGroupName --image $imageName" -ForegroundColor White

Write-Host "`n🎊 PubMed Research API is now live on Azure!" -ForegroundColor Green