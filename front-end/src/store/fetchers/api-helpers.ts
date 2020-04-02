import moment from 'moment';
import * as R from 'ramda';
import {
  CreateProjectShortlinkRequest,
  CreateProjectShortlinkResponse,
  DeleteDeploymentsInProjectRequest,
  DeleteDeploymentsInProjectResponse,
  DeployDiagramRequest,
  DeployDiagramResponse,
  DeployDiagramResponseCode,
  GetAuthenticationStatusRequest,
  GetAuthenticationStatusResponse,
  GetBuildStatusRequest,
  GetBuildStatusResponse,
  GetConsoleCredentialsRequest,
  GetConsoleCredentialsResponse,
  GetProjectExecutionLogObjectsRequest,
  GetProjectExecutionLogObjectsResponse,
  GetProjectExecutionLogsPageRequest,
  GetProjectExecutionLogsPageResponse,
  GetProjectExecutionLogsRequest,
  GetProjectExecutionLogsResponse,
  GetProjectExecutionsRequest,
  GetProjectExecutionsResponse,
  GetProjectShortlinkRequest,
  GetProjectShortlinkResponse,
  GetSavedProjectRequest,
  GetSavedProjectResponse,
  ImportProjectRepoRequest,
  ImportProjectRepoResponse,
  InfraTearDownRequest,
  InfraTearDownResponse,
  RenameProjectRequest,
  RenameProjectResponse,
  SavedBlockStatusCheckRequest,
  SavedBlockStatusCheckResponse,
  SaveProjectRequest,
  SaveProjectResponse,
  SearchSavedBlocksRequest,
  SearchSavedBlocksResponse,
  SharedBlockPublishStatus,
  StartLibraryBuildRequest,
  StartLibraryBuildResponse
} from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import {
  AdditionalBlockExecutionPageData,
  BlockExecutionGroup,
  BlockExecutionLogContentsByLogId,
  BlockExecutionLogData,
  ProductionExecutionResponse
} from '@/types/deployment-executions-types';
import { convertExecutionResponseToProjectExecutionGroup } from '@/utils/project-execution-utils';
import { RefineryProject, SupportedLanguage, WorkflowState } from '@/types/graph';
import { ProductionWorkflowState } from '@/types/production-workflow-types';
import { blockTypeToDefaultStateMapping, DEFAULT_PROJECT_CONFIG } from '@/constants/project-editor-constants';
import { unwrapProjectJson, wrapJson } from '@/utils/project-helpers';
import { ExecutionLogMetadata } from '@/types/execution-logs-types';
import { DeployProjectParams, DeployProjectResult } from '@/types/project-editor-types';
import { CURRENT_TRANSITION_SCHEMA } from '@/constants/graph-constants';
import { timeout } from '@/utils/async-utils';
import ImportableRefineryProject from '@/types/export-project';

export interface LibraryBuildArguments {
  language: SupportedLanguage;
  libraries: string[];
}

export function getDefaultOffsetTimestamp() {
  // 6 hours ago
  return moment()
    .subtract(6, 'hours')
    .unix();
}

export async function getProjectExecutions(
  project: RefineryProject,
  oldestTimestamp: number | null
): Promise<ProductionExecutionResponse | null> {
  const defaultTimestamp = getDefaultOffsetTimestamp();

  const timestampForQuery = (oldestTimestamp !== null && oldestTimestamp) || defaultTimestamp;

  const request: GetProjectExecutionsRequest = {
    project_id: project.project_id,
    // Fetch with the specified time or query by the default
    oldest_timestamp: timestampForQuery
  };

  const executionsResponse = await makeApiRequest<GetProjectExecutionsRequest, GetProjectExecutionsResponse>(
    API_ENDPOINT.GetProjectExecutions,
    request
  );

  if (!executionsResponse || !executionsResponse.success || !executionsResponse.result) {
    return null;
  }

  const convertedExecutions = convertExecutionResponseToProjectExecutionGroup(project, executionsResponse.result);

  // If we want to "load more", then this is the timestamp for where to begin loading more items.
  // TODO: We are probably "widening" the window with this method. We may need to specify a "from" timestamp too?
  // We multiply the timestamp by 1000 so that Moment understands the correct time.
  const nextTimestampToQuery = moment(timestampForQuery * 1000)
    .subtract(6, 'hours')
    .unix();

  return {
    oldestTimestamp: nextTimestampToQuery,
    executions: convertedExecutions
  };
}

