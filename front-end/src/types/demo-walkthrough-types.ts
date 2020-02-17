import { Mutation } from 'vuex';

export interface CyTooltip {
  id: string;
  header: string;
  body: string;
  x: number;
  y: number;
  offsetX: number;
  offsetY: number;
}

export const CY_TOOLTIP_DEFAULTS: CyTooltip = {
  id: '',
  header: '',
  body: '',
  x: 0,
  y: 0,
  offsetX: 120,
  offsetY: -50
};

export interface HTMLTooltipHeader {
  title: string;
}

export interface HTMLTooltip {
  target: string;
  header: HTMLTooltipHeader;
  content: string;
}

export enum TooltipType {
  CyTooltip = 'CyTooltip',
  HTMLTooltip = 'HTMLTooltip'
}

export interface DemoTooltip {
  type: TooltipType;
  visible: boolean;
  tooltip: CyTooltip | HTMLTooltip;
}
