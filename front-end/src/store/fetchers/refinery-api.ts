import { HttpUtil } from '@/utils/make-request';
import {
  AddPaymentMethodRequest,
  AddPaymentMethodResponse,
  BaseApiRequest,
  BaseApiResponse,
  CreateSavedBlockRequest,
  CreateSavedBlockResponse,
  CreateScheduleTriggerRequest,
  CreateScheduleTriggerResponse,
  CreateSQSQueueTriggerRequest,
  CreateSQSQueueTriggerResponse,
  DeleteDeploymentsInProjectRequest,
  DeleteDeploymentsInProjectResponse,
  DeletePaymentMethodRequest,
  DeletePaymentMethodResponse,
  DeleteSavedBlockRequest,
  DeleteSavedBlockResponse,
  DeleteSavedProjectRequest,
  DeleteSavedProjectResponse,
  DeployDiagramRequest,
  DeployDiagramResponse,
  GetAuthenticationStatusRequest,
  GetAuthenticationStatusResponse,
  GetBuildStatusRequest,
  GetBuildStatusResponse,
  GetCloudWatchLogsForLambdaRequest,
  GetCloudWatchLogsForLambdaResponse,
  GetConsoleCredentialsRequest,
  GetConsoleCredentialsResponse,
  GetLatestMonthlyBillRequest,
  GetLatestMonthlyBillResponse,
  GetLatestProjectDeploymentRequest,
  GetLatestProjectDeploymentResponse, GetLogContentsRequest, GetLogContentsResponse,
  GetPaymentMethodsRequest,
  GetPaymentMethodsResponse,
  GetProjectConfigRequest,
  GetProjectConfigResponse,
  GetProjectExecutionLogsRequest,
  GetProjectExecutionLogsResponse,
  GetProjectExecutionsRequest,
  GetProjectExecutionsResponse,
  GetSavedProjectRequest,
  GetSavedProjectResponse,
  HealthCheckRequest,
  HealthCheckResponse,
  InfraCollisionCheckRequest,
  InfraCollisionCheckResponse,
  InfraTearDownRequest,
  InfraTearDownResponse,
  LoginRequest,
  LoginResponse,
  LogoutRequest,
  LogoutResponse,
  MakePrimaryMethodRequest,
  MakePrimaryMethodResponse,
  NewRegistrationRequest,
  NewRegistrationResponse,
  RunLambdaRequest,
  RunLambdaResponse,
  RunTmpLambdaRequest,
  RunTmpLambdaResponse,
  SavedBlockStatusCheckRequest,
  SavedBlockStatusCheckResponse,
  SavedLambdaCreateRequest,
  SavedLambdaCreateResponse,
  SavedLambdaDeleteRequest,
  SavedLambdaDeleteResponse,
  SavedLambdaSearchRequest,
  SavedLambdaSearchResponse,
  SaveProjectConfigRequest,
  SaveProjectConfigResponse,
  SaveProjectRequest,
  SaveProjectResponse,
  SearchSavedBlocksRequest,
  SearchSavedBlocksResponse,
  SearchSavedProjectsRequest,
  SearchSavedProjectsResponse,
  StartLibraryBuildRequest,
  StartLibraryBuildResponse,
  StashStateLogRequest,
  StashStateLogResponse,
  UpdateEnvironmentVariablesRequest,
  UpdateEnvironmentVariablesResponse
} from '@/types/api-types';
import { API_ENDPOINT, ApiConfigMap } from '@/constants/api-constants';

export type RefineryApiCall<TRequest extends BaseApiRequest, TResponse extends BaseApiResponse> = (
  request: TRequest
) => Promise<TResponse | null>;

export type RefineryApiMap = { [key in API_ENDPOINT]: RefineryApiCall<BaseApiRequest, BaseApiResponse> };

export interface RefineryApiTypeMap extends RefineryApiMap {}

function makeApiClient<TRequest extends BaseApiRequest, TResponse extends BaseApiResponse>(apiEndpoint: API_ENDPOINT) {
  return async <TRequest, TResponse>(request: TRequest) => {
    const config = ApiConfigMap[apiEndpoint];

    const httpResponse = await HttpUtil[config.method]<TRequest, TResponse>(
      `${process.env.VUE_APP_API_HOST}${config.path}`,
      request
    );

    if (!httpResponse.parsedBody) {
      console.error('Missing or invalid body received for request', httpResponse);
      throw new Error('Malformed API Response');
    }

    const parsedBody = httpResponse.parsedBody as unknown;

    return parsedBody as TResponse;
  };
}

