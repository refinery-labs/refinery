import { ProjectConfig, RefineryProject, WorkflowRelationshipType, WorkflowState } from '@/types/graph';
import { LayoutOptions } from 'cytoscape';
import cytoscape from '@/components/CytoscapeGraph';
import {
  ConsoleCredentials,
  GetLatestProjectDeploymentResponse,
  SearchSavedProjectsResult,
  TrialInformation
} from '@/types/api-types';
import { DeployProjectResult, LeftSidebarPaneState, SIDEBAR_PANE } from '@/types/project-editor-types';
import { ValidTransitionConfig } from '@/constants/project-editor-constants';
import { EditBlockPaneState } from '@/store/modules/panes/edit-block-pane';
import { ProductionDeploymentRefineryProject } from '@/types/production-workflow-types';
import { BillingPaneState } from '@/store/modules/billing';
import { RunLambdaState } from '@/store/modules/run-lambda';
import { ToastPaneState } from '@/store/modules/toasts';
import { ViewBlockPaneState } from '@/store/modules/panes/view-block-pane';
import { EditTransitionPaneState } from '@/store/modules/panes/edit-transition-pane';
import { DeploymentExecutionsPaneState } from '@/store/modules/panes/deployment-executions-pane';
import { CyElements, CyStyle } from '@/types/cytoscape-types';
import { EnvironmentVariablesEditorPaneState } from '@/store/modules/panes/environment-variables-editor';
import { AddSavedBlockPaneState } from '@/store/modules/panes/add-saved-block-pane';
import { CreateSavedBlockViewState } from '@/store/modules/panes/create-saved-block-view';
import { SettingsAppState } from '@/store/modules/settings-app';
import { BlockLayersState } from '@/store/modules/panes/block-layers-pane';
import { BlockLocalCodeSyncState } from '@/store/modules/panes/block-local-code-sync';
import { ProjectCardStateLookup } from '@/types/all-project-types';
import { SharedFilesPaneState } from '@/store/modules/panes/shared-files';
import { EditSharedFilePaneState } from '@/store/modules/panes/edit-shared-file';
import EditSharedFileLinksPane from '@/components/ProjectEditor/SharedFileLinks';

export interface RootState {
  addSavedBlockPane: AddSavedBlockPaneState;
  blockLayers: BlockLayersState;
  blockLocalCodeSync: BlockLocalCodeSyncState;
  createSavedBlockView: CreateSavedBlockViewState;
  setting: UserInterfaceState;
  deployment: DeploymentViewState;
  deploymentExecutions: DeploymentExecutionsPaneState;
  environmentVariablesEditor: EnvironmentVariablesEditorPaneState;
  viewBlock: ViewBlockPaneState;
  project: ProjectViewState;
  allProjects: AllProjectsState;
  runLambda: RunLambdaState;
  settingsApp: SettingsAppState;
  toasts: ToastPaneState;
  user: UserState;
  billing: BillingPaneState;
  websocket: WebsocketState;
  sharedFiles: SharedFilesPaneState;
  editSharedFile: EditSharedFilePaneState;
  editSharedFileLinks: EditSharedFileLinksPane;
}

export enum UserInterfaceSettings {
  isFixed = 'isFixed',
  isGlobalNavCollapsed = 'isGlobalNavCollapsed',
  isGlobalNavClosing = 'isGlobalNavClosing',
  isSidebarCollapsed = 'isSidebarCollapsed',
  isBoxed = 'isBoxed',
  isFloat = 'isFloat',
  asideHover = 'asideHover',
  asideScrollbar = 'asideScrollbar',
  isCollapsedText = 'isCollapsedText',
  offsidebarOpen = 'offsidebarOpen',
  asideToggled = 'asideToggled',
  showUserBlock = 'showUserBlock',
  horizontal = 'horizontal',
  useFullLayout = 'useFullLayout',
  hiddenFooter = 'hiddenFooter',

  windowWidth = 'windowWidth',
  windowHeight = 'windowHeight',

  isAWSConsoleCredentialModalVisible = 'isAWSConsoleCredentialModalVisible',
  AWSConsoleCredentials = 'AWSConsoleCredentials'
}

