import {
  SupportedLanguage,
  WorkflowRelationshipType,
  WorkflowState
} from '@/types/graph';
import { IfDropDownSelectionType } from '@/store/store-types';
import { SavedBlockStatusCheckResult } from '@/types/api-types';
import {ProjectExecution} from '@/types/deployment-executions-types';

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
  collapsible?: boolean;
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
  dark?: boolean;
  label?: string;
  showLabel?: boolean;
  show: boolean;
  classes?: string;
}

export interface ViewExecutionsListProps {
  projectExecutions: ProjectExecution[] | null;
  selectedProjectExecution: string | null;
  openExecutionGroup: (id: string) => void;
  showMoreExecutions: () => void;
  isBusyRefreshing: boolean;
  hasMoreExecutionsToLoad: boolean;
}

export interface CreateSavedBlockViewProps {
  modalMode: boolean;
  isBusyPublishing: boolean;

  existingBlockMetadata: SavedBlockStatusCheckResult | null;

  nameInput: string | null;
  nameInputValid: boolean | null;
  descriptionInput: string | null;
  descriptionInputValid: boolean | null;
  savedDataInput: string | null;

  publishStatus: boolean;

  setName: (s: string) => void;
  setDescription: (s: string) => void;
  setSavedDataInput: (s: string) => void;
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
