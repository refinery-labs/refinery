import { VuexModule, Module, Mutation, Action, getModule } from 'vuex-module-decorators';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState } from '@/store/store-types';
import { autoRefreshJob } from '@/utils/async-utils';
import uuid from 'uuid/v4';
import { LambdaWorkflowState, WorkflowStateType } from '@/types/graph';
import { getFileFromElementByQuery, getFileFromEvent, readFileAsText } from '@/utils/dom-utils';

const storeName = 'blockLocalCodeSync';

export type BlockIdToJobId = { [key: string]: string };
export type JobIdToJobState = { [key: string]: FileWatchJobState };

export const syncFileIdPrefix = 'sync-local-file-input-';

export interface FileWatchJobState {
  jobId: string;
  blockId: string;
  fileContents: string;
  fileName: string;
  lastModifiedDate: number;
}

export interface FileWatchDomJob {
  file: File;
  blockId: string;
}

export interface BlockLocalCodeSyncState {
  blockIdToJobIdLookup: BlockIdToJobId;
  jobIdToJobStateLookup: JobIdToJobState;

  localFileSyncModalVisible: boolean;
  // This UUID is used so that we can keep identify the HTML element via query selector.
  localFileSyncModalUniqueId: string | null;

  selectedBlockForModal: LambdaWorkflowState | null;
}

export const baseState: BlockLocalCodeSyncState = {
  blockIdToJobIdLookup: {},
  jobIdToJobStateLookup: {},

  localFileSyncModalVisible: false,
  localFileSyncModalUniqueId: null,

  selectedBlockForModal: null
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, dynamic: true, store, name: storeName })
class BlockLocalCodeSyncStore extends VuexModule<ThisType<BlockLocalCodeSyncState>, RootState>
  implements BlockLocalCodeSyncState {
  public blockIdToJobIdLookup: BlockIdToJobId = initialState.blockIdToJobIdLookup;
  public jobIdToJobStateLookup: JobIdToJobState = initialState.jobIdToJobStateLookup;

  public localFileSyncModalVisible: boolean = initialState.localFileSyncModalVisible;
  public localFileSyncModalUniqueId: string | null = initialState.localFileSyncModalUniqueId;

  public selectedBlockForModal: LambdaWorkflowState | null = initialState.selectedBlockForModal;

  // Example of "getter" syntax.
  // get currentExampleValue() {
  // return this.example;
  // }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public addJobForBlock(jobState: FileWatchJobState) {
    this.blockIdToJobIdLookup = {
      ...this.blockIdToJobIdLookup,
      [jobState.blockId]: jobState.jobId
    };
    this.jobIdToJobStateLookup = {
      ...this.jobIdToJobStateLookup,
      [jobState.jobId]: jobState
    };
  }

  @Mutation
  public removeJobForBlock(jobToRemove: FileWatchJobState) {
    // Remove the job from the list
    this.jobIdToJobStateLookup = Object.values(this.jobIdToJobStateLookup).reduce(
      (jobLookup, jobState) => {
        // Add back every job that isn't the one we want to remove.
        if (jobState.jobId !== jobToRemove.jobId) {
          jobLookup[jobState.jobId] = jobState;
        }

        return jobLookup;
      },
      {} as JobIdToJobState
    );

    // Go through the new list of jobs and create the association
    this.blockIdToJobIdLookup = Object.values(this.jobIdToJobStateLookup).reduce(
      (blockLookup, jobState) => {
        // Create the association for the lookup
        blockLookup[jobState.blockId] = jobState.jobId;
        return blockLookup;
      },
      {} as BlockIdToJobId
    );
  }

  @Mutation
  public setModalVisibility(show: boolean) {
    this.localFileSyncModalVisible = show;
  }

  @Mutation
  public setSelectedBlockForModal(block: LambdaWorkflowState) {
    this.selectedBlockForModal = deepJSONCopy(block);
  }

  @Action
  public async addBlockWatchJob() {
    const jobId = this.localFileSyncModalUniqueId;
    const selectedBlock = this.selectedBlockForModal;

    if (!jobId) {
      throw new Error('Cannot add file watch job with missing unique job ID');
    }

    if (!selectedBlock) {
      throw new Error('Cannot add file watch job with missing selected block');
    }

    const fileInputElement = getFileFromElementByQuery(`#${syncFileIdPrefix}${this.localFileSyncModalUniqueId}`);

    if (!fileInputElement) {
      throw new Error('Could not get file input element from DOM');
    }

    const file = await readFileAsText(fileInputElement);

    if (file === null) {
      throw new Error('Unable to read file contents');
    }

    const jobState: FileWatchJobState = {
      jobId: jobId,
      blockId: selectedBlock.id,
      fileContents: file,
      lastModifiedDate: fileInputElement.lastModified,
      fileName: fileInputElement.name
    };

    // Creates a job that runs 10 times per second and checks if the file we're watching has changed.
    await autoRefreshJob({
      nonce: jobId,
      makeRequest: async () => {
        // Don't write changes to the block until we've closed the modal
        if (this.localFileSyncModalVisible) {
          return;
        }

        // TODO: Check if the file contents have changed and dispatch updates
      },
      isStillValid: async (nonce, iteration) => {
        // Keep going so long as the job is still in our lookup!
        return this.jobIdToJobStateLookup[nonce] !== undefined;
      },
      timeoutMs: 100
    });
  }

  @Action
  public async OpenSyncFileModal() {
    if (this.context.rootState.project.openedProject === null) {
      throw new Error('No project is open to sync block');
    }

    const editBlockStore = this.context.rootState.project.editBlockPane;

    if (!editBlockStore) {
      throw new Error('Missing edit block store');
    }

    if (editBlockStore.selectedNode === null || editBlockStore.selectedNode.type !== WorkflowStateType.LAMBDA) {
      throw new Error('No block selected to sync file with');
    }

    const openedProject = this.context.rootState.project.openedProject;

    const selectedCodeBlock = editBlockStore.selectedNode as LambdaWorkflowState;
  }
}

export const BlockLocalCodeSyncStoreModule = getModule(BlockLocalCodeSyncStore);
