import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import store from '@/store/index';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState } from '@/store/store-types';
import { ProjectViewActions } from '@/constants/store-constants';
import { SIDEBAR_PANE } from '@/types/project-editor-types';
import { searchSavedBlocks } from '@/store/fetchers/api-helpers';
import { SavedBlockSearchResult, SharedBlockPublishStatus } from '@/types/api-types';
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

  @Mutation
  public setIsBusySearching(val: boolean) {
    this.isBusySearching = val;
  }

  @Action
  public async searchSavedBlocks() {
    AddSavedBlockPaneStoreModule.setIsBusySearching(true);

    const privateSearch = searchSavedBlocks(this.searchInput, SharedBlockPublishStatus.PRIVATE);
    const publicSearch = searchSavedBlocks(this.searchInput, SharedBlockPublishStatus.PUBLISHED);

    const privateResult = await privateSearch;

    if (!privateResult) {
      console.error('Unable to perform saved block search, server did not yield a response');
      return;
    }

    const publicResult = await publicSearch;

    if (!publicResult) {
      console.error('Unable to perform saved block search, server did not yield a response');
      return;
    }

    this.setSearchResultsPrivate(privateResult);

    // Only add unique results. This strips out all public blocks that are in our saved blocks already.
    const filteredPublicResults = publicResult.filter(
      result => !privateResult.some(privateResult => privateResult.id === result.id)
    );

    this.setSearchResultsPublished(filteredPublicResults);

    AddSavedBlockPaneStoreModule.setIsBusySearching(false);
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
      customBlockProperties: {
        ...match.block_object,
        saved_block_metadata: {
          id: match.id,
          version: match.version,
          timestamp: match.timestamp,
          added_timestamp: Date.now()
        }
      }
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