async function makeRequestWithRetry<T>(
  makeRequest: () => Promise<T>,
  validationCheck: (res: T) => boolean,
  retryCount = 3
) {
  for (let i = 0; i < retryCount; i++) {
    const response = await makeRequest();

    if (validationCheck(response)) {
      return response;
    }

    await timeout(1000);
  }

  return null;
}

export async function getLogsForExecutions(
  project: RefineryProject,
  executionGroup: BlockExecutionGroup
): Promise<BlockExecutionLogData | null> {
  if (!project) {
    console.error('Tried to fetch logs without specified project');
    return null;
  }

  const makeRequest = async () =>
    await makeApiRequest<GetProjectExecutionLogsRequest, GetProjectExecutionLogsResponse>(
      API_ENDPOINT.GetProjectExecutionLogs,
      {
        arn: executionGroup.blockArn,
        execution_pipeline_id: executionGroup.executionId,
        // Subtract 300 so that we make sure to get the right 5 minute shard in Athena.
        // If this isn't a leaking abstraction, I don't know what is! -Free
        oldest_timestamp: executionGroup.timestamp - 601,
        project_id: project.project_id
      }
    );

  const response = await makeRequestWithRetry(makeRequest, response =>
    Boolean(response && response.success && response.result && response.result.results.length > 0)
  );

  if (!response) {
    console.error('Unable to retrieve execution logs.');
    return null;
  }

  // Create an object with log_id as the key
  const logs = R.indexBy(r => r.log_id, response.result.results);

  return {
    logs,
    pages: response.result.pages,
    blockId: executionGroup.blockId,
    totalExecutions: executionGroup.totalExecutionCount
  };
}

export async function getAdditionalLogsByPage(
  blockId: string,
  page: string
): Promise<AdditionalBlockExecutionPageData | null> {
  const makeRequest = async () =>
    await makeApiRequest<GetProjectExecutionLogsPageRequest, GetProjectExecutionLogsPageResponse>(
      API_ENDPOINT.GetProjectExecutionLogsPage,
      {
        id: page
      }
    );

  const response = await makeRequestWithRetry(makeRequest, response =>
    Boolean(response && response.success && response.result && response.result.results.length > 0)
  );

  if (!response) {
    console.error('Unable to retrieve more execution logs.');
    return null;
  }

  // Create an object with log_id as the key
  const logs = R.indexBy(r => r.log_id, response.result.results);

  return {
    blockId,
    logs,
    page
  };
}

export async function getContentsForLogs(
  logs: ExecutionLogMetadata[]
): Promise<BlockExecutionLogContentsByLogId | null> {
  // Nothing to fetch
  if (!logs || logs.length === 0) {
    return null;
  }

  // TODO: Add Retry logic
  const response = await makeApiRequest<GetProjectExecutionLogObjectsRequest, GetProjectExecutionLogObjectsResponse>(
    API_ENDPOINT.GetProjectExecutionLogObjects,
    {
      logs_to_fetch: logs.map(log => ({
        log_id: log.log_id,
        s3_key: log.s3_key
      }))
    }
  );

  if (!response || !response.success || !response.result || !response.result.results) {
    console.error('Unable to retrieve log contents for logs');
    return null;
  }

  const contents = response.result.results.map(result => {
    // Merge in log_id since we need it for the data store.
    return {
      ...result.log_data,
      log_id: result.log_id
    };
  });

  return R.indexBy(r => r.log_id, contents);
}

