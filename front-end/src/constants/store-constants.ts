
export enum AllProjectsMutators {
  setSearchingStatus = 'setSearchingStatus',
  setAvailableProjects = 'setAvailableProjects',
  setSearchBoxInput = 'setSearchBoxInput'
}

export enum ProjectViewMutators {
  setOpenedProject = 'setOpenedProject',
  setOpenedProjectConfig = 'setOpenedProjectConfig',
  setOpenedProjectOriginal = 'setOpenedProjectOriginal',
  setOpenedProjectConfigOriginal = 'setOpenedProjectConfigOriginal',
  selectedResource = 'selectedResource',
  isLoadingProject = 'isLoadingProject',
  isProjectBusy = 'isProjectBusy',
  markProjectDirtyStatus = 'markProjectDirtyStatus',
  setCytoscapeElements = 'setCytoscapeElements',
  setCytoscapeStyle = 'setCytoscapeStyle',
  setCytoscapeLayout = 'setCytoscapeLayout',
  setCytoscapeConfig = 'setCytoscapeConfig',
  setLeftSidebarPaneState = 'setLeftSidebarPaneState',
  setLeftSidebarPane = 'setLeftSidebarPane',
  
  // Add Block Pane
  setSelectedBlockIndex = 'setSelectedBlockIndex',
  
  // Add Transition Pane
  setAddingTransitionStatus = 'setAddingTransitionStatus',
  setAddingTransitionType = 'setAddingTransitionType',
  setValidTransitions = 'setValidTransitions'
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
  setAgreeToTermsValue = 'setAgreeToTermsValue',

  setRegistrationUsernameErrorMessage = 'setRegistrationUsernameErrorMessage',
  setRegistrationErrorMessage = 'setRegistrationErrorMessage',
  setRegistrationSuccessMessage = 'setRegistrationSuccessMessage'
}
