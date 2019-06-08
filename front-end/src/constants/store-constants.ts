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

export enum ProjectViewMutators {
  setOpenedProject = 'setOpenedProject',
  setOpenedProjectConfig = 'setOpenedProjectConfig',
  setOpenedProjectOriginal = 'setOpenedProjectOriginal',
  setOpenedProjectConfigOriginal = 'setOpenedProjectConfigOriginal',

  selectedResource = 'selectedResource',
  isLoadingProject = 'isLoadingProject',
  isProjectBusy = 'isProjectBusy',
  isDeployingProject = 'isDeployingProject',

  markProjectDirtyStatus = 'markProjectDirtyStatus',
  setCytoscapeElements = 'setCytoscapeElements',
  setCytoscapeStyle = 'setCytoscapeStyle',
  setCytoscapeLayout = 'setCytoscapeLayout',
  setCytoscapeConfig = 'setCytoscapeConfig',
  setLeftSidebarPaneState = 'setLeftSidebarPaneState',
  setLeftSidebarPane = 'setLeftSidebarPane',
  setRightSidebarPane = 'setRightSidebarPane',

  // Add Block Pane
  setSelectedBlockIndex = 'setSelectedBlockIndex',

  // Add Transition Pane
  setAddingTransitionStatus = 'setAddingTransitionStatus',
  setAddingTransitionType = 'setAddingTransitionType',
  setValidTransitions = 'setValidTransitions'
}

export enum ProjectViewActions {
  openProject = 'openProject',
  updateProject = 'updateProject',
  saveProject = 'saveProject',
  deployProject = 'deployProject',
  clearSelection = 'clearSelection',
  selectNode = 'selectNode',
  selectEdge = 'selectEdge',
  completeTransitionAdd = 'completeTransitionAdd',
  openLeftSidebarPane = 'openLeftSidebarPane',
  closePane = 'closePane',
  openRightSidebarPane = 'openRightSidebarPane',
  resetProjectState = 'resetProjectState',
  addBlock = 'addBlock',
  _addBlock = '_addBlock',
  addSavedBlock = 'addSavedBlock',
  updateExistingBlock = 'updateExistingBlock',
  addTransition = 'addTransition',
  updateAvailableTransitions = 'updateAvailableTransitions',
  cancelAddingTransition = 'cancelAddingTransition',
  selectTransitionTypeToAdd = 'selectTransitionTypeToAdd'
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
  setRegistrationStripeTokenValue = 'setRegistrationStripeTokenValue',
  setAgreeToTermsValue = 'setAgreeToTermsValue',

  setRegistrationUsernameErrorMessage = 'setRegistrationUsernameErrorMessage',
  setRegistrationErrorMessage = 'setRegistrationErrorMessage',
  setRegistrationSuccessMessage = 'setRegistrationSuccessMessage'
}
