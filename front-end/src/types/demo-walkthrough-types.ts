import { ExecutionStatusType } from '@/types/execution-logs-types';

export interface CyConfig {
  x: number;
  y: number;
  offsetX: number;
  offsetY: number;
}

export interface HTMLConfig {
  placement: string;
}

export const CY_CONFIG_DEFAULTS: CyConfig = {
  x: 0,
  y: 0,
  offsetX: 120,
  offsetY: -50
};

export enum TooltipType {
  CyTooltip = 'CyTooltip',
  HTMLTooltip = 'HTMLTooltip'
}

export enum DemoTooltipActionType {
  openBlockEditorPane = 'openBlockEditorPane',
  closeBlockEditorPane = 'closeBlockEditorPane',
  addDeploymentExecution = 'addDeploymentExecution',
  viewDeployment = 'viewDeployment',
  openExecutionsPane = 'openExecutionsPane',
  viewExecutionLogs = 'viewExecutionLogs',
  openCodeRunner = 'openCodeRunner',
  setCodeRunnerOutput = 'setCodeRunnerOutput',
  closeEditPane = 'closeEditPane',
  closeOpenPanes = 'closeOpenPanes',
  promptUserSignup = 'promptUserSignup'
}

export interface SetCodeRunnerOutputOptions {
  logs: string;
  returned_data: string;
}

export interface ViewExecutionLogsOptions {
  backpack: object;
  input_data: string;
  name: string;
  program_output: string;
  return_data: string;
}

export interface AddDeploymentExecutionInfo {
  blockIndex: number;
  status: ExecutionStatusType;
}

export interface AddDeploymentExecutionOptions {
  executions: AddDeploymentExecutionInfo[];
}

export interface DemoTooltipAction {
  action: DemoTooltipActionType;
  options?: SetCodeRunnerOutputOptions | ViewExecutionLogsOptions | AddDeploymentExecutionOptions;
}

export interface DemoTooltip {
  type: TooltipType;
  visible: boolean;
  target: string;
  header: string;
  body: string;
  setup?: DemoTooltipAction;
  teardown?: DemoTooltipAction;
  config?: CyConfig | HTMLConfig;
}
