import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { ProjectViewActions } from '@/constants/store-constants';
import { SIDEBAR_PANE } from '@/types/project-editor-types';
import { LibraryBuildArguments, searchSavedBlocks, startLibraryBuild } from '@/store/fetchers/api-helpers';
import { SavedBlockSearchResult, SharedBlockPublishStatus } from '@/types/api-types';
import { ChosenBlock } from '@/types/add-block-types';
import { BlockEnvironmentVariable, LambdaWorkflowState, WorkflowStateType } from '@/types/graph';
import { AddSavedBlockEnvironmentVariable } from '@/types/saved-blocks-types';
import { addSharedFilesToProject, linkSharedFilesToCodeBlock, safelyDuplicateBlock } from '@/utils/block-utils';

const storeName = StoreType.addSavedBlockPane;

export interface AddSavedBlockPaneState {
  isBusySearching: boolean;

  searchInput: string;
  languageInput: string;
  blockTypeInput: string;

  searchPrivateToggleValue: boolean;
  searchPublishedToggleValue: boolean;

  searchResultsPrivate: SavedBlockSearchResult[];
  searchResultsPublished: SavedBlockSearchResult[];

  environmentVariablesInputs: { [key: string]: string };

  chosenBlock: ChosenBlock | null;
}

export const baseState: AddSavedBlockPaneState = {
  isBusySearching: false,

  searchInput: '',
  languageInput: '',
  blockTypeInput: SharedBlockPublishStatus.PRIVATE,

  searchPrivateToggleValue: true,
  searchPublishedToggleValue: true,

  searchResultsPrivate: [],
  searchResultsPublished: [],

  environmentVariablesInputs: {},

  chosenBlock: null
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, name: storeName })
export class AddSavedBlockPaneStore extends VuexModule<ThisType<AddSavedBlockPaneState>, RootState>
  implements AddSavedBlockPaneState {
  public isBusySearching: boolean = initialState.isBusySearching;

  public searchInput: string = initialState.searchInput;
  public languageInput: string = initialState.languageInput;
  public blockTypeInput: string = initialState.blockTypeInput;

  public searchPrivateToggleValue: boolean = initialState.searchPrivateToggleValue;
  public searchPublishedToggleValue: boolean = initialState.searchPublishedToggleValue;

  public searchResultsPrivate: SavedBlockSearchResult[] = initialState.searchResultsPrivate;
  public searchResultsPublished: SavedBlockSearchResult[] = initialState.searchResultsPublished;
  public searchResultsGit: SavedBlockSearchResult[] = initialState.searchResultsPublished;

  public environmentVariablesInputs: { [key: string]: string } = initialState.environmentVariablesInputs;

  public chosenBlock: ChosenBlock | null = initialState.chosenBlock;

  get environmentVariableEntries(): AddSavedBlockEnvironmentVariable[] | null {
    if (!this.chosenBlock || this.chosenBlock.block.type !== WorkflowStateType.LAMBDA) {
      return null;
    }

    const block = this.chosenBlock.block.block_object as LambdaWorkflowState;

    const envVariables = block.environment_variables;
    const envVariablesIds = Object.keys(envVariables);

    // Check that any env variables need to be set, else do nothing.
    if (envVariablesIds.length === 0) {
      return null;
    }

    const isVariableValid = (env: BlockEnvironmentVariable) => {
      const value = this.environmentVariablesInputs[env.name];

      if (value === undefined) {
        return null;
      }

      // If the variable isn't required, it's always valid
      if (!env.required) {
        return true;
      }

      return value !== '';
    };

    return envVariablesIds.map(id => ({
      ...envVariables[id],
      id: id,
      valid: isVariableValid(envVariables[id]),
      value: this.environmentVariablesInputs[envVariables[id].name]
    }));
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public setSearchInputValue(value: string) {
    this.searchInput = value;
  }

  @Mutation
  public setLanguageInputValue(value: string) {
    this.languageInput = value;
  }

  @Mutation
  public setBlockTypeInputValue(value: string) {
    this.blockTypeInput = value;
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
  public setSearchResultsGit(results: SavedBlockSearchResult[]) {
    this.searchResultsGit = results;
  }

  @Mutation
  public setIsBusySearching(val: boolean) {
    this.isBusySearching = val;
  }

  @Mutation
  public setChosenBlock(chosenBlock: ChosenBlock) {
    this.chosenBlock = chosenBlock;
  }

  @Mutation
  public clearChosenBlock() {
    this.chosenBlock = null;
  }

  @Mutation
  public setEnvironmentVariablesValue({ name, value }: { name: string; value: string }) {
    this.environmentVariablesInputs = {
      ...this.environmentVariablesInputs,
      [name]: value
    };
  }

  @Action
  public async searchSavedBlocks() {
    this.setIsBusySearching(true);

    if (!this.context.rootState.project.openedProject) {
      console.error('No project is currently opened');
      return;
    }

    const projectId = this.context.rootState.project.openedProject.project_id;

    const privateSearch = searchSavedBlocks(
      this.searchInput,
      SharedBlockPublishStatus.PRIVATE,
      this.languageInput,
      projectId
    );
    const publicSearch = searchSavedBlocks(
      this.searchInput,
      SharedBlockPublishStatus.PUBLISHED,
      this.languageInput,
      projectId
    );
    const gitSearch = searchSavedBlocks(this.searchInput, SharedBlockPublishStatus.GIT, this.languageInput, projectId);

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

    const gitResult = await gitSearch;

    if (!gitResult) {
      console.error('Unable to perform saved block search, server did not yield a response');
      return;
    }

    this.setSearchResultsPrivate(privateResult);

    // Only add unique results. This strips out all public blocks that are in our saved blocks already.
    const filteredPublicResults = publicResult.filter(
      result => !privateResult.some(privateResult => privateResult.id === result.id)
    );

    this.setSearchResultsPublished(filteredPublicResults);

    this.setSearchResultsGit(gitResult);

    this.setIsBusySearching(false);
  }

  @Action
  public async selectBlockToAdd(id: string) {
    const searchMatchFn = (result: SavedBlockSearchResult) => result.id === id;

    const privateMatches = this.searchResultsPrivate.filter(searchMatchFn);
    const publishedMatches = this.searchResultsPublished.filter(searchMatchFn);
    const gitMatches = this.searchResultsGit.filter(searchMatchFn);

    const matches = [...privateMatches, ...publishedMatches, ...gitMatches];

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

    this.setChosenBlock({
      block: matches[0],
      blockSource: privateMatches.length > 0 ? 'private' : 'public'
    });
  }

  @Action
  public async addChosenBlock() {
    const chosenBlock = this.chosenBlock;

    if (!chosenBlock) {
      console.error('Unable to add saved block, no chosen block was found to add');
      return;
    }

    if (!this.context.rootState.project.openedProjectConfig) {
      console.error('Missing project config, cannot add block');
      return;
    }

    if (!this.context.rootState.project.openedProject) {
      console.error("No opened project was found, can't add block!");
      return;
    }

    const openedProjectConfig = this.context.rootState.project.openedProjectConfig;

    let match = chosenBlock.block;

    const addedBlock = await safelyDuplicateBlock(
      this.context.dispatch,
      openedProjectConfig,
      {
        ...match.block_object,
        saved_block_metadata: {
          id: match.id,
          version: match.version,
          timestamp: match.timestamp,
          added_timestamp: Date.now()
        }
      },
      this.environmentVariableEntries
    );

    // Add the Saved Block's Shared Files to the project
    const addedSharedFiles = await addSharedFilesToProject(
      this.context.dispatch,
      chosenBlock.block.shared_files,
      this.context.rootState.project.openedProject
    );

    // Add Shared File Links to the newly-added Code Block
    await linkSharedFilesToCodeBlock(
      this.context.dispatch,
      addedBlock.id,
      addedSharedFiles,
      this.context.rootState.project.openedProject
    );

    // If it's a code block being added, kick off the library build to improve the user's UX.
    if (match.type === WorkflowStateType.LAMBDA && match.block_object.type === WorkflowStateType.LAMBDA) {
      const codeBlock = match.block_object as LambdaWorkflowState;

      const params: LibraryBuildArguments = {
        language: codeBlock.language,
        libraries: codeBlock.libraries
      };

      startLibraryBuild(params);
    }

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
