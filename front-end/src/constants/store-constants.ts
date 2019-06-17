export enum AllProjectsMutators {
  setSearchingStatus = 'setSearchingStatus',
  setAvailableProjects = 'setAvailableProjects',
  setSearchBoxInput = 'setSearchBoxInput',

  setDeleteModalVisibility = 'setDeleteModalVisibility',
  setDeleteProjectId = 'setDeleteProjectId',
  setDeleteProjectName = 'setDeleteProjectName',

  setNewProjectInput = 'setNewProjectInput',
  setNewProjectInputValid = 'setNewProjectInputValid',
  setNewProjectErrorMessage = 'setNewProjectErrorMessage'
}

export enum ProjectViewGetters {
  transitionAddButtonEnabled = 'transitionAddButtonEnabled',
  getValidBlockToBlockTransitions = 'getValidBlockToBlockTransitions',
  getValidMenuDisplayTransitionTypes = 'getValidMenuDisplayTransitionTypes',
  canSaveProject = 'canSaveProject',
  canDeployProject = 'canDeployProject',
  hasCodeBlockSelected = 'hasCodeBlockSelected',
  selectedResourceDirty = 'selectedResourceDirty',
  getValidEditMenuDisplayTransitionTypes = 'getValidEditMenuDisplayTransitionTypes'
}

export enum ProjectViewMutators {
  setOpenedProject = 'setOpenedProject',
  setOpenedProjectConfig = 'setOpenedProjectConfig',
  setOpenedProjectOriginal = 'setOpenedProjectOriginal',
  setOpenedProjectConfigOriginal = 'setOpenedProjectConfigOriginal',

  selectedResource = 'selectedResource',
  isLoadingProject = 'isLoadingProject',
  isProjectBusy = 'isProjectBusy',
  isSavingProject = 'isSavingProject ',
  isDeployingProject = 'isDeployingProject',

  setProjectLogLevel = 'setProjectLogLevel',

  markProjectDirtyStatus = 'markProjectDirtyStatus',
  setCytoscapeElements = 'setCytoscapeElements',
  setCytoscapeStyle = 'setCytoscapeStyle',
  setCytoscapeLayout = 'setCytoscapeLayout',
  setCytoscapeConfig = 'setCytoscapeConfig',
  setLeftSidebarPaneState = 'setLeftSidebarPaneState',
  setLeftSidebarPane = 'setLeftSidebarPane',
  setRightSidebarPane = 'setRightSidebarPane',

  // Deployment
  setLatestDeploymentState = 'setLatestDeploymentState',
  setDeploymentError = 'setDeploymentError',

  // Add Block Pane
  setSelectedBlockIndex = 'setSelectedBlockIndex',

  // Add Transition Pane
  setAddingTransitionStatus = 'setAddingTransitionStatus',
  setAddingTransitionType = 'setAddingTransitionType',
  setValidTransitions = 'setValidTransitions',
  setIfDropdownSelection = 'setIfDropdownSelection',
  setIfExpression = 'setIfExpression',

  // Edit Transition Pane
  setValidEditTransitions = 'setValidEditTransitions',
  setEditingTransitionStatus = 'setEditingTransitionStatus',
  setEditingTransitionType = 'setEditingTransitionType'
}

export enum ProjectViewActions {
  openProject = 'openProject',
  updateProject = 'updateProject',
  saveProject = 'saveProject',

  // Deployment
  deployProject = 'deployProject',
  fetchLatestDeploymentState = 'fetchLatestDeploymentState',
  showDeploymentPane = 'showDeploymentPane',
  resetDeploymentPane = 'resetDeploymentPane',

