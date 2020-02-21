export interface CyConfig {
  x: number;
  y: number;
  offsetX: number;
  offsetY: number;
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
  viewDeployment = 'viewDeployment',
  openExecutionsPane = 'openExecutionsPane',
  addDeploymentExecution = 'addDeploymentExecution',
  viewExecutionLogs = 'viewExecutionLogs',
  openCodeRunner = 'openCodeRunner',
  setCodeRunnerOutput = 'setCodeRunnerOutput'
}

export interface DemoOpenBlockModalOptions {
  nodeId: string;
}

export interface DemoTooltipAction {
  action: DemoTooltipActionType;
  options?: DemoOpenBlockModalOptions;
}

export interface DemoTooltip {
  type: TooltipType;
  visible: boolean;
  target: string;
  header: string;
  body: string;
  setup?: DemoTooltipAction;
  teardown?: DemoTooltipAction;
  config: CyConfig;
}
