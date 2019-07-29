import { VuexModule, Module, Mutation, Action, getModule } from 'vuex-module-decorators';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState } from '@/store/store-types';
import { AllProjectsGetters } from '@/store/modules/all-projects';
import { generateCytoscapeElements, generateCytoscapeStyle } from '@/lib/refinery-to-cytoscript-converter';
import { getNodeDataById, getTransitionDataById } from '@/utils/project-helpers';

// This is the name that this will be added to the Vuex store with.
// You will need to add to the `RootState` interface if you want to access this state via `rootState` from anywhere.
const storeName = 'unauthViewProject';

export interface UnauthViewProjectState {
  selectedElement: string | null;
  showSignupModal: boolean;
}

export const baseState: UnauthViewProjectState = {
  selectedElement: null,
  showSignupModal: false
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, dynamic: true, store, name: storeName })
class UnauthViewProjectStore extends VuexModule<ThisType<UnauthViewProjectState>, RootState>
  implements UnauthViewProjectState {
  public selectedElement: string | null = initialState.selectedElement;

  public showSignupModal: boolean = initialState.showSignupModal;

  get currentProject() {
    return this.context.rootGetters[`allProjects/${AllProjectsGetters.importProjectFromUrlJson}`];
  }

  get cytoscapeElements() {
    const projectJson = this.currentProject;

    if (!projectJson) {
      return null;
    }

    return generateCytoscapeElements(projectJson);
  }

  get cytoscapeStyle() {
    return generateCytoscapeStyle();
  }

  get selectedNode() {
    const project = this.currentProject;

    if (!project || !this.selectedElement) {
      return null;
    }

    return getNodeDataById(project, this.selectedElement);
  }

  get selectedEdge() {
    const project = this.currentProject;

    if (!project || !this.selectedElement) {
      return null;
    }

    return getTransitionDataById(project, this.selectedElement);
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public setSelectedElement(value: string | null) {
    this.selectedElement = value;
  }

  @Mutation
  public setShowSignupModal(show: boolean) {
    this.showSignupModal = show;
  }

  // This is able to call a Mutator via the `this` context because of magic.
  @Action
  public setExampleViaAction(value: string) {
    // this.setExample(value);
  }
}

export const UnauthViewProjectStoreModule = getModule(UnauthViewProjectStore);
