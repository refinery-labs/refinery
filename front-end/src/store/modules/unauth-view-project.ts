import { VuexModule, Module, Mutation, Action, getModule } from 'vuex-module-decorators';
import store from '@/store';
import { resetStoreState, signupDemoUser } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState } from '@/store/store-types';
import { AllProjectsActions, AllProjectsGetters } from '@/store/modules/all-projects';
import { ProjectViewActions, ProjectViewGetters } from '@/constants/store-constants';
import { EditBlockActions } from '@/store/modules/panes/edit-block-pane';
import { createToast } from '@/utils/toasts-utils';
import { ToastVariant } from '@/types/toasts-types';

// This is the name that this will be added to the Vuex store with.
// You will need to add to the `RootState` interface if you want to access this state via `rootState` from anywhere.
const storeName = 'unauthViewProject';

export interface UnauthViewProjectState {
  showSignupModal: boolean;
}

export const baseState: UnauthViewProjectState = {
  showSignupModal: false
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, dynamic: true, store, name: storeName })
class UnauthViewProjectStore extends VuexModule<ThisType<UnauthViewProjectState>, RootState>
  implements UnauthViewProjectState {
  public showSignupModal: boolean = initialState.showSignupModal;

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public setShowSignupModal(show: boolean) {
    this.showSignupModal = show;
  }

  @Action
  public async promptDemoModeSignup(triggerSaveIfAuthenticated: boolean) {
    // TODO: Display Demo Mode signup modal
    const signupResult = await signupDemoUser();

    // If the user is not signed in or signed up, just bail.
    if (!signupResult) {
      return;
    }

    if (triggerSaveIfAuthenticated) {
      const blockDirty = this.context.rootGetters[`project/${ProjectViewGetters.selectedBlockDirty}`];
      const canSaveProject = this.context.rootGetters[`project/${ProjectViewGetters.canSaveProject}`];

      if (blockDirty && !canSaveProject) {
        const message = 'Invalid state for project import';
        console.error(message);
        await createToast(this.context.dispatch, {
          title: 'Save Error',
          content: message,
          variant: ToastVariant.danger
        });
        return;
      }

      // If a block is "dirty", we need to save it before continuing.
      // TODO: Implement this for transitions too
      if (blockDirty && canSaveProject) {
        await this.context.dispatch(`project/editBlockPane/${EditBlockActions.saveBlock}`, null, { root: true });
      }

      await this.context.dispatch(`allProjects/${AllProjectsActions.importProjectFromDemo}`, null, { root: true });
    }
  }
}

export const UnauthViewProjectStoreModule = getModule(UnauthViewProjectStore);
