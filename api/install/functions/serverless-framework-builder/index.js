const AdmZip = require('adm-zip');
const AWS = require('aws-sdk');
const util = require('util');
const spawn = require('child_process').spawn;
const path = require('path');

function flushOutputs() {
  // Configure the streams to be blocking
  makeBlockingStream__refinery(process.stdout);
  makeBlockingStream__refinery(process.stderr);
}

function makeBlockingStream__refinery(stream) {
  if (!stream || !stream._handle || !stream._handle.setBlocking) {
    // Not able to set blocking so just bail out
    return;
  }

  stream._handle.setBlocking(true);
}

const EFS_MOUNT = '/mnt/efs';

async function runCommand(cwd, command, args) {
  const nodeModulePath = `${process.cwd()}/node_modules`;
  const child = spawn(command, args, {
    cwd: cwd,
    env: {
      ...process.env,
      HOME: cwd,
      NODE_PATH: nodeModulePath,
      PATH: `${nodeModulePath}/serverless/bin:${process.env['PATH']}`
    }
  });

  let data = "";
  for await (const chunk of child.stdout) {
      console.log('stdout: ' + chunk);
      data += chunk;
  }
  let error = "";
  for await (const chunk of child.stderr) {
      console.error('stderr: ' + chunk);
      error += chunk;
  }
  const exitCode = await new Promise( (resolve, reject) => {
      child.on('close', resolve);
  });

  if(exitCode) {
      throw new Error( `subprocess error exit ${exitCode}, ${error}`);
  }
  return data;
}

async function executeAction(workDir, action) {
  const nodeModulePath = `${process.cwd()}/node_modules`;
  const serverlessScript = `${nodeModulePath}/serverless/bin/serverless.js`;

  if (action === 'deploy') {
    console.log('Deploying Serverless project...');
    const deployOutput = await runCommand(workDir, 'node', [serverlessScript, 'deploy', '--aws-s3-accelerate']);

    console.log(`Deployment output: ${deployOutput}`);

    // TODO check for errors in deployOutput

    console.log('Getting Serverless resources...');
    return await runCommand(workDir, 'node', [serverlessScript, 'info', '-v']);
  } else if (action === 'remove') {
    console.log('Removing Serverless project...');
    return await runCommand(workDir, 'node', [serverlessScript, 'remove']);
  }

  throw new Error(`action ${action} is not supported`);
}

exports.lambdaHandler = async (event, context) => {
  if (process.stdout._handle) {
    process.stdout._handle.setBlocking(true);
  }

  const action = event.action;
  const deploymentId = event.deployment_id;

  const workDir = path.join(EFS_MOUNT, deploymentId);

  const bucket = event.bucket;
  const key = event.key;

  const s3 = new AWS.S3();

  let serverlessPackage = undefined;

  console.log(`Downloading ${bucket}/${key}...`);
  try {
    serverlessPackage = await s3.getObject({
      Bucket: bucket,
      Key: key
    }).promise();
  } catch (e) {
    console.log(`Error while downloading Serverless package: ${e}`);
    throw e;
  }

  if (serverlessPackage === undefined) {
    flushOutputs();
    throw new Error('serverlessPackage is undefined');
  }

  console.log("Extracting serverless package...");
  const zip = new AdmZip(serverlessPackage.Body);
  zip.extractAllTo(workDir, true, undefined);

  let error = undefined;

  let data = '';

  try {
    console.log(`Executing action ${action}...`);
    data = await executeAction(workDir, action);
  } catch (e) {
    console.log(`Error while performing action: ${e}`);
    error = e;
  } finally {
    const outZip = new AdmZip();
    outZip.addLocalFolder(workDir, '/');

    await s3.putObject({
      Bucket: bucket,
      Key: key,
      Body: outZip.toBuffer()
    }).promise();
  }

  flushOutputs();

  if (error !== undefined) {
    throw error;
  }
  return {
    output: data
  };
};
