#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { EpicCareDailyExportStack } from '../lib/epic-care-daily-export-stack';

const app = new cdk.App();
new EpicCareDailyExportStack(app, 'EpicCareDailyExportStack', {
  env: { account: '673170146169', region: 'us-east-1' },
});