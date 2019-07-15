import { BlockEnvironmentVariable } from '@/types/graph';

export interface AddSavedBlockEnvironmentVariable extends BlockEnvironmentVariable {
  valid: boolean | null;
  id: string;
  value?: string;
}
