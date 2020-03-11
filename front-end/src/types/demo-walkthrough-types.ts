import { ExecutionStatusType } from '@/types/execution-logs-types';
import { languages } from 'monaco-editor';
import html = languages.html;
import placeholder from 'cypress/types/lodash/fp/placeholder';
import {
  BlockExecutionLogContentsByLogId,
  BlockExecutionLogData,
  ProductionExecutionResponse
} from '@/types/deployment-executions-types';

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

export interface DemoMockNetworkResponseLookup {
  blockExecutionLogData?: BlockExecutionLogData;
  blockExecutionLogContentsByLogId?: BlockExecutionLogContentsByLogId;
  getProjectExecutions?: ProductionExecutionResponse;
}

export interface CyConfig {
  blockId: string;
  x: number;
  y: number;
  offsetX: number;
  offsetY: number;
}

export interface HTMLConfig {
  htmlSelector: string;
  placement: string;
}

export const CY_CONFIG_DEFAULTS: CyConfig = {
  blockId: '',
  x: 0,
  y: 0,
  offsetX: 120,
  offsetY: -50
};

export const HTML_CONFIG_DEFAULTS: HTMLConfig = {
  htmlSelector: '',
  placement: 'top'
};

export const EMPTY_HTML_TOOLTIP: HTMLTooltip = {
  type: TooltipType.HTMLTooltip,
  header: '',
  body: '',
  visible: false,
  config: {
    htmlSelector: '',
    placement: ''
  }
};

export interface SetCodeRunnerOutputOptions {
  logs: string;
  returned_data: string;
}

export interface ExecutionLogsOptions {
  block_index: number;
  log_id: string;
  contents: {
    backpack: object;
    input_data: string;
    name: string;
    program_output: string;
    return_data: string;
  };
  data: {
    function_name: string;
    log_id: string;
    s3_key: string;
    timestamp: number;
    type: ExecutionStatusType;
  };
}

export interface AddDeploymentExecutionInfo {
  block_index: number;
  status: ExecutionStatusType;
}

export interface AddDeploymentExecutionOptions {
  executions: AddDeploymentExecutionInfo[];
}

export interface DemoTooltipAction {
  action: DemoTooltipActionType;
  options?: SetCodeRunnerOutputOptions | ExecutionLogsOptions | AddDeploymentExecutionOptions;
}

export interface DemoTooltip {
  type: TooltipType;
  visible: boolean;
  header: string;
  body: string;
  setup?: DemoTooltipAction;
  teardown?: DemoTooltipAction;
}

export interface HTMLTooltip extends DemoTooltip {
  config: HTMLConfig;
}

export interface CyTooltip extends DemoTooltip {
  config: CyConfig;
}
