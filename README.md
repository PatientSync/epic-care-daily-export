# EPIC Care Daily Export

Automated daily export system that queries Redshift for contact center data and emails the results as a CSV file using Microsoft Graph API.

## Overview

This AWS CDK project deploys a Lambda function that:
1. Executes a Redshift query to retrieve daily contact center data
2. Generates a CSV file (EPICDW-XREF.csv) from the query results
3. Authenticates with Microsoft Graph API using OAuth2
4. Sends the CSV file as an email attachment to `data@epic-care.net`

The Lambda function runs automatically every day at 8am EST via an EventBridge scheduled rule.

## Architecture

- **Lambda Function**: Python 3.11 runtime
- **Redshift Data API**: Queries Redshift cluster using IAM authentication
- **Microsoft Graph API**: Sends emails via OAuth2 client credentials flow
- **EventBridge**: Scheduled rule triggers Lambda daily at 8am EST

## Prerequisites

- AWS CLI configured with appropriate profile
- Node.js and CDK CLI installed
- Access to AWS Secrets Manager (for Redshift credentials if needed)
- Microsoft Graph API credentials (Client ID, Client Secret, Tenant ID)

## Configuration

Key configuration values are set in `lib/epic-care-daily-export-stack.ts`:
- Redshift cluster identifier
- Database name and user
- Graph API credentials
- Email addresses (from/to)
- Schedule time

## Deployment

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Build the project:**
   ```bash
   npm run build
   ```

3. **Deploy the stack:**
   ```bash
   npx cdk deploy --profile CH@MegaConnect
   ```

## Testing

Test the Lambda function manually:
```bash
aws lambda invoke \
  --function-name EpicCareDailyExportStack-EpicCareDailyExportFuncti-AXKgCthYd3AZ \
  --profile CH@MegaConnect \
  --region us-east-1 \
  response.json
```

## Project Structure

```
.
├── bin/                          # CDK app entry point
├── lib/                          # CDK stack definition
├── lambda/                       # Lambda function code
│   ├── handler.py               # Main Lambda handler
│   └── requirements.txt         # Python dependencies (none needed - uses boto3)
├── test/                         # Unit tests
├── cdk.json                      # CDK configuration
└── package.json                  # Node.js dependencies
```

## Useful Commands

* `npm run build`   compile TypeScript to JavaScript
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `npx cdk deploy`  deploy this stack to your default AWS account/region
* `npx cdk diff`    compare deployed stack with current state
* `npx cdk synth`   emits the synthesized CloudFormation template

## Security Notes

- Graph API credentials are stored as Lambda environment variables
- Redshift authentication uses IAM/temporary credentials
- All infrastructure is deployed via CDK (no manual resource creation)

## License

Copyright (c) 2024 PatientSync
