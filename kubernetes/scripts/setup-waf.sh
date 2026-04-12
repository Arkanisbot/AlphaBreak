#!/bin/bash
# =============================================================================
# WAF Setup for AlphaBreak CloudFront
# =============================================================================
# Prerequisites:
#   - AWS CLI v2 installed and configured
#   - CloudFront distribution already created (run setup-cloudfront.sh first)
#   - WAF must be created in us-east-1 for CloudFront
#
# Usage: CLOUDFRONT_DIST_ID=EXXXXXXXXX bash setup-waf.sh
# =============================================================================

set -euo pipefail

DIST_ID="${CLOUDFRONT_DIST_ID:?Set CLOUDFRONT_DIST_ID to your CloudFront distribution ID}"
WAF_NAME="alphabreak-waf"
REGION="us-east-1"

echo "Creating WAF WebACL: ${WAF_NAME}..."

# Create the WebACL with managed rule groups
ACL_ARN=$(aws wafv2 create-web-acl \
  --name "${WAF_NAME}" \
  --scope CLOUDFRONT \
  --region "${REGION}" \
  --default-action '{"Allow":{}}' \
  --visibility-config '{
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "alphabreakWAF"
  }' \
  --rules '[
    {
      "Name": "RateLimit",
      "Priority": 1,
      "Action": { "Block": {} },
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimit"
      }
    },
    {
      "Name": "AWSCommonRules",
      "Priority": 2,
      "OverrideAction": { "None": {} },
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "AWSCommonRules"
      }
    },
    {
      "Name": "KnownBadInputs",
      "Priority": 3,
      "OverrideAction": { "None": {} },
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesKnownBadInputsRuleSet"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "KnownBadInputs"
      }
    },
    {
      "Name": "IPReputation",
      "Priority": 4,
      "OverrideAction": { "None": {} },
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesAmazonIpReputationList"
        }
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "IPReputation"
      }
    }
  ]' \
  --query 'Summary.ARN' \
  --output text)

echo "WebACL created: ${ACL_ARN}"

# Associate WAF with CloudFront distribution
echo "Associating WAF with CloudFront distribution ${DIST_ID}..."

CF_ARN=$(aws cloudfront get-distribution \
  --id "${DIST_ID}" \
  --query 'Distribution.ARN' \
  --output text)

aws wafv2 associate-web-acl \
  --web-acl-arn "${ACL_ARN}" \
  --resource-arn "${CF_ARN}" \
  --region "${REGION}"

echo ""
echo "========================================="
echo "WAF setup complete!"
echo "  WebACL: ${WAF_NAME}"
echo "  ARN: ${ACL_ARN}"
echo "  Attached to: ${DIST_ID}"
echo "========================================="
echo ""
echo "Rules active:"
echo "  1. Rate limit: 2000 requests / 5 min per IP"
echo "  2. AWS Common Rule Set (XSS, SQLi, etc.)"
echo "  3. Known Bad Inputs (Log4j, etc.)"
echo "  4. IP Reputation (known malicious IPs)"
