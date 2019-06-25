import { RefineryProject } from '@/types/graph';

export interface NewProjectConfig {
  setStatus: (status: boolean) => void;
  setError: (message: string | null) => void;
  unknownError: string;
  navigateToNewProject: boolean;

  json?: string;
  name?: string;
}