export interface UserInterfaceState {
  /* Layout fixed. Scroll content only */
  [UserInterfaceSettings.isFixed]?: boolean;
  /* Global Nav collapsed */
  [UserInterfaceSettings.isGlobalNavCollapsed]?: boolean;
  /* Global Nav closing, fires when nav is closed */
  [UserInterfaceSettings.isGlobalNavClosing]?: boolean;
  /* Sidebar collapsed */
  [UserInterfaceSettings.isSidebarCollapsed]?: boolean;
  /* Boxed layout */
  [UserInterfaceSettings.isBoxed]?: boolean;
  /* Floating sidebar */
  [UserInterfaceSettings.isFloat]?: boolean;
  /* Sidebar show menu on hover only */
  [UserInterfaceSettings.asideHover]?: boolean;
  /* Show sidebar scrollbar (dont' hide it) */
  [UserInterfaceSettings.asideScrollbar]?: boolean;
  /* Sidebar collapsed with big icons and text */
  [UserInterfaceSettings.isCollapsedText]?: boolean;
  /* Toggle for the offsidebar */
  [UserInterfaceSettings.offsidebarOpen]?: boolean;
  /* Toggle for the sidebar offcanvas (mobile) */
  [UserInterfaceSettings.asideToggled]?: boolean;
  /* Toggle for the sidebar user block */
  [UserInterfaceSettings.showUserBlock]?: boolean;
  /* Enables layout horizontal */
  [UserInterfaceSettings.horizontal]?: boolean;
  /* Full size layout */
  [UserInterfaceSettings.useFullLayout]?: boolean;
  /* Hide footer */
  [UserInterfaceSettings.hiddenFooter]?: boolean;

  /* Used to get the current size of the page */
  [UserInterfaceSettings.windowWidth]?: number;
  [UserInterfaceSettings.windowHeight]?: number;

  /* Boolean to display the AWS console credentials */
  [UserInterfaceSettings.isAWSConsoleCredentialModalVisible]: boolean;
  /* AWS console credentials */
  [UserInterfaceSettings.AWSConsoleCredentials]: ConsoleCredentials | null;
}

export interface AvailableTransition {
  valid: boolean;
  transitionConfig: ValidTransitionConfig;
  fromNode: WorkflowState;
  toNode: WorkflowState;
  simple: boolean;
}

export interface AvailableTransitionsByType {
  simple: AvailableTransition[];
  complex: AvailableTransition[];
}

export interface ProjectViewState {
  // Submodules
  editBlockPane?: EditBlockPaneState;
  editTransitionPane?: EditTransitionPaneState;

  // Project State
  openedProject: RefineryProject | null;
  openedProjectConfig: ProjectConfig | null;

  // Disgusting backup copies so that we can revert or whatever later
  openedProjectOriginal: RefineryProject | null;
  openedProjectConfigOriginal: ProjectConfig | null;

  isInDemoMode: boolean;
  isCreatingShortlink: boolean;
  shortlinkUrl: string | null;

  isLoadingProject: boolean;
  isProjectBusy: boolean;
  isSavingProject: boolean;
  isDeployingProject: boolean;
  hasProjectBeenModified: boolean;

  leftSidebarPaneState: LeftSidebarPaneState;
  activeLeftSidebarPane: SIDEBAR_PANE | null;
  activeRightSidebarPane: SIDEBAR_PANE | null;

  // Deployment State
  latestDeploymentState: GetLatestProjectDeploymentResponse | null;
  deploymentError: DeployProjectResult;

  // Shared Graph State
  selectedResource: string | null;
  // If this is "null" then it enables all elements
  enabledGraphElements: string[] | null;

  // Cytoscape Specific state
  cytoscapeElements: CyElements | null;
  cytoscapeStyle: CyStyle | null;
  cytoscapeLayoutOptions: LayoutOptions | null;
  cytoscapeConfig: cytoscape.CytoscapeOptions | null;

  // Add Block Pane
  selectedBlockIndex: number | null;

  // Add Transition Pane
  isAddingTransitionCurrently: boolean;
  newTransitionTypeSpecifiedInAddFlow: WorkflowRelationshipType | null;
  availableTransitions: AvailableTransitionsByType | null;
  ifSelectDropdownValue: IfDropDownSelectionType | null;
  ifExpression: string;

  // Edit Transition Pane
  availableEditTransitions: AvailableTransitionsByType | null;
  isEditingTransitionCurrently: boolean;
  newTransitionTypeSpecifiedInEditFlow: WorkflowRelationshipType | null;
}

