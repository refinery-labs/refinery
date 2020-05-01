import { ExecutionS3FilenameMetadata, ExecutionStatusType } from '@/types/execution-logs-types';

function getResourceName(resource_type: string, arnParts: string[]) {
  if (resource_type === 'lambda') {
    return arnParts[6];
  }

  if (resource_type === 'events') {
    return arnParts[5].replace('rule/', '');
  }

  return arnParts[5];
}

export function parseArn(input_arn: string) {
  // arn:aws:sns:us-west-2:148731734429:Example_Topic
  const fullArn = input_arn;
  const arnParts = input_arn.split(':');
  const resourceType = arnParts[2];
  const awsRegion = arnParts[3];
  const accountId = arnParts[4];

  return {
    fullArn,
    resourceType,
    awsRegion,
    accountId,
    resourceName: getResourceName(resourceType, arnParts)
  };
}

export function getLinkForArn(arn: string) {
  const parsedArn = parseArn(arn);

  if (parsedArn.resourceType === 'sns') {
    return `https://${parsedArn.awsRegion}.console.aws.amazon.com/sns/v2/home?region=${parsedArn.awsRegion}#/topic/${parsedArn.fullArn}`;
  }

  if (parsedArn.resourceType === 'lambda') {
    return `https://${parsedArn.awsRegion}.console.aws.amazon.com/lambda/home?region=${parsedArn.awsRegion}#/functions/${parsedArn.resourceName}?tab=graph`;
  }

  // Timer block
  if (parsedArn.resourceType === 'events') {
    return `https://${parsedArn.awsRegion}.console.aws.amazon.com/cloudwatch/home?region=${parsedArn.awsRegion}#rules:name=${parsedArn.resourceName}`;
  }

  if (parsedArn.resourceType === 'sqs') {
    return `https://console.aws.amazon.com/sqs/home?region=${parsedArn.awsRegion}#queue-browser:selected=https://sqs.${parsedArn.awsRegion}.amazonaws.com/${parsedArn.accountId}/${parsedArn.resourceName};prefix=`;
  }

  return null;
}

export function getMonitorLinkForCodeBlockArn(arn: string) {
  const parsedArn = parseArn(arn);

  if (!parsedArn) {
    return null;
  }

  return `https://${parsedArn.awsRegion}.console.aws.amazon.com/lambda/home?region=${parsedArn.awsRegion}#/functions/${parsedArn.resourceName}?tab=monitoring`;
}

export function getCloudWatchLinkForCodeBlockArn(arn: string) {
  const parsedArn = parseArn(arn);

  if (!parsedArn) {
    return null;
  }

  return `https://${parsedArn.awsRegion}.console.aws.amazon.com/cloudwatch/home?region=${parsedArn.awsRegion}#logStream:group=/aws/lambda/${parsedArn.resourceName};streamFilter=typeLogStreamPrefix`;
}
