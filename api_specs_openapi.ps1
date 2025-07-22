# Create a static OpenAPI schema that Azure AI Foundry can accept
# This script generates an OpenAPI 3.0 specification with configurable server URL

param(
    [string]$ServerUrl = "https://your-api-name.your-environment.azurecontainerapps.io",
    [string]$OutputFile = "pubmed-openapi.json",
    [string]$ApiTitle = "PubMed Research API",
    [string]$ApiVersion = "1.0.0"
)

Write-Host "Generating OpenAPI 3.0 specification for Azure AI Foundry..." -ForegroundColor Yellow
Write-Host "Server URL: $ServerUrl" -ForegroundColor Cyan
Write-Host "Output File: $OutputFile" -ForegroundColor Cyan

$openApiSchema = @"
{
  "openapi": "3.0.0",
  "info": {
    "title": "$ApiTitle",
    "description": "A REST API for searching and retrieving scientific publications from PubMed",
    "version": "$ApiVersion"
  },
  "servers": [
    {
      "url": "$ServerUrl",
      "description": "API server"
    }
  ],
  "paths": {
    "/search": {
      "post": {
        "tags": ["Search"],
        "summary": "Search for publications in PubMed",
        "description": "Search for scientific publications using keywords, author names, topics, or any other PubMed-supported search terms",
        "operationId": "searchPublications",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "query": {
                    "type": "string",
                    "description": "Search query for PubMed articles",
                    "minLength": 1,
                    "maxLength": 500
                  },
                  "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10
                  }
                },
                "required": ["query"]
              },
              "example": {
                "query": "COVID-19 vaccine efficacy",
                "max_results": 10
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Search completed successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "success": {
                      "type": "boolean",
                      "description": "Whether the request was successful"
                    },
                    "data": {
                      "type": "string",
                      "description": "Response data in markdown format"
                    }
                  }
                }
              }
            }
          },
          "400": {
            "description": "Bad request",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "success": {
                      "type": "boolean",
                      "example": false
                    },
                    "error": {
                      "type": "string"
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/publication": {
      "post": {
        "tags": ["Publications"],
        "summary": "Get detailed information about a specific publication",
        "description": "Retrieve comprehensive details about a scientific publication using its PubMed ID (PMID)",
        "operationId": "getPublicationDetails",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "pmid": {
                    "type": "string",
                    "description": "PubMed ID of the publication",
                    "pattern": "^\\d+$"
                  }
                },
                "required": ["pmid"]
              },
              "example": {
                "pmid": "35000000"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Publication details retrieved successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "success": {
                      "type": "boolean"
                    },
                    "data": {
                      "type": "string",
                      "description": "Publication details in markdown format"
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/similar": {
      "post": {
        "tags": ["Similar"],
        "summary": "Find articles similar to a given publication",
        "description": "Discover publications related to a specific paper using PubMed's similar articles feature",
        "operationId": "getSimilarArticles",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "pmid": {
                    "type": "string",
                    "description": "PubMed ID of the reference publication",
                    "pattern": "^\\d+$"
                  },
                  "max_results": {
                    "type": "integer",
                    "description": "Maximum number of similar articles to return",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10
                  }
                },
                "required": ["pmid"]
              },
              "example": {
                "pmid": "35000000",
                "max_results": 10
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Similar articles found successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "success": {
                      "type": "boolean"
                    },
                    "data": {
                      "type": "string",
                      "description": "Similar articles in markdown format"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "SimpleAPIResponse": {
        "type": "object",
        "properties": {
          "success": {
            "type": "boolean",
            "description": "Whether the request was successful"
          },
          "data": {
            "type": "string",
            "description": "Response data in markdown format"
          }
        }
      },
      "ErrorResponse": {
        "type": "object",
        "properties": {
          "success": {
            "type": "boolean",
            "example": false
          },
          "error": {
            "type": "string",
            "description": "Error message"
          }
        }
      }
    }
  }
}
"@

# Save the schema to a file
try {
    $openApiSchema | Out-File -FilePath $OutputFile -Encoding UTF8
    Write-Host "✅ OpenAPI schema created: $OutputFile" -ForegroundColor Green
    
    # Validate file was created and show size
    if (Test-Path $OutputFile) {
        $fileSize = (Get-Item $OutputFile).Length
        Write-Host "📊 File size: $fileSize bytes" -ForegroundColor Gray
        Write-Host "🚀 Ready for Azure AI Foundry integration!" -ForegroundColor Magenta
        Write-Host "💡 Remember to update the server URL for your deployment" -ForegroundColor Yellow
    }
} catch {
    Write-Error "❌ Failed to create OpenAPI file: $_"
    exit 1
}

# Display usage examples
Write-Host "`n📋 Usage Examples:" -ForegroundColor Cyan
Write-Host "   # Use default placeholder URL:" -ForegroundColor Gray
Write-Host "   .\api_specs_openapi.ps1" -ForegroundColor White
Write-Host "`n   # Specify your deployment URL:" -ForegroundColor Gray
Write-Host "   .\api_specs_openapi.ps1 -ServerUrl `"https://your-actual-deployment.azurecontainerapps.io`"" -ForegroundColor White
Write-Host "`n   # Create a specific environment version:" -ForegroundColor Gray
Write-Host "   .\api_specs_openapi.ps1 -ServerUrl `"https://dev-api.example.com`" -OutputFile `"dev-openapi.json`"" -ForegroundColor White