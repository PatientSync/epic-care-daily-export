# EPIC Care Daily Export - Deployment Guide

## Overview
This CDK stack deploys a Lambda function that:
1. Queries Redshift for daily contact center data
2. Generates a CSV file (EPICDW-XREF.csv)
3. Emails the CSV to data@epic-care.com using Microsoft Graph API

## Prerequisites
- AWS CLI configured with CH@MegaConnect profile
- Node.js and CDK CLI installed
- Access to AWS Secrets Manager to find the Redshift password secret

## Finding the Redshift Secret Name

Before deploying, you need to identify the correct Secrets Manager secret name for the Redshift password. You can find it by:

1. **Check AWS Secrets Manager Console:**
   - Go to AWS Secrets Manager in us-east-1
   - Look for secrets related to Redshift, pathforward, or admin

2. **Or use AWS CLI:**
   ```bash
   aws secretsmanager list-secrets --profile CH@MegaConnect --region us-east-1
   ```

3. **Update the secret name in CDK:**
   - Edit `lib/epic care daily export-stack.ts`
   - Update the `REDSHIFT_SECRET_NAME` constant (line 15)
   - Or pass it via CDK context: `cdk deploy --context redshiftSecretName=your-secret-name`

## Configuration

The following are configured in the CDK stack:
- **Redshift Cluster**: `pathforward-redshift-prod-redshif-redshiftcluster-1cojcxd2viyhj`
- **Database**: `connectctrprod`
- **Database User**: `admin`
- **From Email**: `Ashley.Clarke@patientsync.com`
- **To Email**: `data@epic-care.com`
- **Schedule**: 8am EST daily (1pm UTC)

## Deployment Steps

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Build the TypeScript:**
   ```bash
   npm run build
   ```

3. **Synthesize the CloudFormation template:**
   ```bash
   cdk synth --profile CH@MegaConnect
   ```

4. **Deploy the stack:**
   
   **Required:** Provide Graph API credentials via CDK context:
   ```bash
   cdk deploy --profile CH@MegaConnect \
     --context graphClientId=your-client-id \
     --context graphClientSecret=your-client-secret \
     --context graphTenantId=your-tenant-id
   ```

   Optional: Specify Redshift secret name:
   ```bash
   cdk deploy --profile CH@MegaConnect \
     --context graphClientId=your-client-id \
     --context graphClientSecret=your-client-secret \
     --context graphTenantId=your-tenant-id \
     --context redshiftSecretName=your-secret-name
   ```

## Testing

After deployment, you can test the Lambda function manually:

```bash
aws lambda invoke \
  --function-name <LambdaFunctionName> \
  --profile CH@MegaConnect \
  --region us-east-1 \
  response.json
```

## Schedule Adjustment

The default schedule is set to 8am EST (1pm UTC). To adjust:
- Edit `lib/epic care daily export-stack.ts`
- Modify the `hour` field in the cron schedule (line 72)
- During EDT (Daylight Saving), use hour '12' for 8am EDT

## Troubleshooting

1. **Secret not found error:**
   - Verify the secret name exists in Secrets Manager
   - Check that the Lambda has permissions to read the secret
   - Ensure the secret contains the password in the expected format

2. **Redshift query timeout:**
   - Increase Lambda timeout in the stack (currently 15 minutes)
   - Check Redshift cluster performance

3. **Email sending fails:**
   - Verify Graph API credentials are correct
   - Check that the FROM_EMAIL has permission to send emails via Graph API
   - Review CloudWatch Logs for detailed error messages

