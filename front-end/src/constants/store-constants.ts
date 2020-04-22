export enum AllProjectsMutators {
  setSearchingStatus = 'setSearchingStatus',
  setAvailableProjects = 'setAvailableProjects',
  setSearchBoxInput = 'setSearchBoxInput',

  setCardStateLookup = 'setCardStateLookup',
  setCardSelectedVersion = 'setCardSelectedVersion',

  setDeleteModalVisibility = 'setDeleteModalVisibility',
  setDeleteProjectId = 'setDeleteProjectId',
  setDeleteProjectName = 'setDeleteProjectName',

  setRenameProjectId = 'setRenameProjectId',
  setRenameProjectInput = 'setRenameProjectInput',
  setRenameProjectBusy = 'setRenameProjectBusy',
  setRenameProjectError = 'setRenameProjectError',

  setNewProjectInput = 'setNewProjectInput',
  setNewProjectErrorMessage = 'setNewProjectErrorMessage',
  setNewProjectBusy = 'setNewProjectBusy',

  setUploadProjectInput = 'setUploadProjectInput',
  setUploadProjectErrorMessage = 'setUploadProjectErrorMessage',
  setUploadProjectBusy = 'setUploadProjectBusy',

  setImportProjectInput = 'setImportProjectInput',
  setImportProjectErrorMessage = 'setImportProjectErrorMessage',
  setImportProjectBusy = 'setImportProjectBusy',

  setImportProjectFromUrlContent = 'setImportProjectFromUrlContent',
  setImportProjectFromUrlError = 'setImportProjectFromUrlError',
  setImportProjectFromUrlBusy = 'setImportProjectFromUrlBusy'
}

export enum ProjectViewGetters {
  transitionAddButtonEnabled = 'transitionAddButtonEnabled',
  getValidBlockToBlockTransitions = 'getValidBlockToBlockTransitions',
  getValidMenuDisplayTransitionTypes = 'getValidMenuDisplayTransitionTypes',
  canSaveProject = 'canSaveProject',
  canDeployProject = 'canDeployProject',
  isProjectRepoSet = 'isProjectRepoSet',
  hasCodeBlockSelected = 'hasCodeBlockSelected',

  selectedBlockDirty = 'selectedBlockDirty',

  selectedTransitionDirty = 'selectedTransitionDirty',
  selectedResourceDirty = 'selectedResourceDirty',
  getValidEditMenuDisplayTransitionTypes = 'getValidEditMenuDisplayTransitionTypes',
  exportProjectJson = 'exportProjectJson',
  shareProjectUrl = 'shareProjectUrl',
  getCodeBlockIDs = 'getCodeBlockIDs'
}

export enum ProjectViewMutators {
  resetState = 'resetState',

  setOpenedProject = 'setOpenedProject',
  setOpenedProjectConfig = 'setOpenedProjectConfig',
  setOpenedProjectOriginal = 'setOpenedProjectOriginal',
  setOpenedProjectConfigOriginal = 'setOpenedProjectConfigOriginal',

  setDemoMode = 'setDemoMode',
  setIsCreatingShortlink = 'setIsCreatingShortlink',
  setShortlinkUrl = 'setShortlinkUrl',

  selectedResource = 'selectedResource',
  isLoadingProject = 'isLoadingProject',
  isProjectBusy = 'isProjectBusy',
  isSavingProject = 'isSavingProject ',
  isDeployingProject = 'isDeployingProject',

  setProjectLogLevel = 'setProjectLogLevel',
  setProjectRuntimeLanguage = 'setProjectRuntimeLanguage',
  setProjectRepo = 'setProjectRepo',

  markProjectDirtyStatus = 'markProjectDirtyStatus',
  setCytoscapeElements = 'setCytoscapeElements',
  setCytoscapeStyle = 'setCytoscapeStyle',
  setCytoscapeLayout = 'setCytoscapeLayout',
  setCytoscapeConfig = 'setCytoscapeConfig',
  setLeftSidebarPaneState = 'setLeftSidebarPaneState',
  setLeftSidebarPane = 'setLeftSidebarPane',
  setRightSidebarPane = 'setRightSidebarPane',

