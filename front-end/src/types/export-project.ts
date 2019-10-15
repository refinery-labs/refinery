import { WorkflowFile, WorkflowFileLink, WorkflowRelationship, WorkflowState } from '@/types/graph';

export default interface ImportableRefineryProject {
  name: string;
  workflow_states: WorkflowState[];
  workflow_relationships: WorkflowRelationship[];
  workflow_files?: WorkflowFile[];
  workflow_file_links?: WorkflowFileLink[];
}
