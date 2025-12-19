import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Duration } from 'aws-cdk-lib';

export class EpicCareDailyExportStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Configuration - Use CDK context or environment variables for sensitive values
    // Set these via: cdk deploy --context graphClientId=xxx --context graphClientSecret=xxx
    // Or use AWS Secrets Manager for production deployments
    const REDSHIFT_SECRET_NAME = this.node.tryGetContext('redshiftSecretName') || 'redshift/pathforward-redshift-prod/admin';
    const REDSHIFT_CLUSTER_IDENTIFIER = 'pathforward-redshift-prod-redshif-redshiftcluster-1cojcxd2viyhj';
    const REDSHIFT_DATABASE_NAME = 'connectctrprod';
    const REDSHIFT_DB_USER = 'admin';
    const GRAPH_CLIENT_ID = this.node.tryGetContext('graphClientId') || process.env.GRAPH_CLIENT_ID || '';
    const GRAPH_CLIENT_SECRET = this.node.tryGetContext('graphClientSecret') || process.env.GRAPH_CLIENT_SECRET || '';
    const GRAPH_TENANT_ID = this.node.tryGetContext('graphTenantId') || process.env.GRAPH_TENANT_ID || '';
    const FROM_EMAIL = 'Ashley.Clarke@patientsync.com';
    const TO_EMAIL = 'data@epic-care.net';
    const BCC_EMAIL = 'clint.holliday@patientsync.com';
    
    // Validate required configuration
    if (!GRAPH_CLIENT_ID || !GRAPH_CLIENT_SECRET || !GRAPH_TENANT_ID) {
      throw new Error('Graph API credentials must be provided via CDK context (--context) or environment variables');
    }

    // Get the Redshift secret - CDK will reference it during build
    // The Lambda will use the SecretArn to fetch credentials at runtime via Redshift Data API
    const redshiftSecret = secretsmanager.Secret.fromSecretNameV2(this, 'RedshiftSecret', REDSHIFT_SECRET_NAME);
    const redshiftSecretArn = redshiftSecret.secretArn;

    // Create Lambda function
    const dailyExportFunction = new lambda.Function(this, 'EpicCareDailyExportFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('lambda'),
      timeout: Duration.minutes(15),
      memorySize: 512,
      environment: {
        REDSHIFT_CLUSTER_IDENTIFIER: REDSHIFT_CLUSTER_IDENTIFIER,
        REDSHIFT_DATABASE_NAME: REDSHIFT_DATABASE_NAME,
        REDSHIFT_DB_USER: REDSHIFT_DB_USER,
        REDSHIFT_SECRET_ARN: redshiftSecretArn,
        GRAPH_CLIENT_ID: GRAPH_CLIENT_ID,
        GRAPH_CLIENT_SECRET: GRAPH_CLIENT_SECRET,
        GRAPH_TENANT_ID: GRAPH_TENANT_ID,
        FROM_EMAIL: FROM_EMAIL,
        TO_EMAIL: TO_EMAIL,
        BCC_EMAIL: BCC_EMAIL,
      },
    });

    // Grant Lambda permissions to use Redshift Data API
    dailyExportFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'redshift-data:ExecuteStatement',
        'redshift-data:DescribeStatement',
        'redshift-data:GetStatementResult',
        'redshift-data:CancelStatement',
      ],
      resources: ['*'], // Redshift Data API doesn't support resource-level permissions
    }));

    // Grant Lambda permissions for Redshift IAM authentication (for temporary credentials)
    dailyExportFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'redshift:GetClusterCredentials',
      ],
      resources: [
        `arn:aws:redshift:${this.region}:${this.account}:dbuser:${REDSHIFT_CLUSTER_IDENTIFIER}/${REDSHIFT_DB_USER}`,
        `arn:aws:redshift:${this.region}:${this.account}:dbname:${REDSHIFT_CLUSTER_IDENTIFIER}/${REDSHIFT_DATABASE_NAME}`,
      ],
    }));

    // Grant Lambda permissions to read from Secrets Manager
    redshiftSecret.grantRead(dailyExportFunction);

    // Create EventBridge rule for 8am EST daily (1pm UTC)
    // cron(Minutes Hours Day-of-month Month Day-of-week Year)
    // 8am EST = 1pm UTC (13:00 UTC)
    // Note: During EDT (Daylight Saving), 8am EDT = 12pm UTC, so adjust hour to '12' if needed
    const dailySchedule = new events.Rule(this, 'EpicCareDailyExportSchedule', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '13', // 8am EST = 1pm UTC
        day: '*',
        month: '*',
        year: '*',
      }),
      description: 'Trigger EPIC Care Daily Export at 8am EST (1pm UTC) daily',
    });

    // Add Lambda as target for the schedule
    dailySchedule.addTarget(new targets.LambdaFunction(dailyExportFunction));

    // Output the Lambda function name and ARN
    new cdk.CfnOutput(this, 'LambdaFunctionName', {
      value: dailyExportFunction.functionName,
      description: 'Name of the EPIC Care Daily Export Lambda function',
    });

    new cdk.CfnOutput(this, 'LambdaFunctionArn', {
      value: dailyExportFunction.functionArn,
      description: 'ARN of the EPIC Care Daily Export Lambda function',
    });
  }
}
