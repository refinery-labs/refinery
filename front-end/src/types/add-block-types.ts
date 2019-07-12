import { SavedBlockSearchResult } from '@/types/api-types';

export interface ChosenBlock {
  block: SavedBlockSearchResult;
  blockSource: ChosenBlockSource;
}

export type ChosenBlockSource = 'public' | 'private';