  setNextTooltip = 'setNextTooltip',

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
  setEditingTransitionType = 'setEditingTransitionType',

  setWarmupConcurrencyLevel = 'setWarmupConcurrencyLevel',

  setIsAddingSharedFileToCodeBlock = 'setIsAddingSharedFileToCodeBlock'
}

export enum ProjectViewActions {
  openProject = 'openProject',
  openDemo = 'openDemo',

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
  updateExistingBlock = 'updateExistingBlock',
  saveSelectedResource = 'saveSelectedResource',
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
  setProjectConfigRuntimeLanguage = 'setProjectConfigRuntimeLanguage',
  setProjectConfigRepo = 'setProjectConfigRepo',
  saveProjectConfig = 'saveProjectConfig',
  checkBuildStatus = 'checkBuildStatus',
  startLibraryBuild = 'startLibraryBuild',
  loadProjectConfig = 'loadProjectConfig',
  // Share Project
  generateShareUrl = 'generateShareUrl',
  setWarmupConcurrencyLevel = 'setWarmupConcurrencyLevel',

  // Shared Files
  addSharedFile = 'addSharedFile',
  editSharedFile = 'editSharedFile',
  openSharedFile = 'openSharedFile',
  saveSharedFile = 'saveSharedFile',
  deleteSharedFile = 'deleteSharedFile',
  addSharedFileLink = 'addSharedFileLink',
  deleteSharedFileLink = 'deleteSharedFileLink',

  setIsAddingSharedFileToCodeBlock = 'setIsAddingSharedFileToCodeBlock',
  completeAddingSharedFileToCodeBlock = 'completeAddingSharedFileToCodeBlock'
}

export enum DeploymentViewGetters {
  hasValidDeployment = 'hasValidDeployment',
  getSelectedBlock = 'getSelectedBlock'
}

export enum DeploymentViewMutators {
  resetState = 'resetState',
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
  loadDeploymentData = 'loadDeploymentData',
  destroyDeployment = 'destroyDeployment',

  clearSelection = 'clearSelection',
  selectNode = 'selectNode',
  selectEdge = 'selectEdge',
  openLeftSidebarPane = 'openLeftSidebarPane',
  closePane = 'closePane',
  openRightSidebarPane = 'openRightSidebarPane',
  resetDeploymentState = 'resetDeploymentState',
  openViewExecutionsPane = 'openViewExecutionsPane'
}

export enum SettingsMutators {
  toggleSetting = 'toggleSetting',
  toggleSettingOff = 'toggleSettingOff',
  toggleSettingOn = 'toggleSettingOn',
  changeSetting = 'changeSetting',
  setWindowWidth = 'setWindowWidth',
  setWindowHeight = 'setWindowHeight',
  setIsAWSConsoleCredentialModalVisible = 'setIsAWSConsoleCredentialModalVisible',
  setAWSConsoleCredentials = 'setAWSConsoleCredentials'
}

export enum SettingsActions {
  getAWSConsoleCredentials = 'getAWSConsoleCredentials',
  setIsAWSConsoleCredentialModalVisibleValue = 'setIsAWSConsoleCredentialModalVisibleValue'
}

export enum UserMutators {
  setAuthenticationState = 'setAuthenticationState',
  setLoginAttemptMessage = 'setLoginAttemptMessage',
  setRedirectState = 'setRedirectState',
  setIsBusyStatus = 'setIsBusyStatus',
  setLoginErrorMessage = 'setLoginErrorMessage',

  setAutoRefreshJobRunning = 'setAutoRefreshJobRunning',
  setAutoRefreshJobIterations = 'setAutoRefreshJobIterations',
  setAutoRefreshJobNonce = 'setAutoRefreshJobNonce',
  cancelAutoRefreshJob = 'cancelAutoRefreshJob',

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

export enum UserActions {
  authWithGithub = 'authWithGithub',
  fetchAuthenticationState = 'fetchAuthenticationState',
  redirectIfAuthenticated = 'redirectIfAuthenticated',
  loginUser = 'loginUser',
  registerUser = 'registerUser',

  loopWaitingLogin = 'loopWaitingLogin'
}