  clearSelection = 'clearSelection',
  selectNode = 'selectNode',
  selectEdge = 'selectEdge',
  completeTransitionAdd = 'completeTransitionAdd',
  openLeftSidebarPane = 'openLeftSidebarPane',
  closePane = 'closePane',
  openRightSidebarPane = 'openRightSidebarPane',
  resetProjectState = 'resetProjectState',
  addBlock = 'addBlock',
  addIndividualBlock = 'addIndividualBlock',
  addSavedBlock = 'addSavedBlock',
  updateExistingBlock = 'updateExistingBlock',
  addTransition = 'addTransition',
  updateAvailableTransitions = 'updateAvailableTransitions',
  updateAvailableEditTransitions = 'updateAvailableEditTransitions',
  cancelAddingTransition = 'cancelAddingTransition',
  selectTransitionTypeToAdd = 'selectTransitionTypeToAdd',
  deleteExistingBlock = 'deleteExistingBlock',
  deleteExistingTransition = 'deleteExistingTransition',
  changeExistingTransition = 'changeExistingTransition',
  deselectResources = 'deselectResources',
  ifDropdownSelection = 'ifDropdownSelection',
  setIfExpression = 'setIfExpression',
  selectTransitionTypeToEdit = 'selectTransitionTypeToEdit',
  cancelEditingTransition = 'cancelEditingTransition',
  resetPanelStates = 'resetPanelStates',
  setProjectConfigLoggingLevel = 'setProjectConfigLoggingLevel',
  saveProjectConfig = 'saveProjectConfig'
}

export enum DeploymentViewGetters {
  hasValidDeployment = 'hasValidDeployment',
  getSelectedBlock = 'getSelectedBlock'
}

export enum DeploymentViewMutators {
  setOpenedDeployment = 'setOpenedDeployment',

  setDestroyDeploymentModalVisibility = 'setDestroyDeploymentModalVisibility',
  setIsDestroyingDeployment = 'setIsDestroyingDeployment',

  selectedResource = 'selectedResource',
  isLoadingDeployment = 'isLoadingDeployment',

  setCytoscapeElements = 'setCytoscapeElements',
  setCytoscapeStyle = 'setCytoscapeStyle',
  setCytoscapeLayout = 'setCytoscapeLayout',
  setCytoscapeConfig = 'setCytoscapeConfig',
  setLeftSidebarPane = 'setLeftSidebarPane',
  setRightSidebarPane = 'setRightSidebarPane',

  // View Block Pane
  setSelectedBlockIndex = 'setSelectedBlockIndex'
}

export enum DeploymentViewActions {
  openDeployment = 'openDeployment',
  destroyDeployment = 'destroyDeployment',

  clearSelection = 'clearSelection',
  selectNode = 'selectNode',
  selectEdge = 'selectEdge',
  openLeftSidebarPane = 'openLeftSidebarPane',
  closePane = 'closePane',
  openRightSidebarPane = 'openRightSidebarPane',
  resetDeploymentState = 'resetDeploymentState'
}

export enum SettingsMutators {
  toggleSetting = 'toggleSetting',
  toggleSettingOff = 'toggleSettingOff',
  toggleSettingOn = 'toggleSettingOn',
  changeSetting = 'changeSetting'
}

export enum UserMutators {
  setAuthenticationState = 'setAuthenticationState',
  setLoginAttemptMessage = 'setLoginAttemptMessage',
  setRedirectState = 'setRedirectState',
  setIsBusyStatus = 'setIsBusyStatus',
  setLoginErrorMessage = 'setLoginErrorMessage',

  // Login form
  setRememberMeState = 'setRememberMeState',
  setEmailInputValue = 'setEmailInputValue',

  // Register form
  setRegisterEmailInputValue = 'setRegisterEmailInputValue',
  setRegisterNameInputValue = 'setRegisterNameInputValue',
  setRegisterPhoneInputValue = 'setRegisterPhoneInputValue',
  setRegisterOrgNameInputValue = 'setRegisterOrgNameInputValue',
  setRegistrationStripeToken = 'setRegistrationStripeToken',
  setAgreeToTermsValue = 'setAgreeToTermsValue',

  setRegistrationUsernameErrorMessage = 'setRegistrationUsernameErrorMessage',
  setRegistrationErrorMessage = 'setRegistrationErrorMessage',
  setRegistrationSuccessMessage = 'setRegistrationSuccessMessage'
}
