export enum API_ENDPOINT {
  HealthHandler = 'HealthHandler',
  GetAuthenticationStatus = 'GetAuthenticationStatus',
  NewRegistration = 'NewRegistration',
  Login = 'Login',
  Logout = 'Logout',
  GetProjectExecutionLogs = 'GetProjectExecutionLogs',
  GetProjectExecutions = 'GetProjectExecutions',
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
  SaveProjectConfig = 'SaveProjectConfig'
}

export enum HTTP_METHOD {
  GET = 'GET',
  POST = 'POST',
  PUT = 'PUT',
  DELETE = 'DELETE',
  OPTIONS = 'OPTIONS',
  HEAD = 'HEAD',
  PATCH = 'PATCH'
  // '*' = '*' // Technically supported by AWS but the cross-over to our actually API fetch() breaks this.
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
  }
};
