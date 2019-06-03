import {Module} from 'vuex';
import {RootState} from '../../store-types';

export enum EditBlockState {

}

export enum EditBlockGetter {

}

export enum EditBlockMutators {

}

export enum EditBlockActions {

}

export type EditBlockPaneStateKeys = {
  [key in EditBlockState]: any
}

export interface EditBlockPaneState extends EditBlockPaneStateKeys {

}

const moduleState: EditBlockPaneState = {
};

const EditBlockPaneModule: Module<EditBlockPaneState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {
  
  },
  mutations: {
  
  },
  actions: {
  
  }
};

export default EditBlockPaneModule;