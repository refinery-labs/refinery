
export enum AllProjectsMutators {
  setSearchingStatus = 'setSearchingStatus',
  setAvailableProjects = 'setAvailableProjects',
  setSearchBoxInput = 'setSearchBoxInput'
}

export enum ProjectViewMutators {
  setOpenedProject = 'setOpenedProject',
  selectedResource = 'selectedResource',
  isLoadingProject = 'isLoadingProject',
  setCytoscapeElements = 'setCytoscapeElements',
  setCytoscapeStyle = 'setCytoscapeStyle',
  setCytoscapeLayout = 'setCytoscapeLayout',
  setCytoscapeConfig = 'setCytoscapeConfig'
}

export enum SettingsMutators {
  toggleSetting = 'toggleSetting',
  toggleSettingOff = 'toggleSettingOff',
  toggleSettingOn = 'toggleSettingOn',
  changeSetting = 'changeSetting'
}
