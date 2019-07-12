import { BlockExecutionMetadata, ExecutionLogMetadata } from '@/types/deployment-executions-types';
import { ExecutionStatusType } from '@/types/api-types';

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

/**
 * We store metadata about a log instance in the filename of the file in S3. This lets us avoid reading
 * the file in order to get information about the log contents.
 * Example filename:
 * 3bea10f3-4064-4945-99b7-28b9865e3ee8/8437501899/6f67b9ca-a50b-4a13-91fe-1e3aef411f8d/RETURN~Get_Data_RFNpESp7R3~1c81c051-1770-4e2e-9b57-20ddf7ba176c~1562498056
 * @param logName Super long filename that contains concatenated chunks of data that will be parsed out.
 */
export function parseS3LogFilename(logName: string): ExecutionLogMetadata {
  const pathParts = logName.split('/');
  const executionId = pathParts[2];
  const logFileName = pathParts[3];
  const logFileNameParts = logFileName.split('~');
  const logType = logFileNameParts[0];
  const lambdaName = logFileNameParts[1];
  const logId = logFileNameParts[2];
  const timestamp = parseInt(logFileNameParts[3], 10);

  return {
    executionId,
    executionStatus: logType as ExecutionStatusType,
    blockName: lambdaName,
    logId,
    rawLog: logName,
    timestamp
  };
}

export function getLinkForArn(arn: string) {
  const parsedArn = parseArn(arn);

  if (parsedArn.resourceType === 'sns') {
    return `https://${parsedArn.awsRegion}.console.aws.amazon.com/sns/v2/home?region=${parsedArn.awsRegion}#/topic/${
      parsedArn.fullArn
    }`;
  }

  if (parsedArn.resourceType === 'lambda') {
    return `https://${parsedArn.awsRegion}.console.aws.amazon.com/lambda/home?region=${
      parsedArn.awsRegion
    }#/functions/${parsedArn.resourceName}?tab=graph`;
  }

  // Timer block
  if (parsedArn.resourceType === 'events') {
    return `https://${parsedArn.awsRegion}.console.aws.amazon.com/cloudwatch/home?region=${
      parsedArn.awsRegion
    }#rules:name=${parsedArn.resourceName}`;
  }

  if (parsedArn.resourceType === 'sqs') {
    return `https://console.aws.amazon.com/sqs/home?region=${parsedArn.awsRegion}#queue-browser:selected=https://sqs.${
      parsedArn.awsRegion
    }.amazonaws.com/${parsedArn.accountId}/${parsedArn.resourceName};prefix=`;
  }

  return null;
}

export function getMonitorLinkForCodeBlockArn(arn: string) {
  const parsedArn = parseArn(arn);

  if (!parsedArn) {
    return null;
  }

  return `https://${parsedArn.awsRegion}.console.aws.amazon.com/lambda/home?region=${parsedArn.awsRegion}#/functions/${
    parsedArn.resourceName
  }?tab=monitoring`;
}

export function getCloudWatchLinkForCodeBlockArn(arn: string) {
  const parsedArn = parseArn(arn);

  if (!parsedArn) {
    return null;
  }

  return `https://${parsedArn.awsRegion}.console.aws.amazon.com/cloudwatch/home?region=${
    parsedArn.awsRegion
  }#logStream:group=/aws/lambda/${parsedArn.resourceName};streamFilter=typeLogStreamPrefix`;
}
