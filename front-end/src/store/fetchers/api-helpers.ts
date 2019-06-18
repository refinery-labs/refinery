import {
  Execution,
  GetBuildStatusRequest,
  GetBuildStatusResponse,
  GetProjectExecutionsRequest,
  GetProjectExecutionsResponse,
  StartLibraryBuildRequest,
  StartLibraryBuildResponse
} from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import { SupportedLanguage } from '@/types/graph';

export interface libraryBuildArguments {
  language: SupportedLanguage;
  libraries: string[];
}

export type ExecutionResult = { [key: string]: Execution };

export async function getProjectExecutions(
  projectId: string,
  onResult?: (result: ExecutionResult) => void,
  token?: string
): Promise<ExecutionResult | null> {
  const executionsResponse = await makeApiRequest<GetProjectExecutionsRequest, GetProjectExecutionsResponse>(
    API_ENDPOINT.GetProjectExecutions,
    {
      project_id: projectId,
      continuation_token: token
    }
  );

  if (!executionsResponse || !executionsResponse.success || !executionsResponse.result) {
    return null;
  }

  if (onResult) {
    onResult(executionsResponse.result.executions);
  }

  if (!executionsResponse.result.continuation_token) {
    return executionsResponse.result.executions;
  }

  const additionalExecutions = await getProjectExecutions(
    projectId,
    onResult,
    executionsResponse.result.continuation_token
  );

  if (!additionalExecutions) {
    return null;
  }

  return {
    ...executionsResponse.result.executions,
    ...additionalExecutions
  };
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
