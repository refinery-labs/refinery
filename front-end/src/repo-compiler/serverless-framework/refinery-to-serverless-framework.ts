import {
  ApiEndpointWorkflowState,
  LambdaWorkflowState,
  ProjectConfig,
  RefineryProject,
  ScheduleTriggerWorkflowState,
  SnsTopicWorkflowState,
  SqsQueueWorkflowState,
  WorkflowFile,
  WorkflowFileLink,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import {
  defaultWorkflowStateHandler,
  setupProjectRepo,
  WorkflowStateActions
} from '@/repo-compiler/one-to-one/refinery-to-git';
import { PromiseFsClient } from 'isomorphic-git';
import Path from 'path';
import {
  GLOBAL_BASE_PATH,
  LAMBDA_SHARED_FILES_DIR,
  PROJECT_SHARED_FILES_DIR,
  PROJECTS_CONFIG_FOLDER,
  SERVERLESS_CONFIG_FOLDER
} from '@/repo-compiler/shared/constants';
import { convertProjectDownloadZipConfigToFileList, createDownloadZipConfig } from '@/utils/project-debug-utils';
import { getFolderName, getUniqueLambdaIdentifier, maybeMkdir, writeConfig } from '@/repo-compiler/shared/fs-utils';
import slugify from 'slugify';
import {
  languageToBaseCodeLookup,
  UNIMPLEMENTED_BASE_CODE_MESSAGE
} from '@/repo-compiler/serverless-framework/base-code-lookup';

const languageToLayerLookup: Record<string, string> = {
  'nodejs8.10': 'arn:aws:lambda:us-west-2:623905218559:layer:refinery-layer:1'
};

function lambdaEnvironmentVariables() {
  return {
    REDIS_HOSTNAME: '$(file(secrets.json:REDIS_HOSTNAME))',
    REDIS_PASSWORD: '$(file(secrets.json:REDIS_PASSWORD))',
    REDIS_PORT: '6379',
    EXECUTION_PIPELINE_ID: '<placeholder>',
    LOG_BUCKET_NAME: 'lambda-logging-serverless-2',
    PACKAGES_BUCKET_NAME: 'lambdabuildpackages-a82d4bf25863445bb29abcaea1647602',
    PIPELINE_LOGGING_LEVEL: 'LOG_ALL',
    EXECUTION_MODE: 'REGULAR',
    TRANSITION_DATA: JSON.stringify({
      if: [],
      else: [],
      exception: [],
      then: [],
      ['fan-out']: [],
      ['fan-in']: [],
      merge: []
    })
  };
}

function createServerlessLambdaFunction(
  lambdaPath: string,
  workflowState: LambdaWorkflowState,
  lambdaEvents: object[],
  projectEnvVars: Record<string, string>
) {
  const functionNameSlug = slugify(workflowState.name).toLowerCase();

  const formattedEnvVariables: Record<string, string> = Object.keys(workflowState.environment_variables).reduce(
    (envVars, envKey) => {
      const envVar = workflowState.environment_variables[envKey];
      return {
        ...envVars,
        [envVar.name]: projectEnvVars[envKey]
      };
    },
    {}
  );

  const languageLayer = languageToLayerLookup[workflowState.language];
  if (languageLayer === '') {
    throw Error(`Unsupported language for serverless framework compilation ${workflowState.language}`);
  }

  return {
    [functionNameSlug]: {
      handler: 'lambda._init',
      name: functionNameSlug,
      description: 'Description of what the lambda function does',
      runtime: 'provided',
      memorySize: workflowState.memory,
      timeout: workflowState.max_execution_time,
      //provisionedConcurrency: workflowState.provisioned_concurrency_count,
      reservedConcurrency: workflowState.reserved_concurrency_count,
      tracing: 'PassThrough',
      events: lambdaEvents || [],
      layers: [languageLayer, ...workflowState.layers],
      environment: {
        ...lambdaEnvironmentVariables(),
        ...formattedEnvVariables
      }
    }
  };
}

function createServerlessServiceConfig(project: RefineryProject, lambdaConfigFiles: string[]) {
  const projectNameSlug = slugify(project.name);
  return {
    service: projectNameSlug,
    package: {
      individually: true,
      functionsPath: '../lambda'
    },
    plugins: ['serverless-s3-remover', 'serverless-stack-output'],
    custom: {
      remover: {
        buckets: ['lambda-logging-serverless-2']
      },
      output: {
        handler: 'scripts/output.handler',
        file: 'stack.json'
      }
    },
    provider: {
      name: 'aws',
      runtime: 'provided',
      region: 'us-west-2',
      iamRoleStatements: [
        {
          Effect: 'Allow',
          Action: 'S3:PutObject',
          Resource: 'arn:aws:s3:::lambda-logging-serverless-2/*'
        }
      ]
    },
    functions: lambdaConfigFiles.map(relativeLambdaConfigPath => `\${file(${relativeLambdaConfigPath})}`),
    resources: {
      Resources: {
        LambdaLoggingBucket: {
          Type: 'AWS::S3::Bucket',
          Properties: {
            BucketName: 'lambda-logging-serverless-2'
          }
        }
      }
    }
  };
}

async function getLambdaPath(fs: PromiseFsClient, lambdaDir: string, lambdaId: string): Promise<string> {
  try {
    const lambdaIdPart = lambdaId.split('-')[0];
    const lambdaPath = lambdaDir + '-' + lambdaIdPart;
    await fs.promises.stat(lambdaPath);
    return lambdaPath;
  } catch (e) {
    return lambdaDir;
  }
}

async function handleLambda(
  fs: PromiseFsClient,
  projectDir: string,
  project: RefineryProject,
  projectConfig: ProjectConfig,
  workflowState: WorkflowState,
  lambdaEvents: object[]
): Promise<string> {
  const lambda = workflowState as LambdaWorkflowState;

  const typeFolderName = getFolderName(workflowState.type);
  const typePath = Path.join(projectDir, GLOBAL_BASE_PATH, typeFolderName);
  await maybeMkdir(fs, typePath);

  const blockDir = getFolderName(lambda.name);

  // check if we have a name collision with an existing lambda
  // if so, we append the first part of the idea to the folder name
  const relativeLambdaDir = Path.join(typePath, blockDir);
  const lambdaDir = await getLambdaPath(fs, relativeLambdaDir, lambda.id);
  await maybeMkdir(fs, lambdaDir);

  const lambdaIdPart = lambda.id.split('-')[0];
  const lambdaSuffix = lambdaDir.endsWith(lambdaIdPart) ? '-' + lambdaIdPart : '';

  const blockWithSuffix = blockDir + lambdaSuffix;
  const relativePath = Path.join(typeFolderName, blockWithSuffix);

  const envVars: Record<string, string> = Object.keys(projectConfig.environment_variables).reduce((envVars, envKey) => {
    const envVar = projectConfig.environment_variables[envKey];
    return {
      ...envVars,
      [envKey]: envVar
    };
  }, {});

  console.log('file path:', Path.join(lambdaDir, 'lambda'));

  if (languageToBaseCodeLookup[lambda.language]) {
    await fs.promises.writeFile(Path.join(lambdaDir, 'lambda'), languageToBaseCodeLookup[lambda.language]);
  } else {
    await fs.promises.writeFile(Path.join(lambdaDir, 'lambda'), UNIMPLEMENTED_BASE_CODE_MESSAGE);
  }

  const serverlessFunction = createServerlessLambdaFunction(
    Path.join('..', relativePath),
    lambda,
    lambdaEvents,
    envVars
  );

  Object.values(serverlessFunction).map(p => {
    // Strip undefined values
    // @ts-ignore
    if (p.layers && p.layers.includes(undefined)) {
      p.layers = p.layers.filter(p => p !== undefined);
    }
  });
  console.log('serverlessFunction', serverlessFunction);

  const lambdaConfig = Path.join(lambdaDir, 'serverless.yaml');
  await writeConfig(fs, lambdaConfig, serverlessFunction);

  return lambdaDir;
}

function workflowStateToEvent(w: WorkflowState) {
  const sluggedName = slugify(w.name).toLowerCase();
  if (w.type === WorkflowStateType.API_ENDPOINT) {
    const apiEndpointState = w as ApiEndpointWorkflowState;
    return {
      http: {
        method: apiEndpointState.http_method,
        path: apiEndpointState.api_path
      }
    };
  }
  if (w.type === WorkflowStateType.SCHEDULE_TRIGGER) {
    const scheduledTriggerState = w as ScheduleTriggerWorkflowState;
    return {
      schedule: {
        name: sluggedName,
        rate: scheduledTriggerState.schedule_expression,
        description: scheduledTriggerState.description,
        input: scheduledTriggerState.input_string
      }
    };
  }
  if (w.type === WorkflowStateType.SNS_TOPIC) {
    return {
      sns: sluggedName
    };
  }
  if (w.type === WorkflowStateType.SQS_QUEUE) {
    // TODO Creating SQS Queues is not supported by serverless framework, so we create a topic to get similar functionality to a queue
    return {
      sns: sluggedName
    };
  }
  return undefined;
}

export async function saveProjectToServerlessFramework(
  fs: PromiseFsClient,
  dir: string,
  project: RefineryProject,
  config: ProjectConfig,
  gitURL: string
) {
  const refineryDir = Path.join(dir, GLOBAL_BASE_PATH);

  const serverlessDir = Path.join(refineryDir, SERVERLESS_CONFIG_FOLDER);
  console.log('first maybeMkdir');

  await maybeMkdir(fs, serverlessDir);

  const nodeToWorkflowState = project.workflow_states.reduce((workflowStates, w: WorkflowState) => {
    return {
      ...workflowStates,
      [w.id]: w
    };
  }, {} as Record<string, WorkflowState>);

  console.log('pre-write workflows');
  const nodeToEventTargetsLookup = project.workflow_relationships.reduce((lambdaEventNodeLookup, wr) => {
    const currentLambdaEvents = lambdaEventNodeLookup[wr.next] || [];

    console.log('pre-write workflow state', wr.node, nodeToWorkflowState[wr.node]);
    const workflowStateEvent = workflowStateToEvent(nodeToWorkflowState[wr.node]);
    if (!workflowStateEvent) {
      return lambdaEventNodeLookup;
    }

    return {
      ...lambdaEventNodeLookup,
      [wr.next]: [...currentLambdaEvents, workflowStateEvent]
    };
  }, {} as Record<string, object[]>);

  const lambdaToPathLookup = await project.workflow_states
    .filter(w => w.type === WorkflowStateType.LAMBDA)
    .reduce(async (pathLookup, w) => {
      const awaitedLookup = await pathLookup;

      console.log('pre-write lambda ', w.id, nodeToEventTargetsLookup[w.id]);
      const path = await handleLambda(fs, dir, project, config, w, nodeToEventTargetsLookup[w.id]);
      return {
        ...awaitedLookup,
        [w.id]: path
      };
    }, Promise.resolve({} as Record<string, string>));

  console.log('pre create serverless service config');
  const serverlessConfig = createServerlessServiceConfig(
    project,
    Object.keys(lambdaToPathLookup).map(lambdaId =>
      Path.join('..', Path.relative(Path.join(dir, 'refinery'), lambdaToPathLookup[lambdaId]), 'serverless.yaml')
    )
  );
  const serverlessConfigPath = Path.join(serverlessDir, 'serverless.yaml');

  console.log('pre-write config');
  await writeConfig(fs, serverlessConfigPath, serverlessConfig);

  const outputScriptsDir = Path.join(serverlessDir, 'scripts');
  console.log('pre-maybeMkdir');
  await maybeMkdir(fs, outputScriptsDir);

  const outputHandlerJs = Path.join(outputScriptsDir, 'output.js');
  console.log('pre-write outputHandlerJs');
  await fs.promises.writeFile(
    outputHandlerJs,
    `
function handler (data, serverless, options) {
  console.log('Received Stack Output', data)
}

module.exports = { handler }`
  );

  console.log('post-write outputHandlerJs');
}
