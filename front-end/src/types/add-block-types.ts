import { SavedBlockSearchResult } from '@/types/api-types';
import { WorkflowState } from '@/types/graph';

export interface ChosenBlock {
  block: SavedBlockSearchResult;
  blockSource: ChosenBlockSource;
}

export type ChosenBlockSource = 'public' | 'private';
