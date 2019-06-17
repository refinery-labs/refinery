import { Execution, GetProjectExecutionsRequest, GetProjectExecutionsResponse } from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';

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
