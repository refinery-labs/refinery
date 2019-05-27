import {HttpUtil} from '@/utils/make-request';
import {
  BaseApiRequest,
  BaseApiResponse,
  SearchSavedProjectsRequest,
  SearchSavedProjectsResponse,
  DeployDiagramResponse,
  UpdateEnvironmentVariablesRequest,
  GetProjectExecutionLogsRequest,
  GetProjectExecutionsRequest,
  CreateScheduleTriggerRequest,
  InfraCollisionCheckResponse,
  CreateScheduleTriggerResponse,
  DeployDiagramRequest,
  RunLambdaRequest,
  GetLatestProjectDeploymentRequest,
  GetSavedProjectResponse,
  InfraCollisionCheckRequest,
  SavedLambdaDeleteRequest,
  UpdateEnvironmentVariablesResponse,
  RunLambdaResponse,
  SaveProjectResponse,
  SavedLambdaCreateRequest,
  GetProjectExecutionLogsResponse,
  GetCloudWatchLogsForLambdaResponse,
  GetProjectConfigRequest,
  SaveProjectRequest,
  SavedLambdaDeleteResponse,
  GetProjectConfigResponse,
  DeleteDeploymentsInProjectRequest,
  RunTmpLambdaRequest,
  GetProjectExecutionsResponse,
  GetLatestProjectDeploymentResponse,
  RunTmpLambdaResponse,
  InfraTearDownRequest,
  DeleteSavedProjectRequest,
  InfraTearDownResponse,
  SavedLambdaSearchRequest,
  SavedLambdaSearchResponse,
  GetCloudWatchLogsForLambdaRequest,
  SavedLambdaCreateResponse,
  DeleteSavedProjectResponse,
  DeleteDeploymentsInProjectResponse,
  GetSavedProjectRequest, CreateSQSQueueTriggerRequest, CreateSQSQueueTriggerResponse
} from '@/types/api-types';
import {API_ENDPOINT, ApiConfigMap} from '@/constants/api-constants';
import {RefineryProject} from '@/types/graph';

export type RefineryApiCall<TRequest extends BaseApiRequest, TResponse extends BaseApiResponse>
  = (request: TRequest) => Promise<TResponse>;

export type RefineryApiMap = {
  [key in API_ENDPOINT]: RefineryApiCall<BaseApiRequest, BaseApiResponse>
}

export interface RefineryApiTypeMap extends RefineryApiMap {
}

function makeApiClient<TRequest extends BaseApiRequest, TResponse extends BaseApiResponse>(apiEndpoint: API_ENDPOINT) {
  return async <TRequest, TResponse>(request: TRequest) => {
    const config = ApiConfigMap[apiEndpoint];

    const httpResponse
      = await HttpUtil[config.method]<TRequest, TResponse>(`http://localhost:8002${config.path}`, request);

    if (!httpResponse.parsedBody) {
      throw new Error('Malformed API Response');
    }

    const parsedBody = httpResponse.parsedBody as unknown;

    return parsedBody as TResponse;
  };
}

export class RefineryApi implements RefineryApiTypeMap {
  [API_ENDPOINT.CreateSQSQueueTrigger] = makeApiClient<CreateSQSQueueTriggerRequest, CreateSQSQueueTriggerResponse>(API_ENDPOINT.CreateSQSQueueTrigger);
  [API_ENDPOINT.CreateScheduleTrigger] = makeApiClient<CreateScheduleTriggerRequest, CreateScheduleTriggerResponse>(API_ENDPOINT.CreateScheduleTrigger);
  [API_ENDPOINT.DeleteDeploymentsInProject] = makeApiClient<DeleteDeploymentsInProjectRequest, DeleteDeploymentsInProjectResponse>(API_ENDPOINT.DeleteDeploymentsInProject);
  [API_ENDPOINT.DeleteSavedProject] = makeApiClient<DeleteSavedProjectRequest, DeleteSavedProjectResponse>(API_ENDPOINT.DeleteSavedProject);
  [API_ENDPOINT.DeployDiagram] = makeApiClient<DeployDiagramRequest, DeployDiagramResponse>(API_ENDPOINT.DeployDiagram);
  [API_ENDPOINT.GetCloudWatchLogsForLambda] = makeApiClient<GetCloudWatchLogsForLambdaRequest, GetCloudWatchLogsForLambdaResponse>(API_ENDPOINT.GetCloudWatchLogsForLambda);
  [API_ENDPOINT.GetLatestProjectDeployment] = makeApiClient<GetLatestProjectDeploymentRequest, GetLatestProjectDeploymentResponse>(API_ENDPOINT.GetLatestProjectDeployment);
  [API_ENDPOINT.GetProjectConfig] = makeApiClient<GetProjectConfigRequest, GetProjectConfigResponse>(API_ENDPOINT.GetProjectConfig);
  [API_ENDPOINT.GetProjectExecutionLogs] = makeApiClient<GetProjectExecutionLogsRequest, GetProjectExecutionLogsResponse>(API_ENDPOINT.GetProjectExecutionLogs);
  [API_ENDPOINT.GetProjectExecutions] = makeApiClient<GetProjectExecutionsRequest, GetProjectExecutionsResponse>(API_ENDPOINT.GetProjectExecutions);
  [API_ENDPOINT.GetSavedProject] = makeApiClient<GetSavedProjectRequest, GetSavedProjectResponse>(API_ENDPOINT.GetSavedProject);
  [API_ENDPOINT.InfraCollisionCheck] = makeApiClient<InfraCollisionCheckRequest, InfraCollisionCheckResponse>(API_ENDPOINT.InfraCollisionCheck);
  [API_ENDPOINT.InfraTearDown] = makeApiClient<InfraTearDownRequest, InfraTearDownResponse>(API_ENDPOINT.InfraTearDown);
  [API_ENDPOINT.RunLambda] = makeApiClient<RunLambdaRequest, RunLambdaResponse>(API_ENDPOINT.RunLambda);
  [API_ENDPOINT.RunTmpLambda] = makeApiClient<RunTmpLambdaRequest, RunTmpLambdaResponse>(API_ENDPOINT.RunTmpLambda);
  [API_ENDPOINT.SaveProject] = makeApiClient<SaveProjectRequest, SaveProjectResponse>(API_ENDPOINT.SaveProject);
  [API_ENDPOINT.SavedLambdaCreate] = makeApiClient<SavedLambdaCreateRequest, SavedLambdaCreateResponse>(API_ENDPOINT.SavedLambdaCreate);
  [API_ENDPOINT.SavedLambdaDelete] = makeApiClient<SavedLambdaDeleteRequest, SavedLambdaDeleteResponse>(API_ENDPOINT.SavedLambdaDelete);
  [API_ENDPOINT.SavedLambdaSearch] = makeApiClient<SavedLambdaSearchRequest, SavedLambdaSearchResponse>(API_ENDPOINT.SavedLambdaSearch);
  [API_ENDPOINT.SearchSavedProjects] = makeApiClient<SearchSavedProjectsRequest, SearchSavedProjectsResponse>(API_ENDPOINT.SearchSavedProjects);
  [API_ENDPOINT.UpdateEnvironmentVariables] = makeApiClient<UpdateEnvironmentVariablesRequest, UpdateEnvironmentVariablesResponse>(API_ENDPOINT.UpdateEnvironmentVariables);
}

export const apiClientMap: RefineryApiTypeMap = new RefineryApi();

export const getApiClient = <T extends API_ENDPOINT>(t: T): RefineryApiMap[T] => apiClientMap[t];
