import { SupportedLanguage, WorkflowRelationshipType } from '@/types/graph';
import { IfDropDownSelectionType } from '@/store/store-types';

export interface EditorProps {
  name: string;
  lang: SupportedLanguage | 'text';
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
  helperText: string | null;
  cancelModifyingTransition: () => void;
  saveModificationButtonAction: (key: WorkflowRelationshipType | null) => void;
  currentlySelectedTransitionType: WorkflowRelationshipType | null;
  hasSaveModificationButton: boolean;
  ifSelectDropdownValue: IfDropDownSelectionType | null;
  ifExpression: string | null;
  ifDropdownSelection: (dropdownSelection: string) => void;
  setIfExpression: (ifExpression: string) => void;
}

export interface LoadingContainerProps {
  [key: string]: any;
  label?: string;
  show: boolean;
}
