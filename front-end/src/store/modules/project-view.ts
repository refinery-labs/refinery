/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import {RootState, ProjectViewState} from '@/store/store-types';

// @ts-ignore
import simpleDataJson from '../fake-project-data/simple-data';
import {RefineryProject} from '@/types/graph';

const simpleData: RefineryProject = simpleDataJson;

const moduleState: ProjectViewState = {
  openedProject: simpleData,
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
