#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { VeriBidStack } from '../lib/veribid-stack.js';

const app = new cdk.App();

new VeriBidStack(app, 'VeriBidStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? 'us-east-1',
  },
  description: 'VeriBid evidence-driven bid evaluation MVP baseline',
});