export enum IfDropDownSelectionType {
  EQUALS_VALUE = 'EQUALS_VALUE',
  NOT_EQUALS_VALUE = 'NOT_EQUALS_VALUE',
  EQUALS_TRUE = 'EQUALS_TRUE',
  EQUALS_FALSE = 'EQUALS_FALSE',
  CUSTOM_CONDITIONAL = 'CUSTOM_CONDITIONAL',
  DEFAULT = 'DEFAULT'
}

export type IfDropdownSelectionKeys = { [key in IfDropDownSelectionType]: string };

export const IfDropdownSelectionExpressionValues: IfDropdownSelectionKeys = {
  [IfDropDownSelectionType.DEFAULT]: 'return_data == "SOME_STRING"',
  [IfDropDownSelectionType.EQUALS_VALUE]: 'return_data == "SOME_STRING"',
  [IfDropDownSelectionType.NOT_EQUALS_VALUE]: 'return_data != "SOME_STRING"',
  [IfDropDownSelectionType.EQUALS_TRUE]: 'return_data == True',
  [IfDropDownSelectionType.EQUALS_FALSE]: 'return_data == False',
  [IfDropDownSelectionType.CUSTOM_CONDITIONAL]: '"test" in return_data'
};

export interface AllProjectsState {
  availableProjects: SearchSavedProjectsResult[];
  searchBoxText: string;
  isSearching: boolean;

  cardStateByProjectId: ProjectCardStateLookup;

  deleteModalVisible: boolean;
  deleteProjectId: string | null;
  deleteProjectName: string | null;

  renameProjectId: string | null;
  renameProjectInput: string | null;
  renameProjectBusy: boolean;
  renameProjectError: string | null;

  newProjectInput: string | null;
  newProjectErrorMessage: string | null;
  newProjectBusy: boolean;

  uploadProjectInput: string | null;
  uploadProjectErrorMessage: string | null;
  uploadProjectBusy: boolean;

  importProjectInput: string | null;
  importProjectErrorMessage: string | null;
  importProjectBusy: boolean;

  importProjectFromUrlContent: string | null;
  importProjectFromUrlError: string | null;
  importProjectFromUrlBusy: boolean;
}

export interface DeploymentViewState {
  // Deployment State
  openedDeployment: ProductionDeploymentRefineryProject | null;
  openedDeploymentId: string | null;
  openedDeploymentProjectId: string | null;
  openedDeploymentTimestamp: number | null;

  destroyModalVisible: boolean;
  isDestroyingDeployment: boolean;

  isLoadingDeployment: boolean;

  activeLeftSidebarPane: SIDEBAR_PANE | null;
  activeRightSidebarPane: SIDEBAR_PANE | null;

  // Deployment State
  latestDeploymentState: GetLatestProjectDeploymentResponse | null;
  deploymentError: string | null;

  // Shared Graph State
  selectedResource: string | null;
  // If this is "null" then it enables all elements
  enabledGraphElements: string[] | null;

  // Cytoscape Specific state
  cytoscapeElements: CyElements | null;
  cytoscapeStyle: CyStyle | null;
  cytoscapeLayoutOptions: LayoutOptions | null;
  cytoscapeConfig: cytoscape.CytoscapeOptions | null;

  // View Block Pane
  selectedBlockIndex: number | null;
}

export interface UserState {
  // Server populated data
  authenticated: boolean;
  name: string | null;
  email: string | null;
  permissionLevel: string | null;
  trialInformation: TrialInformation | null;
  intercomUserHmac: string | null;

  // State about the login process
  redirectState: string | null;
  loginAttemptMessage: string | null;
  loginErrorMessage: string | null;
  isBusy: boolean;

  autoRefreshJobRunning: boolean;
  autoRefreshJobIterations: number;
  autoRefreshJobNonce: string | null;

  // Local data
  rememberMeToggled: boolean;
  loginEmailInput: string;

  loginEmailInputValid: boolean | null;

  // Registration page data
  registrationEmailInput: string;
  registrationNameInput: string;
  registrationPhoneInput: string;
  registrationOrgNameInput: string;
  registrationStripeToken: string;
  termsAndConditionsAgreed: boolean;

  registrationEmailErrorMessage: string | null;
  registrationErrorMessage: string | null;
  registrationSuccessMessage: string | null;

  registrationEmailInputValid: boolean | null;
  registrationNameInputValid: boolean | null;
  registrationOrgNameInputValid: boolean | null;
  registrationPaymentCardInputValid: boolean | null;
  termsAndConditionsAgreedValid: boolean | null;
}

export interface WebsocketState {}
