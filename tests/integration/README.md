# Commercial Backend Integration Tests

These tests verify pdfsmith works correctly with real commercial PDF parsing APIs. They require valid API credentials and will incur small costs (~$0.007 per full run).

## Setup

### 1. Install Test Dependencies

```bash
pip install pdfsmith[dev,commercial]
```

### 2. Configure Credentials

Create `.env` file in project root:

```bash
# AWS Textract
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1

# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key

# Google Document AI
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_DOCUMENT_AI_PROCESSOR_ID=your-processor-id

# Databricks
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_CLIENT_ID=your-client-id
DATABRICKS_CLIENT_SECRET=your-secret
# Optional: DATABRICKS_WAREHOUSE_ID=your-warehouse-id

# Enable commercial tests
RUN_COMMERCIAL_TESTS=1
```

See `docs/COMMERCIAL_BACKENDS.md` for detailed setup instructions for each provider.

### 3. Verify Setup

```bash
# Test individual provider
pytest tests/integration/ -v -m aws
pytest tests/integration/ -v -m azure
pytest tests/integration/ -v -m google
pytest tests/integration/ -v -m databricks
```

## Running Tests

### Run All Commercial Integration Tests

```bash
# Set environment flag
export RUN_COMMERCIAL_TESTS=1

# Run all integration tests
pytest tests/integration/ -v
```

**Cost**: ~$0.007 per run (assuming 1-page test PDFs)

### Run Specific Provider Tests

```bash
# AWS only
pytest tests/integration/ -v -m aws

# Azure only
pytest tests/integration/ -v -m azure

# Google only
pytest tests/integration/ -v -m google

# Databricks only
pytest tests/integration/ -v -m databricks
```

### Compare All Providers

```bash
# Run cross-provider comparison
pytest tests/integration/ -v -m commercial
```

## What Gets Tested

### AWS Textract
- ✓ Single-page PDF parsing
- ✓ Multi-page PDF handling (PNG conversion)
- ✓ Error handling for oversized files

### Azure Document Intelligence
- ✓ Single-page PDF parsing
- ✓ Large file handling (up to 500MB)
- ✓ `prebuilt-read` model usage

### Google Document AI
- ✓ Single-page PDF parsing
- ✓ 15-page limit enforcement
- ✓ Synchronous API usage

### Databricks
- ✓ PDF parsing via SQL warehouse
- ✓ Warehouse auto-detection
- ✓ OAuth M2M authentication

### Cross-Provider
- ✓ Consistency check across all providers
- ✓ Result comparison

## Troubleshooting

### "Commercial API tests disabled"

Set environment variable:
```bash
export RUN_COMMERCIAL_TESTS=1
```

Or in pytest:
```bash
RUN_COMMERCIAL_TESTS=1 pytest tests/integration/
```

### Provider-Specific Errors

**AWS: "Unable to locate credentials"**
- Check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set
- Or configure with: `aws configure`

**Azure: "Endpoint not found"**
- Verify endpoint URL format: `https://<resource>.cognitiveservices.azure.com/`
- Check resource is created in Azure portal

**Google: "GOOGLE_APPLICATION_CREDENTIALS must be set"**
- Download service account JSON from GCP console
- Set absolute path to JSON file

**Databricks: "No SQL warehouses found"**
- Create serverless SQL warehouse in Databricks
- Grant service principal "Can use" permission

See `docs/COMMERCIAL_BACKENDS.md` for detailed troubleshooting.

## Cost Control

### Estimated Costs per Test Run

| Provider | Cost/Test | Notes |
|----------|-----------|-------|
| AWS Textract | $0.0015 | 1 page × $1.50/1k |
| Azure | $0.0015 | 1 page × $1.50/1k |
| Google | $0.0015 | 1 page × $1.50/1k |
| Databricks | $0.003 | Varies by warehouse |

**Total**: ~$0.007 per full integration test run

### Tips to Minimize Costs

1. **Run selectively**: Use `-m` markers to test only what you need
2. **Use free tiers**: Azure offers F0 free tier (500 pages/month)
3. **Cache results**: Tests create minimal test PDFs
4. **Set billing alerts**: Monitor spending in cloud consoles
5. **Clean up**: Delete test resources when done

## CI/CD Integration

For CI/CD pipelines, use **mock tests** instead of integration tests to avoid costs and credential management:

```bash
# Unit tests with mocking (no API calls, no cost)
pytest tests/test_commercial_backends.py -v
```

**Recommendation**: Run integration tests manually before releases, not on every commit.

## Security Notes

1. **Never commit credentials** to version control
2. **Add `.env` to `.gitignore`**
3. **Use service accounts** with minimal permissions
4. **Rotate keys regularly**
5. **Monitor API usage** for unexpected activity

## Further Reading

- [Commercial Backends Configuration Guide](../../docs/COMMERCIAL_BACKENDS.md)
- [AWS Textract Pricing](https://aws.amazon.com/textract/pricing/)
- [Azure Document Intelligence Pricing](https://azure.microsoft.com/pricing/details/ai-document-intelligence/)
- [Google Document AI Pricing](https://cloud.google.com/document-ai/pricing)
- [Databricks Pricing](https://www.databricks.com/product/pricing)
