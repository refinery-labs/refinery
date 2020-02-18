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

export interface DemoTooltip {
  type: TooltipType;
  visible: boolean;
  target: string;
  header: string;
  body: string;
  config: CyConfig;
}
