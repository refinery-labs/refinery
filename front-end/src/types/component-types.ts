import {
  LambdaWorkflowState,
  SupportedLanguage,
  WorkflowRelationshipType,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { IfDropDownSelectionType } from '@/store/store-types';
import { ProductionExecution } from '@/types/deployment-executions-types';
import { SavedBlockStatusCheckResult } from '@/types/api-types';

export interface EditorProps {
  name: string;
  lang: SupportedLanguage | 'text' | 'json';
  content: string;
  theme?: string;
  onChange?: (s: string) => void;
  onChangeContext?: (c: { value: string; this: any }) => void;

  // Ace Props
  readOnly?: boolean;
  wrapText?: boolean;

  // Ace is garbage and we need this
  extraClasses?: string;
}

export interface EditTransitionSelectorProps {
  readOnly: boolean;
  checkIfValidTransitionGetter: WorkflowRelationshipType[] | null;
  selectTransitionAction: (key: WorkflowRelationshipType) => void;
  newTransitionTypeSpecifiedInFlowState: WorkflowRelationshipType | null;
  cancelModifyingTransition?: () => void;
  currentlySelectedTransitionType: WorkflowRelationshipType | null;
  ifSelectDropdownValue: IfDropDownSelectionType | null;
  ifExpression: string | null;
  ifDropdownSelection: (dropdownSelection: string) => void;
  setIfExpression: (ifExpression: string) => void;
}

export interface LoadingContainerProps {
  [key: string]: any;
  label?: string;
  showLabel?: boolean;
  show: boolean;
}

export interface ViewExecutionsListProps {
  projectExecutions: ProductionExecution[] | null;
  selectedExecutionGroup: string | null;
  openExecutionGroup: (id: string) => void;
  showMoreExecutions: () => void;
  isBusyRefreshing: boolean;
  hasMoreExecutionsToLoad: boolean;
}

export interface CreateSavedBlockViewProps {
  modalMode: boolean;

  existingBlockMetadata: SavedBlockStatusCheckResult | null;

  nameInput: string | null;
  nameInputValid: boolean | null;
  descriptionInput: string | null;
  descriptionInputValid: boolean | null;

  publishStatus: boolean;

  setName: (s: string) => void;
  setDescription: (s: string) => void;
  setPublishStatus: (s: boolean) => void;

  publishBlock: () => void;

  modalVisibility?: boolean;
  setModalVisibility?: (b: boolean) => void;
}

export interface EditBlockPaneProps {
  selectedNode: WorkflowState;
  selectedNodeMetadata: SavedBlockStatusCheckResult | null;
  readOnly: boolean;
}

export interface SavedBlockSearchResult {
  id: string;
  description: string;
  name: string;
  type: WorkflowStateType;
  block_object: WorkflowState;
  version: number;
  timestamp: number;
}
