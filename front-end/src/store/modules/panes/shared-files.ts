import { Module } from 'vuex';
import { IfDropDownSelectionType, RootState } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';

// Enums
export enum SharedFilesMutators {}

export enum SharedFilesActions {}

// Types
export interface SharedFilesPaneState {}

// Initial State
const moduleState: SharedFilesPaneState = {};

const SharedFilesPaneModule: Module<SharedFilesPaneState, RootState> = {
  namespaced: true,
  state: deepJSONCopy(moduleState),
  getters: {},
  mutations: {},
  actions: {}
};

export default SharedFilesPaneModule;
