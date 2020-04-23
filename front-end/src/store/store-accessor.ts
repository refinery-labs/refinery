// This is the "store accessor":
// It initializes all the modules using a Vuex plugin (see store/drop.ts)
// In here you import all your modules, call getModule on them to turn them
// into the actual stores, and then re-export them.

import { Module, Store } from 'vuex';
import { getModule, VuexModule } from 'vuex-module-decorators';

import { CreateSavedBlockViewStore } from '@/store/modules/panes/create-saved-block-view';
import { EnvironmentVariablesEditorStore } from '@/store/modules/panes/environment-variables-editor';
import { SettingsAppStore } from '@/store/modules/settings-app';
import { SharedFilesPaneStore } from '@/store/modules/panes/shared-files';
import { EditSharedFilePaneStore } from '@/store/modules/panes/edit-shared-file';
import { CodeBlockSharedFilesPaneStore } from '@/store/modules/panes/code-block-shared-files';
import { AddSavedBlockPaneStore } from '@/store/modules/panes/add-saved-block-pane';
import { BlockLayersStore } from '@/store/modules/panes/block-layers-pane';
import { BlockLocalCodeSyncStore } from '@/store/modules/panes/block-local-code-sync';
import { RootState, StoreType } from '@/store/store-types';
import { UnauthViewProjectStore } from '@/store/modules/unauth-view-project';
import { ViewSharedFilePaneStore } from '@/store/modules/panes/view-shared-file';
import { ReadmeEditorPaneStore } from '@/store/modules/panes/readme-editor-pane';
import { DemoWalkthroughStore } from '@/store/modules/demo-walkthrough';
import { SyncProjectRepoPaneStore } from '@/store/modules/panes/sync-project-repo-pane';
import { ProjectSettingsStore } from '@/store/modules/project-settings';

declare type ConstructorOf<C> = {
  new (...args: any[]): C;
};

// To add a new decorated module:
//   1: Add a new entry in the StoreType enum
//   2: Copy-paste the `base-module-template.ts` file to your new file. Setup names as you see fit.
//   3: Add to `decoratedModules` with the name of your enum and your store as the value
//   4: Export your store below (notice suffix is "Module")
//   5: Re-assign the value to your exported store via a call to `getModule(<STORE>)`
//   6: Add your store state to `RootState`

// These are the store modules that use the "nice" syntax. They require an extra step to be loaded.
export const storeModules: { [key in StoreType]: ConstructorOf<VuexModule> & Module<any, RootState> } = {
  addSavedBlockPane: AddSavedBlockPaneStore,
  blockLayers: BlockLayersStore,
  blockLocalCodeSync: BlockLocalCodeSyncStore,
  codeBlockSharedFiles: CodeBlockSharedFilesPaneStore,
  createSavedBlockView: CreateSavedBlockViewStore,
  editSharedFile: EditSharedFilePaneStore,
  viewSharedFile: ViewSharedFilePaneStore,
  environmentVariablesEditor: EnvironmentVariablesEditorStore,
  settingsApp: SettingsAppStore,
  sharedFiles: SharedFilesPaneStore,
  unauthViewProject: UnauthViewProjectStore,
  readmeEditor: ReadmeEditorPaneStore,
  demoWalkthrough: DemoWalkthroughStore,
  syncProjectRepo: SyncProjectRepoPaneStore,
  projectSettings: ProjectSettingsStore
};

export let AddSavedBlockPaneStoreModule: AddSavedBlockPaneStore;
export let BlockLayersStoreModule: BlockLayersStore;
export let BlockLocalCodeSyncStoreModule: BlockLocalCodeSyncStore;
export let CodeBlockSharedFilesPaneModule: CodeBlockSharedFilesPaneStore;
export let CreateSavedBlockViewStoreModule: CreateSavedBlockViewStore;
export let EditSharedFilePaneModule: EditSharedFilePaneStore;
export let ViewSharedFilePaneModule: ViewSharedFilePaneStore;
export let EnvironmentVariablesEditorModule: EnvironmentVariablesEditorStore;
export let SettingsAppStoreModule: SettingsAppStore;
export let SharedFilesPaneModule: SharedFilesPaneStore;
export let UnauthViewProjectStoreModule: UnauthViewProjectStore;
export let ReadmeEditorPaneStoreModule: ReadmeEditorPaneStore;
export let DemoWalkthroughStoreModule: DemoWalkthroughStore;
export let SyncProjectRepoPaneStoreModule: SyncProjectRepoPaneStore;
export let ProjectSettingsStoreModule: ProjectSettingsStore;

// Creates the actual instances of the store for each module.
// These instances are what the app uses to reference the store in a "nice" way.
export function initializeStores(store: Store<any>): void {
  AddSavedBlockPaneStoreModule = getModule(AddSavedBlockPaneStore, store);
  BlockLayersStoreModule = getModule(BlockLayersStore, store);
  BlockLocalCodeSyncStoreModule = getModule(BlockLocalCodeSyncStore, store);
  CodeBlockSharedFilesPaneModule = getModule(CodeBlockSharedFilesPaneStore, store);
  CreateSavedBlockViewStoreModule = getModule(CreateSavedBlockViewStore, store);
  EditSharedFilePaneModule = getModule(EditSharedFilePaneStore, store);
  ViewSharedFilePaneModule = getModule(ViewSharedFilePaneStore, store);
  EnvironmentVariablesEditorModule = getModule(EnvironmentVariablesEditorStore, store);
  SettingsAppStoreModule = getModule(SettingsAppStore, store);
  SharedFilesPaneModule = getModule(SharedFilesPaneStore, store);
  UnauthViewProjectStoreModule = getModule(UnauthViewProjectStore, store);
  ReadmeEditorPaneStoreModule = getModule(ReadmeEditorPaneStore, store);
  DemoWalkthroughStoreModule = getModule(DemoWalkthroughStore, store);
  SyncProjectRepoPaneStoreModule = getModule(SyncProjectRepoPaneStore, store);
  ProjectSettingsStoreModule = getModule(ProjectSettingsStore, store);
}

// for use in 'modules' store init (see store/drop.ts), so each module
// appears as an element of the root store's state.
// (This is required!)