export async function checkBuildStatus(libraryBuildArgs: LibraryBuildArguments) {
  const response = await makeApiRequest<GetBuildStatusRequest, GetBuildStatusResponse>(API_ENDPOINT.GetBuildStatus, {
    libraries: libraryBuildArgs.libraries,
    language: libraryBuildArgs.language
  });

  if (!response || !response.success) {
    console.error('Unable to check library build cache: server error.');
    throw 'Server error occurred while checking library build cache!';
  }

  return response.is_already_cached;
}

export async function startLibraryBuild(libraryBuildArgs: LibraryBuildArguments) {
  // Check if we're already build this before
  const buildIsCached = await checkBuildStatus(libraryBuildArgs);

  // If so no need to kick it off
  if (buildIsCached) {
    return;
  }

  const response = await makeApiRequest<StartLibraryBuildRequest, StartLibraryBuildResponse>(
    API_ENDPOINT.StartLibraryBuild,
    {
      libraries: libraryBuildArgs.libraries,
      language: libraryBuildArgs.language
    }
  );

  if (!response || !response.success) {
    console.error('Unable kick off library build: server error.');
    throw 'Server error occurred while kicking off library build!';
  }
}

export async function teardownProject(openedDeploymentProjectId: string, states: ProductionWorkflowState[]) {
  const destroyDeploymentResult = await makeApiRequest<InfraTearDownRequest, InfraTearDownResponse>(
    API_ENDPOINT.InfraTearDown,
    {
      project_id: openedDeploymentProjectId,
      teardown_nodes: states
    }
  );

  if (!destroyDeploymentResult || !destroyDeploymentResult.success) {
    throw new Error('Server failed to handle Destroy Deployment request');
  }

  const deleteAllInProjectResult = await makeApiRequest<
    DeleteDeploymentsInProjectRequest,
    DeleteDeploymentsInProjectResponse
  >(API_ENDPOINT.DeleteDeploymentsInProject, {
    project_id: openedDeploymentProjectId
  });

  if (!deleteAllInProjectResult || !deleteAllInProjectResult.success) {
    throw new Error('Server failed to handle Delete Deployment request');
  }
}

export async function getConsoleCredentials() {
  const response = await makeApiRequest<GetConsoleCredentialsRequest, GetConsoleCredentialsResponse>(
    API_ENDPOINT.GetConsoleCredentials,
    {}
  );

  if (!response || !response.success) {
    console.error('An error occurred while obtained AWS console credentials.');
    return;
  }

  return response.console_credentials;
}

export async function checkLoginStatus() {
  const response = await makeApiRequest<GetAuthenticationStatusRequest, GetAuthenticationStatusResponse>(
    API_ENDPOINT.GetAuthenticationStatus,
    {}
  );

  if (!response) {
    console.error('Unable to get user login status');
    return null;
  }

  return response;
}
export async function importProject(json: string) {
  return await makeApiRequest<SaveProjectRequest, SaveProjectResponse>(API_ENDPOINT.SaveProject, {
    version: false,
    project_id: false,
    diagram_data: json,
    config: JSON.stringify(DEFAULT_PROJECT_CONFIG)
  });
}

export async function createProject(name: string) {
  return await importProject(JSON.stringify({ name }));
}

export async function openProject(request: GetSavedProjectRequest) {
  const projectResult = await makeApiRequest<GetSavedProjectRequest, GetSavedProjectResponse>(
    API_ENDPOINT.GetSavedProject,
    request
  );

  if (!projectResult || !projectResult.success) {
    return null;
  }

  const project = unwrapProjectJson(projectResult);

  if (!project) {
    return null;
  }

  // Ensures that we have all fields, especially if the schema changes.
  project.workflow_states = project.workflow_states.map(wfs => ({
    ...blockTypeToDefaultStateMapping[wfs.type](),
    ...wfs
  }));

  project.workflow_relationships = project.workflow_relationships.map(wr => ({
    version: CURRENT_TRANSITION_SCHEMA,
    ...wr
  }));

  return project;
}

