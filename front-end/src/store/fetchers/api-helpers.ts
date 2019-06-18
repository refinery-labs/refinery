import {
  GetBuildStatusRequest, GetBuildStatusResponse,
  GetProjectExecutionLogsRequest,
  GetProjectExecutionLogsResponse,
  GetProjectExecutionsRequest,
  GetProjectExecutionsResponse, StartLibraryBuildRequest, StartLibraryBuildResponse
} from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import { ProductionExecution, ProductionExecutionResponse } from '@/types/deployment-executions-types';
import { convertExecutionResponseToProjectExecutions } from '@/utils/project-execution-utils';
import {SupportedLanguage} from '@/types/graph';

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
    return;
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
