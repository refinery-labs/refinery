import { Module, VuexModule } from 'vuex-module-decorators';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';

// This is the name that this will be added to the Vuex store with.
// You will need to add to the `RootState` interface if you want to access this state via `rootState` from anywhere.
const storeName = StoreType.projectSettings;

export interface ProjectSettingsState {}

export const baseState: ProjectSettingsState = {};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: storeName })
export class ProjectSettingsStore extends VuexModule<ThisType<ProjectSettingsState>, RootState>
  implements ProjectSettingsState {}