export class RefineryApi implements RefineryApiTypeMap {
  [API_ENDPOINT.HealthHandler] = makeApiClient<HealthCheckRequest, HealthCheckResponse>(API_ENDPOINT.HealthHandler);
  [API_ENDPOINT.GetAuthenticationStatus] = makeApiClient<
    GetAuthenticationStatusRequest,
    GetAuthenticationStatusResponse
  >(API_ENDPOINT.GetAuthenticationStatus);
  [API_ENDPOINT.NewRegistration] = makeApiClient<NewRegistrationRequest, NewRegistrationResponse>(
    API_ENDPOINT.NewRegistration
  );
  [API_ENDPOINT.Login] = makeApiClient<LoginRequest, LoginResponse>(API_ENDPOINT.Login);
  [API_ENDPOINT.Logout] = makeApiClient<LogoutRequest, LogoutResponse>(API_ENDPOINT.Logout);
  [API_ENDPOINT.CreateSQSQueueTrigger] = makeApiClient<CreateSQSQueueTriggerRequest, CreateSQSQueueTriggerResponse>(
    API_ENDPOINT.CreateSQSQueueTrigger
  );
  [API_ENDPOINT.CreateScheduleTrigger] = makeApiClient<CreateScheduleTriggerRequest, CreateScheduleTriggerResponse>(
    API_ENDPOINT.CreateScheduleTrigger
  );
  [API_ENDPOINT.DeleteDeploymentsInProject] = makeApiClient<
    DeleteDeploymentsInProjectRequest,
    DeleteDeploymentsInProjectResponse
  >(API_ENDPOINT.DeleteDeploymentsInProject);
  [API_ENDPOINT.DeleteSavedProject] = makeApiClient<DeleteSavedProjectRequest, DeleteSavedProjectResponse>(
    API_ENDPOINT.DeleteSavedProject
  );
  [API_ENDPOINT.DeployDiagram] = makeApiClient<DeployDiagramRequest, DeployDiagramResponse>(API_ENDPOINT.DeployDiagram);
  [API_ENDPOINT.GetCloudWatchLogsForLambda] = makeApiClient<
    GetCloudWatchLogsForLambdaRequest,
    GetCloudWatchLogsForLambdaResponse
  >(API_ENDPOINT.GetCloudWatchLogsForLambda);
  [API_ENDPOINT.GetLatestProjectDeployment] = makeApiClient<
    GetLatestProjectDeploymentRequest,
    GetLatestProjectDeploymentResponse
  >(API_ENDPOINT.GetLatestProjectDeployment);
  [API_ENDPOINT.GetProjectConfig] = makeApiClient<GetProjectConfigRequest, GetProjectConfigResponse>(
    API_ENDPOINT.GetProjectConfig
  );
  [API_ENDPOINT.GetProjectExecutionLogs] = makeApiClient<
    GetProjectExecutionLogsRequest,
    GetProjectExecutionLogsResponse
  >(API_ENDPOINT.GetProjectExecutionLogs);
  [API_ENDPOINT.GetProjectExecutions] = makeApiClient<GetProjectExecutionsRequest, GetProjectExecutionsResponse>(
    API_ENDPOINT.GetProjectExecutions
  );
  [API_ENDPOINT.GetLogContents] = makeApiClient<
    GetLogContentsRequest,
    GetLogContentsResponse
    >(API_ENDPOINT.GetLogContents);
  [API_ENDPOINT.GetSavedProject] = makeApiClient<GetSavedProjectRequest, GetSavedProjectResponse>(
    API_ENDPOINT.GetSavedProject
  );
  [API_ENDPOINT.InfraCollisionCheck] = makeApiClient<InfraCollisionCheckRequest, InfraCollisionCheckResponse>(
    API_ENDPOINT.InfraCollisionCheck
  );
  [API_ENDPOINT.InfraTearDown] = makeApiClient<InfraTearDownRequest, InfraTearDownResponse>(API_ENDPOINT.InfraTearDown);
  [API_ENDPOINT.RunLambda] = makeApiClient<RunLambdaRequest, RunLambdaResponse>(API_ENDPOINT.RunLambda);
  [API_ENDPOINT.RunTmpLambda] = makeApiClient<RunTmpLambdaRequest, RunTmpLambdaResponse>(API_ENDPOINT.RunTmpLambda);
  [API_ENDPOINT.SaveProject] = makeApiClient<SaveProjectRequest, SaveProjectResponse>(API_ENDPOINT.SaveProject);
  [API_ENDPOINT.SavedLambdaCreate] = makeApiClient<SavedLambdaCreateRequest, SavedLambdaCreateResponse>(
    API_ENDPOINT.SavedLambdaCreate
  );
  [API_ENDPOINT.SavedLambdaDelete] = makeApiClient<SavedLambdaDeleteRequest, SavedLambdaDeleteResponse>(
    API_ENDPOINT.SavedLambdaDelete
  );
  [API_ENDPOINT.SavedLambdaSearch] = makeApiClient<SavedLambdaSearchRequest, SavedLambdaSearchResponse>(
    API_ENDPOINT.SavedLambdaSearch
  );
  [API_ENDPOINT.SearchSavedProjects] = makeApiClient<SearchSavedProjectsRequest, SearchSavedProjectsResponse>(
    API_ENDPOINT.SearchSavedProjects
  );
  [API_ENDPOINT.UpdateEnvironmentVariables] = makeApiClient<
    UpdateEnvironmentVariablesRequest,
    UpdateEnvironmentVariablesResponse
  >(API_ENDPOINT.UpdateEnvironmentVariables);
  [API_ENDPOINT.GetPaymentMethods] = makeApiClient<GetPaymentMethodsRequest, GetPaymentMethodsResponse>(
    API_ENDPOINT.GetPaymentMethods
  );
  [API_ENDPOINT.DeletePaymentMethod] = makeApiClient<DeletePaymentMethodRequest, DeletePaymentMethodResponse>(
    API_ENDPOINT.DeletePaymentMethod
  );
  [API_ENDPOINT.MakePrimaryPaymentMethod] = makeApiClient<MakePrimaryMethodRequest, MakePrimaryMethodResponse>(
    API_ENDPOINT.MakePrimaryPaymentMethod
  );
  [API_ENDPOINT.AddPaymentMethod] = makeApiClient<AddPaymentMethodRequest, AddPaymentMethodResponse>(
    API_ENDPOINT.AddPaymentMethod
  );
  [API_ENDPOINT.GetLatestMonthBill] = makeApiClient<GetLatestMonthlyBillRequest, GetLatestMonthlyBillResponse>(
    API_ENDPOINT.GetLatestMonthBill
  );
  [API_ENDPOINT.SaveProjectConfig] = makeApiClient<SaveProjectConfigRequest, SaveProjectConfigResponse>(
    API_ENDPOINT.SaveProjectConfig
  );
  [API_ENDPOINT.GetBuildStatus] = makeApiClient<GetBuildStatusRequest, GetBuildStatusResponse>(
    API_ENDPOINT.GetBuildStatus
  );
  [API_ENDPOINT.StartLibraryBuild] = makeApiClient<StartLibraryBuildRequest, StartLibraryBuildResponse>(
    API_ENDPOINT.StartLibraryBuild
  );
  [API_ENDPOINT.GetConsoleCredentials] = makeApiClient<GetConsoleCredentialsRequest, GetConsoleCredentialsResponse>(
    API_ENDPOINT.GetConsoleCredentials
  );
  [API_ENDPOINT.StashStateLog] = makeApiClient<StashStateLogRequest, StashStateLogResponse>(API_ENDPOINT.StashStateLog);
  [API_ENDPOINT.CreateSavedBlock] = makeApiClient<CreateSavedBlockRequest, CreateSavedBlockResponse>(
    API_ENDPOINT.CreateSavedBlock
  );
  [API_ENDPOINT.SearchSavedBlocks] = makeApiClient<SearchSavedBlocksRequest, SearchSavedBlocksResponse>(
    API_ENDPOINT.SearchSavedBlocks
  );
  [API_ENDPOINT.SavedBlockStatusCheck] = makeApiClient<SavedBlockStatusCheckRequest, SavedBlockStatusCheckResponse>(
    API_ENDPOINT.SavedBlockStatusCheck
  );
  [API_ENDPOINT.DeleteSavedBlock] = makeApiClient<DeleteSavedBlockRequest, DeleteSavedBlockResponse>(
    API_ENDPOINT.DeleteSavedBlock
  );
}

export const apiClientMap: RefineryApiTypeMap = new RefineryApi();

export const getApiClient = <T extends API_ENDPOINT>(t: T): RefineryApiMap[T] => apiClientMap[t];

export async function makeApiRequest<TReq extends BaseApiRequest, TRes extends BaseApiResponse>(
  type: API_ENDPOINT,
  request: TReq
) {
  const client = getApiClient(type);

  try {
    return (await client(request)) as TRes;
  } catch (e) {
    console.error('Error making API request', e);
    return null;
  }
}