export async function searchSavedBlocks(
  query: string,
  status: SharedBlockPublishStatus,
  language: string,
  projectId: string
) {
  const searchResult = await makeApiRequest<SearchSavedBlocksRequest, SearchSavedBlocksResponse>(
    API_ENDPOINT.SearchSavedBlocks,
    {
      search_string: query,
      share_status: status,
      language: language,
      project_id: projectId
    }
  );

  if (!searchResult || !searchResult.success) {
    return null;
  }

  return searchResult.results.reverse();
}

export async function getSavedBlockStatus(block: WorkflowState) {
  if (!block.saved_block_metadata) {
    return null;
  }

  const savedBlockId = block.saved_block_metadata.id;

  const response = await makeApiRequest<SavedBlockStatusCheckRequest, SavedBlockStatusCheckResponse>(
    API_ENDPOINT.SavedBlockStatusCheck,
    {
      block_ids: [savedBlockId]
    }
  );

  if (!response || !response.success) {
    return null;
  }

  if (!response.results || response.results.length === 0) {
    return null;
  }

  return response.results[0];
}

export async function importProjectRepo(projectId: string, projectRepo: string): Promise<RefineryProject | null> {
  const result = await makeApiRequest<ImportProjectRepoRequest, ImportProjectRepoResponse>(
    API_ENDPOINT.ImportProjectRepo,
    {
      project_id: projectId,
      project_repo: projectRepo
    }
  );

  if (!result || !result.success) {
    // TODO: raise error?
    return null;
  }

  return result.compiled_project;
}

export async function deployProject({ project, projectConfig }: DeployProjectParams): Promise<DeployProjectResult> {
  if (!project || !projectConfig) {
    console.error('Unable to deploy project, missing data');
    throw new Error('Unable to deploy project, missing data');
  }

  const projectJson = wrapJson(project);

  if (!projectJson) {
    throw new Error('Unable to send project to server.');
  }

  const response = await makeApiRequest<DeployDiagramRequest, DeployDiagramResponse>(API_ENDPOINT.DeployDiagram, {
    diagram_data: projectJson,
    project_config: projectConfig,
    project_id: project.project_id,
    project_name: project.name
  });

  if (!response || !response.success) {
    if (response && response.code && response.code == DeployDiagramResponseCode.DeploymentLockFailure) {
      throw new Error('Deployment is currently in progress for this project.');
    }
    throw new Error('Unable to create new deployment.');
  }

  if (!response.result.deployment_success) {
    const exceptions = response.result.exceptions;

    if (!exceptions || exceptions.length === 0) {
      throw new Error('Unable to create new deployment, unknown failure cause');
    }

    return exceptions;
  }

  return null;
}

export async function createShortlink(diagramData: ImportableRefineryProject): Promise<string> {
  if (!diagramData) {
    throw new Error('Missing data to send to create shortlink.');
  }

  const response = await makeApiRequest<CreateProjectShortlinkRequest, CreateProjectShortlinkResponse>(
    API_ENDPOINT.CreateProjectShortlink,
    {
      diagram_data: diagramData
    }
  );

  if (!response || !response.success) {
    throw new Error('Unable to create new deployment.');
  }

  return response.result.project_short_link_id;
}

export async function getShortlinkContents(shortlinkUrl: string): Promise<ImportableRefineryProject | null> {
  const response = await makeApiRequest<GetProjectShortlinkRequest, GetProjectShortlinkResponse>(
    API_ENDPOINT.GetProjectShortlink,
    {
      project_short_link_id: shortlinkUrl
    }
  );

  if (!response || !response.success) {
    return null;
  }

  return response.result.diagram_data;
}

/**
 * Allows you to update the name of a project.
 * @param projectId Must be a valid project ID for an existing RefineryProject
 * @param name The new name of the project
 */
export async function renameProject(projectId: string, name: string) {
  const response = await makeApiRequest<RenameProjectRequest, RenameProjectResponse>(API_ENDPOINT.RenameProject, {
    project_id: projectId,
    name: name
  });

  if (!response) {
    throw new Error('Unable to read response from server');
  }

  if (!response.success) {
    return response.msg;
  }

  return null;
}
