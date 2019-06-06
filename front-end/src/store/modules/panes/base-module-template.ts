import {Module} from 'vuex';
import {RootState} from '../../store-types';

// Enums
export enum BaseBlockMutators {

}

export enum BaseBlockActions {

}

// Types
export interface BaseBlockPaneState {

}

// Initial State
const moduleState: BaseBlockPaneState = {
};

const BaseBlockPaneModule: Module<BaseBlockPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {
  
  },
  mutations: {
  
  },
  actions: {
  
  }
};

export default BaseBlockPaneModule;