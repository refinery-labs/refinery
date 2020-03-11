import { HTMLTooltip } from '@/types/demo-walkthrough-types';

export interface TooltipProps {
  step: HTMLTooltip | undefined;
  nextTooltip: () => void;
  skipTooltips: () => void;
}
