import jsCookie from '../../lib/js-cookie';
import { VuexModule, Module, Mutation, Action, getModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';

const storeName = StoreType.settingsApp;

const cookieName = 'keyboard-mode';

export enum KeyboardEditorMode {
  standard = 'standard',
  vim = 'vim',
  emacs = 'emacs',
  sublime = 'sublime'
}

const cookieKeyboardMode = jsCookie.get(cookieName);
const savedKeyboardMode =
  cookieKeyboardMode && cookieKeyboardMode in KeyboardEditorMode && (cookieKeyboardMode as KeyboardEditorMode);

export type KeyboardModeToAceConfig = { [key in KeyboardEditorMode]: string | null };

export const keyboardMapToAceConfigMap: KeyboardModeToAceConfig = {
  [KeyboardEditorMode.standard]: null,
  [KeyboardEditorMode.vim]: 'ace/keyboard/vim',
  [KeyboardEditorMode.emacs]: 'ace/keyboard/emacs',
  [KeyboardEditorMode.sublime]: 'ace/keyboard/sublime'
};

export interface SettingsAppState {
  keyboardMode: KeyboardEditorMode;
  editBlockPaneWidth?: number;
}

export const baseState: SettingsAppState = {
  keyboardMode: savedKeyboardMode || KeyboardEditorMode.standard
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: storeName })
export class SettingsAppStore extends VuexModule<ThisType<SettingsAppState>, RootState> implements SettingsAppState {
  public keyboardMode: KeyboardEditorMode = initialState.keyboardMode;
  public editBlockPaneWidth?: number = initialState.editBlockPaneWidth;

  get keyboardModeToAceConfig() {
    return keyboardMapToAceConfigMap[this.keyboardMode];
  }

  get getEditBlockPaneWidth() {
    return this.editBlockPaneWidth !== undefined && this.editBlockPaneWidth + 'px';
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  // Note: Mutators cannot call other Mutators. If you need to do that, use an Action.
  @Mutation
  public setKeyboardMode(value: KeyboardEditorMode) {
    // Because the module is dynamic, just set this as a cookie... Screw it
    document.cookie = `${cookieName}=${value};path=/;max-age=${60 * 60 * 24 * 365}`;
    this.keyboardMode = value;
  }

  @Mutation
  public setEditBlockPaneWidth(width?: number) {
    this.editBlockPaneWidth = width;
  }
}
