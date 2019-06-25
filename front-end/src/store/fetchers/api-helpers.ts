import {
  DeleteDeploymentsInProjectRequest,
  DeleteDeploymentsInProjectResponse,
  GetAuthenticationStatusRequest,
  GetAuthenticationStatusResponse,
  GetBuildStatusRequest,
  GetBuildStatusResponse,
  GetConsoleCredentialsRequest,
  GetConsoleCredentialsResponse,
  GetProjectExecutionLogsRequest,
  GetProjectExecutionLogsResponse,
  GetProjectExecutionsRequest,
  GetProjectExecutionsResponse,
  InfraTearDownRequest,
  InfraTearDownResponse,
  SaveProjectRequest,
  SaveProjectResponse,
  StartLibraryBuildRequest,
  StartLibraryBuildResponse
} from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import { ProductionExecution, ProductionExecutionResponse } from '@/types/deployment-executions-types';
import { convertExecutionResponseToProjectExecutions } from '@/utils/project-execution-utils';
import { SupportedLanguage, WorkflowState } from '@/types/graph';
import { ProductionWorkflowState } from '@/types/production-workflow-types';
import { DEFAULT_PROJECT_CONFIG } from '@/constants/project-editor-constants';
import { AllProjectsMutators } from '@/constants/store-constants';

export interface libraryBuildArguments {
  language: SupportedLanguage;
  libraries: string[];
}

export async function getProjectExecutions(
  projectId: string,
  token: string | null
): Promise<ProductionExecutionResponse | null> {
  const request: GetProjectExecutionsRequest = {
    project_id: projectId
  };

  // Pass the token if we have one
  if (token) {
    request.continuation_token = token;
  }

  const executionsResponse = await makeApiRequest<GetProjectExecutionsRequest, GetProjectExecutionsResponse>(
    API_ENDPOINT.GetProjectExecutions,
    request
  );

  if (
    !executionsResponse ||
    !executionsResponse.success ||
    !executionsResponse.result ||
    !executionsResponse.result.executions
  ) {
    return null;
  }

  const convertedExecutions = convertExecutionResponseToProjectExecutions(executionsResponse.result.executions);

  return {
    continuationToken: executionsResponse.result.continuation_token,
    executions: convertedExecutions
  };
}

export async function getLogsForExecutions(execution: ProductionExecution) {
  const response = await makeApiRequest<GetProjectExecutionLogsRequest, GetProjectExecutionLogsResponse>(
    API_ENDPOINT.GetProjectExecutionLogs,
    {
      logs: execution.logs
    }
  );

  if (!response || !response.success || !response.result) {
    console.error('Unable to retrieve execution logs.');
    return null;
  }

  return response.result;
}

export async function checkBuildStatus(libraryBuildArgs: libraryBuildArguments) {
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

export async function startLibraryBuild(libraryBuildArgs: libraryBuildArguments) {
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
