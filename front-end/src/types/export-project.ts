import { WorkflowRelationship, WorkflowState } from '@/types/graph';

export default interface ImportableRefineryProject {
  name: string;
  workflow_states: WorkflowState[];
  workflow_relationships: WorkflowRelationship[];
}
