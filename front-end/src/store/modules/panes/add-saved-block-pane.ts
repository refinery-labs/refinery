import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import store from '@/store/index';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState } from '@/store/store-types';
import { WorkflowState, WorkflowStateType } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { SIDEBAR_PANE } from '@/types/project-editor-types';
import { searchSavedBlocks } from '@/store/fetchers/api-helpers';
import { SharedBlockPublishStatus } from '@/types/api-types';
import { AddBlockArguments } from '@/store/modules/project-view';

const storeName = 'addSavedBlockPane';

export interface AddSavedBlockPaneState {
  isBusySearching: boolean;

  searchInput: string;

  searchPrivateToggleValue: boolean;
  searchPublishedToggleValue: boolean;

  searchResultsPrivate: SavedBlockSearchResult[];
  searchResultsPublished: SavedBlockSearchResult[];
}

export const baseState: AddSavedBlockPaneState = {
  isBusySearching: false,

  searchInput: '',

  searchPrivateToggleValue: true,
  searchPublishedToggleValue: true,

  searchResultsPrivate: [],
  searchResultsPublished: []
};

export interface SavedBlockSearchResult {
  id: string;
  description: string;
  name: string;
  type: WorkflowStateType;
  block_object: WorkflowState;
  version: number;
  timestamp: number;
}

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class AddSavedBlockPaneStore extends VuexModule<ThisType<AddSavedBlockPaneState>, RootState>
  implements AddSavedBlockPaneState {
  public isBusySearching: boolean = initialState.isBusySearching;

  public searchInput: string = initialState.searchInput;

  public searchPrivateToggleValue: boolean = initialState.searchPrivateToggleValue;
  public searchPublishedToggleValue: boolean = initialState.searchPublishedToggleValue;

  public searchResultsPrivate: SavedBlockSearchResult[] = initialState.searchResultsPrivate;
  public searchResultsPublished: SavedBlockSearchResult[] = initialState.searchResultsPublished;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setSearchInputValue(value: string) {
    this.searchInput = value;
  }

  @Mutation
  public setSearchResultsPrivate(results: SavedBlockSearchResult[]) {
    this.searchResultsPrivate = results;
  }

  @Mutation
  public setSearchResultsPublished(results: SavedBlockSearchResult[]) {
    this.searchResultsPublished = results;
  }

  @Action
  public async searchSavedBlocksWithPublishStatus(status: SharedBlockPublishStatus) {
    const result = await searchSavedBlocks(this.searchInput, status);

    if (!result) {
      console.error('Unable to perform saved block search, server did not yield a response');
      return;
    }

    if (status === SharedBlockPublishStatus.PRIVATE) {
      this.setSearchResultsPrivate(result);
      return;
    }

    if (status === SharedBlockPublishStatus.PUBLISHED) {
      this.setSearchResultsPublished(result);
      return;
    }

    console.error('Unknown block publish status to set response value for');
  }

  @Action
  public async searchSavedBlocks() {
    // this.isBusySearching = true;

    // We push all jobs to this array of promises and then we await them below
    const searchJobs = [];

    if (this.searchPrivateToggleValue) {
      searchJobs.push(this.searchSavedBlocksWithPublishStatus(SharedBlockPublishStatus.PRIVATE));
    }

    if (this.searchPublishedToggleValue) {
      searchJobs.push(this.searchSavedBlocksWithPublishStatus(SharedBlockPublishStatus.PUBLISHED));
    }

    await Promise.all(searchJobs);

    // this.isBusySearching = false;
  }

  @Action
  public async addChosenBlock(id: string) {
    const searchMatchFn = (result: SavedBlockSearchResult) => result.id === id;

    const matches = [
      ...this.searchResultsPrivate.filter(searchMatchFn),
      ...this.searchResultsPublished.filter(searchMatchFn)
    ];

    if (matches.length > 1) {
      console.error(
        'Unable to add saved block due to non-unique ID being specified, resulting in multiple search results'
      );
      return;
    }

    if (matches.length === 0) {
      console.error('Unable to add saved block, no matches found for given ID in search results');
      return;
    }

    const match = matches[0];

    const addBlockArgs: AddBlockArguments = {
      rawBlockType: match.type,
      selectAfterAdding: true,
      customBlockProperties: match.block_object
    };

    await this.context.dispatch(`project/${ProjectViewActions.addIndividualBlock}`, addBlockArgs, { root: true });
    this.resetState();
  }

  /**
   * This returns the pane to the AddBlock pane. Effectively going "back" in the add block flow.
   */
  @Action
  public async goBackToAddBlockPane() {
    await this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.addBlock, {
      root: true
    });
    this.resetState();
  }
}

export const AddSavedBlockPaneStoreModule = getModule(AddSavedBlockPaneStore);
