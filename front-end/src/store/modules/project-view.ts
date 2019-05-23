/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import {RootState, ProjectViewState} from '@/store/store-types';

const moduleState: ProjectViewState = {
  openedProject: null,
  selectedNode: null
};

const SettingModule: Module<ProjectViewState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {
    getOpenedProject(state) {
      return state.openedProject;
    }
  },
  mutations: {
    setOpenedProject(state, project) {
      return {
        ...state,
        openedProject: project
      };
    }
  },
  actions: {}
};

export default SettingModule;
