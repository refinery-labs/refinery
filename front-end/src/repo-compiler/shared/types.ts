import { SupportedLanguage, WorkflowRelationshipType } from '@/types/graph';

export type ProjectBlockLookup = {
  [index: string]: RefineryGitProjectBlock;
};

export type ProjectRelationshipLookup = {
  [index: string]: RefineryGitProjectRelationship;
};

export interface RefineryGitProjectConfig {
  name: string;
  blocks: ProjectBlockLookup;
  relationships: ProjectRelationshipLookup;
}

export interface RefineryGitProjectBlock {
  language: SupportedLanguage;
  path: string;
  config?: RefineryGitProjectBlockConfig;
}

export type BlockConfigEnvVarLookup = {
  [index: string]: string;
};

export interface RefineryGitProjectBlockConfig {
  env: BlockConfigEnvVarLookup;
}

export type RefineryGitProjectRelationship = { [key in WorkflowRelationshipType]?: string[] };
