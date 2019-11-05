export enum API_ENDPOINT {
  HealthHandler = 'HealthHandler',
  GetAuthenticationStatus = 'GetAuthenticationStatus',
  NewRegistration = 'NewRegistration',
  Login = 'Login',
  Logout = 'Logout',
  GetProjectExecutionLogs = 'GetProjectExecutionLogs',
  GetProjectExecutions = 'GetProjectExecutions',
  GetProjectExecutionLogsPage = 'GetProjectExecutionLogsPage',
  GetProjectExecutionLogObjects = 'GetProjectExecutionLogObjects',
  DeployDiagram = 'DeployDiagram',
  SavedLambdaCreate = 'SavedLambdaCreate',
  SavedLambdaSearch = 'SavedLambdaSearch',
  SavedLambdaDelete = 'SavedLambdaDelete',
  RunLambda = 'RunLambda',
  GetCloudWatchLogsForLambda = 'GetCloudWatchLogsForLambda',
  UpdateEnvironmentVariables = 'UpdateEnvironmentVariables',
  CreateScheduleTrigger = 'CreateScheduleTrigger',
  RunTmpLambda = 'RunTmpLambda',
  CreateSQSQueueTrigger = 'CreateSQSQueueTrigger',
  InfraTearDown = 'InfraTearDown',
  InfraCollisionCheck = 'InfraCollisionCheck',
  SaveProject = 'SaveProject',
  RenameProject = 'RenameProject',
  SearchSavedProjects = 'SearchSavedProjects',
  GetSavedProject = 'GetSavedProject',
  DeleteSavedProject = 'DeleteSavedProject',
  GetProjectConfig = 'GetProjectConfig',
  GetLatestProjectDeployment = 'GetLatestProjectDeployment',
  DeleteDeploymentsInProject = 'DeleteDeploymentsInProject',
  GetPaymentMethods = 'GetPaymentMethods',
  DeletePaymentMethod = 'DeletePaymentMethod',
  MakePrimaryPaymentMethod = 'MakePrimaryPaymentMethod',
  AddPaymentMethod = 'AddPaymentMethod',
  GetLatestMonthBill = 'GetLatestMonthBill',
  SaveProjectConfig = 'SaveProjectConfig',
  GetBuildStatus = 'GetBuildStatus',
  StartLibraryBuild = 'StartLibraryBuild',
  GetConsoleCredentials = 'GetConsoleCredentials',
  StashStateLog = 'StashStateLog',
  CreateSavedBlock = 'CreateSavedBlock',
  SearchSavedBlocks = 'SearchSavedBlocks',
  SavedBlockStatusCheck = 'SavedBlockStatusCheck',
  CreateProjectShortlink = 'CreateProjectShortlink',
  GetProjectShortlink = 'GetProjectShortlink',
  DeleteSavedBlock = 'DeleteSavedBlock',
  GetBlockCachedInputs = 'GetBlockCachedInputs'
}

export enum HTTP_METHOD {
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
  DELETE = 'DELETE',
  OPTIONS = 'OPTIONS',
  HEAD = 'HEAD',
  PATCH = 'PATCH',
  '*' = 'ANY'
}

export interface ApiEndpointConfig {
  path: string;
  method: HTTP_METHOD;
}

export type ApiConfigMapType = { [key in API_ENDPOINT]: ApiEndpointConfig };

export const ApiConfigMap: ApiConfigMapType = {
  [API_ENDPOINT.HealthHandler]: {
    path: '/api/v1/health',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetAuthenticationStatus]: {
    path: '/api/v1/auth/me',
    method: HTTP_METHOD.GET
  },
  [API_ENDPOINT.NewRegistration]: {
    path: '/api/v1/auth/register',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.Login]: {
    path: '/api/v1/auth/login',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.Logout]: {
    path: '/api/v1/auth/logout',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.SearchSavedProjects]: {
    path: '/api/v1/projects/search',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetProjectExecutionLogs]: {
    path: '/api/v1/logs/executions/get',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetProjectExecutions]: {
    path: '/api/v1/logs/executions',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetProjectExecutionLogsPage]: {
    path: '/api/v1/logs/executions/get-contents',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetProjectExecutionLogObjects]: {
    path: '/api/v1/logs/executions/get-logs',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.DeployDiagram]: {
    path: '/api/v1/aws/deploy_diagram',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.SavedLambdaCreate]: {
    path: '/api/v1/lambdas/create',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.SavedLambdaSearch]: {
    path: '/api/v1/lambdas/search',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.SavedLambdaDelete]: {
    path: '/api/v1/lambdas/delete',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.RunLambda]: {
    path: '/api/v1/lambdas/run',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetCloudWatchLogsForLambda]: {
    path: '/api/v1/lambdas/logs',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.UpdateEnvironmentVariables]: {
    path: '/api/v1/lambdas/env_vars/update',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.CreateScheduleTrigger]: {
    path: '/api/v1/aws/create_schedule_trigger',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.RunTmpLambda]: {
    path: '/api/v1/aws/run_tmp_lambda',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.CreateSQSQueueTrigger]: {
    path: '/api/v1/aws/create_sqs_trigger',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.InfraTearDown]: {
    path: '/api/v1/aws/infra_tear_down',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.InfraCollisionCheck]: {
    path: '/api/v1/aws/infra_collision_check',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.SaveProject]: {
    path: '/api/v1/projects/save',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.RenameProject]: {
    path: '/api/v1/projects/rename',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.SaveProjectConfig]: {
    path: '/api/v1/projects/config/save',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetSavedProject]: {
    path: '/api/v1/projects/get',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.DeleteSavedProject]: {
    path: '/api/v1/projects/delete',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetProjectConfig]: {
    path: '/api/v1/projects/config/get',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetLatestProjectDeployment]: {
    path: '/api/v1/deployments/get_latest',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetPaymentMethods]: {
    path: '/api/v1/billing/creditcards/list',
    method: HTTP_METHOD.GET
  },
  [API_ENDPOINT.DeleteDeploymentsInProject]: {
    path: '/api/v1/deployments/delete_all_in_project',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.DeletePaymentMethod]: {
    path: '/api/v1/billing/creditcards/delete',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.MakePrimaryPaymentMethod]: {
    path: '/api/v1/billing/creditcards/make_primary',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.AddPaymentMethod]: {
    path: '/api/v1/billing/creditcards/add',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetLatestMonthBill]: {
    path: '/api/v1/billing/get_month_totals',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetBuildStatus]: {
    path: '/api/v1/lambdas/libraries_cache_check',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.StartLibraryBuild]: {
    path: '/api/v1/lambdas/build_libraries',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetConsoleCredentials]: {
    path: '/api/v1/iam/console_credentials',
    method: HTTP_METHOD.GET
  },
  [API_ENDPOINT.StashStateLog]: {
    path: '/api/v1/internal/log',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.CreateSavedBlock]: {
    path: '/api/v1/saved_blocks/create',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.SearchSavedBlocks]: {
    path: '/api/v1/saved_blocks/search',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.SavedBlockStatusCheck]: {
    path: '/api/v1/saved_blocks/status_check',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.CreateProjectShortlink]: {
    path: '/api/v1/project_short_link/create',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetProjectShortlink]: {
    path: '/api/v1/project_short_link/get',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.DeleteSavedBlock]: {
    path: '/api/v1/saved_blocks/delete',
    method: HTTP_METHOD.POST
  },
  [API_ENDPOINT.GetBlockCachedInputs]: {
    path: '/api/v1/transforms/get_block_inputs',
    method: HTTP_METHOD.POST
  }
};
