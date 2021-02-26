const AdmZip = require('adm-zip');
const AWS = require('aws-sdk');
const util = require('util');
const spawn = require('child_process').spawn;
const path = require('path');

function flushProcessOutputsAndExit__refinery(exitCode) {
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

  if( exitCode) {
      throw new Error( `subprocess error exit ${exitCode}, ${error}`);
  }
  return data;
}

var serialize = function(object) {
  return JSON.stringify(object, null, 2)
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

  console.log(`${bucket} ${key}`)

  const s3 = new AWS.S3();

  const serverlessPackage = await s3.getObject({
    Bucket: bucket,
    Key: key
  }).promise();

  if (serverlessPackage === undefined) {
    console.log('serverlessPackage is undefined');
    flushProcessOutputsAndExit__refinery(0);
    return;
  }

  const zip = new AdmZip(serverlessPackage.Body);
  zip.extractAllTo(workDir, true);

  const nodeModulePath = `${process.cwd()}/node_modules`;
  const serverlessScript = `${nodeModulePath}/serverless/bin/serverless.js`;

  let data = '';

  if (action === 'deploy') {
    const deployOutput = await runCommand('node', [serverlessScript, 'deploy', '--aws-s3-accelerate']).catch(e => {
      return e;
    });

    // TODO check for errors in deployOutput

    data = await runCommand('node', [serverlessScript, 'info', '-v']).catch(e => {
      return e;
    });
  } else if (action === 'remove') {
    data = await runCommand('node', [serverlessScript, 'remove']).catch(e => {
      return e;
    });
  }

  const outZip = new AdmZip();
  outZip.addLocalFolder(workDir, '/');

  await s3.putObject({
    Bucket: bucket,
    Key: key,
    Body: outZip.toBuffer()
  }).promise();

  flushProcessOutputsAndExit__refinery(0);
  return {
    output: data
  };
}
