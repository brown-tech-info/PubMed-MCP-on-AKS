# PubMed Research API

A FastAPI-based REST API wrapper for PubMed research, designed for deployment on Azure Container Apps and integration with Azure AI Foundry Agents.

## 🌟 Features

- 🔍 **Search PubMed** - Search for scientific publications using keywords, authors, or topics
- 📄 **Publication Details** - Get comprehensive information about specific papers via PMID
- 🔗 **Similar Articles** - Discover related research papers using PubMed's similarity algorithms
- 📊 **OpenAPI 3.0** - Azure AI Foundry compatible API specification
- 🚀 **Azure Ready** - Optimized for Azure Container Apps deployment
- 🤖 **AI Agent Ready** - Perfect for integration with Azure AI Foundry Agents
- 🐳 **Containerized** - Docker support for consistent deployments

## 📋 Prerequisites

- Python 3.9+
- Azure CLI (for Azure deployment)
- Docker (optional, for containerized deployment)
- PubMed API access (free registration recommended)

## 🚀 Quick Start

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd azure-hosted-pubmed-mcp
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Setup environment
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Configure environment** (edit `.env`):
   ```bash
   PUBMED_EMAIL=your_email@domain.com
   PUBMED_TOOL_NAME=YourAppName
   PORT=8000
   ```

3. **Run locally**:
   ```bash
   python app.py
   ```

4. **Access API**:
   - API Base: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## ☁️ Azure Deployment

### Automated Deployment

1. **Run deployment script**:
   ```powershell
   .\scripts\deploy-azure.ps1 -SubscriptionId "your-subscription-id" -ResourceGroupName "your-resource-group"
   ```

### Manual Deployment Steps

1. **Create Azure Resources**:
   ```bash
   # Create resource group
   az group create --name pubmed-api-rg --location eastus
   
   # Create container registry
   az acr create --resource-group pubmed-api-rg --name yourregistry --sku Basic
   
   # Create container app environment
   az containerapp env create --name pubmed-env --resource-group pubmed-api-rg --location eastus
   ```

2. **Build and push container**:
   ```bash
   # Build image
   az acr build --registry yourregistry --image pubmed-api:latest .
   
   # Deploy container app
   az containerapp create \
     --name pubmed-research-api \
     --resource-group pubmed-api-rg \
     --environment pubmed-env \
     --image yourregistry.azurecr.io/pubmed-api:latest
   ```

## 📚 API Documentation

### Endpoints

#### `POST /search`
Search PubMed publications

**Request Body:**
```json
{
  "query": "machine learning medicine",
  "max_results": 10
}
```

**Response:**
```json
{
  "success": true,
  "data": "## Search Results\n\n1. **Title**: Example Paper\n   - **Authors**: Smith, J. et al.\n   - **PMID**: 12345678\n   ..."
}
```

#### `POST /publication`
Get detailed publication information

**Request Body:**
```json
{
  "pmid": "12345678"
}
```

#### `POST /similar`
Find similar articles

**Request Body:**
```json
{
  "pmid": "12345678",
  "max_results": 10
}
```

### Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error description here"
}
```

## 🤖 Azure AI Foundry Integration

### Generating OpenAPI Specification

1. **Generate the spec**:
   ```powershell
   .\api_specs_openapi.ps1
   ```

2. **Update server URL** in generated `pubmed-openapi.json` with your deployment URL

3. **Import into Azure AI Foundry**:
   - Navigate to Azure AI Foundry
   - Go to Tools → Add Tool → OpenAPI 3.0 specified tool
   - Upload your `pubmed-openapi.json` file

### Agent Configuration

Configure your Azure AI Foundry Agent with instructions like:

```
You are a helpful research assistant that helps users find scientific publications. 
Use the PubMed tools to search for articles, get publication details, and find similar research.
Always provide citations with PMID numbers when referencing papers.
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `PUBMED_EMAIL` | Your email for PubMed API identification | ✅ | - |
| `PUBMED_API_KEY` | PubMed API key (optional but recommended) | ❌ | - |
| `PUBMED_TOOL_NAME` | Tool name for API requests | ❌ | AzurePubMedAPI |
| `PORT` | Server port | ❌ | 8000 |

### PubMed API Guidelines

- **Email Required**: PubMed requires an email for API identification
- **Rate Limits**: Max 3 requests/second without API key, 10/second with key
- **API Key**: Free registration at [NCBI](https://www.ncbi.nlm.nih.gov/account/)

## 🐳 Docker Support

### Local Docker Build

```bash
# Build image
docker build -t pubmed-api .

# Run container
docker run -p 8000:8000 --env-file .env pubmed-api
```

### Environment Variables in Docker

```bash
docker run -p 8000:8000 \
  -e PUBMED_EMAIL=your_email@domain.com \
  -e PUBMED_TOOL_NAME=YourApp \
  pubmed-api
```

## 📁 Project Structure

```
├── app.py                    # Main FastAPI application
├── server.py                 # Original MCP server (reference)
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container configuration
├── .env.example             # Environment template
├── api_specs_openapi.ps1    # OpenAPI spec generator
├── scripts/
│   └── deploy-azure.ps1     # Azure deployment automation
└── README.md               # This file
```

## 🔧 Development

### Adding New Endpoints

1. Add endpoint logic to `app.py`
2. Update the OpenAPI specification in `api_specs_openapi.ps1`
3. Regenerate spec: `.\api_specs_openapi.ps1`
4. Test locally before deployment

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test search endpoint
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "COVID-19 vaccine", "max_results": 5}'
```

## 🔒 Security Notes

- Environment files (`.env`) are excluded from git
- Generated OpenAPI specs contain deployment URLs and should not be committed
- PubMed API keys should be kept secure
- Azure resource names should be parameterized for different environments

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` endpoint when running locally
- **Issues**: Please create an issue in the repository
- **PubMed API**: [Official Documentation](https://www.ncbi.nlm.nih.gov/books/NBK25497/)

## 🔄 Version History

- **v1.0.0**: Initial release with core PubMed search functionality
- **v1.1.0**: Added Azure AI Foundry compatibility
- **v1.2.0**: Improved error handling and documentation