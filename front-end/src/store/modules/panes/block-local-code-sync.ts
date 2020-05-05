import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { autoRefreshJob, timeout } from '@/utils/async-utils';
import { LambdaWorkflowState, WorkflowStateType } from '@/types/graph';
import { copyElementToDocumentBody, getFileFromElementByQuery, readFileAsText } from '@/utils/dom-utils';
import { ProjectViewActions } from '@/constants/store-constants';
import { EditBlockMutators } from '@/store/modules/panes/edit-block-pane';
import uuid from 'uuid/v4';
import { RunCodeBlockLambdaConfig } from '@/types/run-lambda-types';
import { RunLambdaActions } from '@/store/modules/run-lambda';
import { OpenProjectMutation, SIDEBAR_PANE } from '@/types/project-editor-types';

const storeName = StoreType.blockLocalCodeSync;

export type BlockIdToJobId = { [key: string]: string };
export type JobIdToJobState = { [key: string]: FileWatchJobState };

export const syncFileIdPrefix = 'sync-local-file-input-';

export interface FileWatchJobState {
  jobId: string;
  blockId: string;
  fileContents: string;
  fileName: string;
  lastModifiedDate: number;
  autoExecuteBlock: boolean;
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
  executeBlockOnFileChangeToggled: boolean;

  selectedBlockForModal: LambdaWorkflowState | null;
}

export const baseState: BlockLocalCodeSyncState = {
  blockIdToJobIdLookup: {},
  jobIdToJobStateLookup: {},

  localFileSyncModalVisible: false,
  localFileSyncModalUniqueId: null,
  executeBlockOnFileChangeToggled: false,

  selectedBlockForModal: null
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: storeName })
export class BlockLocalCodeSyncStore extends VuexModule<ThisType<BlockLocalCodeSyncState>, RootState>
  implements BlockLocalCodeSyncState {
  public blockIdToJobIdLookup: BlockIdToJobId = initialState.blockIdToJobIdLookup;
  public jobIdToJobStateLookup: JobIdToJobState = initialState.jobIdToJobStateLookup;

  public localFileSyncModalVisible: boolean = initialState.localFileSyncModalVisible;
  public localFileSyncModalUniqueId: string | null = initialState.localFileSyncModalUniqueId;
  public executeBlockOnFileChangeToggled: boolean = initialState.executeBlockOnFileChangeToggled;

  public selectedBlockForModal: LambdaWorkflowState | null = initialState.selectedBlockForModal;

  // Example of "getter" syntax.
  get isBlockBeingSynced() {
    return (id: string) => !!this.blockIdToJobIdLookup[id];
  }

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
    this.jobIdToJobStateLookup = Object.values(this.jobIdToJobStateLookup).reduce((jobLookup, jobState) => {
      // Add back every job that isn't the one we want to remove.
      if (jobState.jobId !== jobToRemove.jobId) {
        jobLookup[jobState.jobId] = jobState;
      }

      return jobLookup;
    }, {} as JobIdToJobState);

    // Go through the new list of jobs and create the association
    this.blockIdToJobIdLookup = Object.values(this.jobIdToJobStateLookup).reduce((blockLookup, jobState) => {
      // Create the association for the lookup
      blockLookup[jobState.blockId] = jobState.jobId;
      return blockLookup;
    }, {} as BlockIdToJobId);
  }

  @Mutation
  public updateJobState(jobState: FileWatchJobState) {
    this.jobIdToJobStateLookup = {
      ...this.jobIdToJobStateLookup,
      [jobState.jobId]: jobState
    };
  }

  @Mutation
  public setModalVisibility(show: boolean) {
    this.localFileSyncModalVisible = show;
  }

  @Mutation
  public setSelectedBlockForModal(block: LambdaWorkflowState | null) {
    if (!block) {
      this.selectedBlockForModal = null;
      return;
    }

    this.selectedBlockForModal = deepJSONCopy(block);
  }

  @Mutation
  public setExecuteBlockOnFileChangeToggled(toggled: boolean) {
    this.executeBlockOnFileChangeToggled = toggled;
  }

  @Mutation
  public setModalUniqueId(id: string | null) {
    this.localFileSyncModalUniqueId = id;
  }

  @Action
  public resetModal() {
    this.setModalVisibility(false);
    this.setModalUniqueId(null);
    this.setSelectedBlockForModal(null);
    // Maybe the user would want this to stick between block adds?
    // Don't want to create unexpected behavior, so going to reset it for now.
    this.setExecuteBlockOnFileChangeToggled(false);
  }

  @Action
  public async updateProjectStoreBlockCode(jobState: FileWatchJobState) {
    const projectStore = this.context.rootState.project;

    if (!projectStore.openedProject) {
      throw new Error('Unable to retrieve opened project to update block code for in block file sync job');
    }

    const project = projectStore.openedProject;

    // Grab the actual block contents from the store.
    const block = project.workflow_states.find(block => block.id === jobState.blockId);

    // Ensure that we have a block and that it is a code block.
    if (!block || block.type !== WorkflowStateType.LAMBDA) {
      throw new Error('Unable to locate matching block to update code for in block file sync job');
    }

    // Since we know that it's a code block, we can cast it as such.
    const codeBlock = block as LambdaWorkflowState;

    const newBlock: LambdaWorkflowState = {
      ...codeBlock,
      // Write the new code to the block.
      code: jobState.fileContents
    };

    await this.context.dispatch(`project/${ProjectViewActions.updateExistingBlock}`, newBlock, { root: true });
  }

  @Action
  public async updateEditBlockPaneBlockCode(jobState: FileWatchJobState) {
    const projectStore = this.context.rootState.project;

    if (!projectStore.openedProject) {
      throw new Error('Unable to retrieve opened project to update edit block pane code for in block file sync job');
    }

    // Grab the currently selected block being edited.
    const editBlockPaneSelectedBlock = projectStore.editBlockPane && projectStore.editBlockPane.selectedNode;

    // If there isn't a block being edited currently, we can safely return.
    if (!editBlockPaneSelectedBlock) {
      return;
    }

    // If the block being edited isn't the same as the block sync job (or the block type is wrong), bail out.
    if (
      editBlockPaneSelectedBlock.id !== jobState.blockId ||
      editBlockPaneSelectedBlock.type !== WorkflowStateType.LAMBDA
    ) {
      return;
    }

    // Update the code of the currently selected block
    await this.context.commit(`project/editBlockPane/${EditBlockMutators.setCodeInput}`, jobState.fileContents, {
      root: true
    });
  }

  @Action
  public async executeBlockCode(jobState: FileWatchJobState) {
    const editBlockPane = this.context.rootState.project.editBlockPane;

    if (!editBlockPane) {
      throw new Error('Unable to execute block without edit block pane in store');
    }

    // We only re-select the node if we don't currently have it selected. This should prevent clearing the Monaco state.
    if (!editBlockPane.selectedNode || editBlockPane.selectedNode.id !== jobState.blockId) {
      // We auto-select the block in order to show the user what's going on.
      // This also ensures that the RunLambda store executes the right block.
      // TODO: Make the UI function independently of the "selected block" pane.
      await this.context.dispatch(`project/${ProjectViewActions.selectNode}`, jobState.blockId, { root: true });
    }

    // Ensure that the left sidebar pane is set to the code runner.
    // TODO: Clean up this leaky af abstraction
    if (this.context.rootState.project.activeLeftSidebarPane !== SIDEBAR_PANE.runEditorCodeBlock) {
      // Open up the left sidebar pane so that we can show the execution happening.
      await this.context.dispatch(
        `project/${ProjectViewActions.openLeftSidebarPane}`,
        SIDEBAR_PANE.runEditorCodeBlock,
        { root: true }
      );
    }

    const runLambdaConfig: RunCodeBlockLambdaConfig | null = this.context.rootGetters[`runLambda/getRunLambdaConfig`];

    if (!runLambdaConfig) {
      throw new Error('Unable to execute synced block, could not get run lambda config');
    }

    await this.context.dispatch(`runLambda/${RunLambdaActions.runLambdaCode}`, runLambdaConfig, { root: true });
  }

  @Action
  public async updateBlockCode(jobId: string) {
    // TODO: Check if the file contents have changed and dispatch updates
    const jobState = this.jobIdToJobStateLookup[jobId];

    // This shouldn't happen, but just in case we will bail.
    if (!jobState) {
      console.error('Could not find file update job data. This is weird.');
      return;
    }

    // TODO: Move everything to a single source of truth for the block code. This is bound to create bugs, eventually.
    // Handles updating the main project copy of the block
    await this.updateProjectStoreBlockCode(jobState);

    // Updates the edit block pane copy of the block
    await this.updateEditBlockPaneBlockCode(jobState);

    // If the user wanted this to be executed, kick off the job.
    if (jobState.autoExecuteBlock) {
      await this.executeBlockCode(jobState);
    }
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

    const selector = `#${syncFileIdPrefix}${this.localFileSyncModalUniqueId}`;

    // Keep a copy of the file input around for after the Modal closes.
    copyElementToDocumentBody(selector);

    const fileInputElement = getFileFromElementByQuery(selector);

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
      fileName: fileInputElement.name,
      autoExecuteBlock: false
    };

    // Add the job state to the store for later usage.
    this.addJobForBlock(jobState);

    // Perform the initial grab of the code from the file.
    this.updateBlockCode(jobId);

    // If we are supposed to execute the code on save, then set that flag for future job runs.
    if (this.executeBlockOnFileChangeToggled) {
      this.updateJobState({
        ...jobState,
        autoExecuteBlock: true
      });
    }

    // Clear the state before the next run
    this.resetModal();

    // Creates a job that runs 10 times per second and checks if the file we're watching has changed.
    await autoRefreshJob({
      nonce: jobId,
      makeRequest: async () => {
        // Don't write changes to the block until we've closed the modal
        if (this.localFileSyncModalVisible) {
          return;
        }

        const fileInputElement = getFileFromElementByQuery(selector);

        if (!fileInputElement) {
          throw new Error('Could not get file input element from DOM');
        }

        // TODO: Check if the file contents have changed and dispatch updates
        const jobState = this.jobIdToJobStateLookup[jobId];

        // This shouldn't happen, but just in case we will bail.
        if (!jobState) {
          console.error('Could not find file update job data. This is weird.');
          return;
        }

        // If the file hasn't changed, just return.
        if (jobState.lastModifiedDate === fileInputElement.lastModified) {
          return;
        }

        try {
          // Grab the contents of the file so that we can update the block code.
          const updatedCode = await readFileAsText(fileInputElement);

          if (updatedCode === null) {
            console.error('Unable to read file contents for block file sync job.');
            return;
          }

          // Update the store with the new state
          this.updateJobState({
            ...jobState,
            fileContents: updatedCode,
            lastModifiedDate: fileInputElement.lastModified
          });

          // Kick off updating the block state
          await this.updateBlockCode(jobId);
        } catch (e) {
          console.error('Unable to update block code', e);
        }
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
      throw new Error('Missing edit block store for creating sync job');
    }

    if (editBlockStore.selectedNode === null || editBlockStore.selectedNode.type !== WorkflowStateType.LAMBDA) {
      throw new Error('No block selected to sync file with');
    }

    // const openedProject = this.context.rootState.project.openedProject;

    const selectedCodeBlock = editBlockStore.selectedNode as LambdaWorkflowState;

    this.setModalUniqueId(uuid());
    this.setSelectedBlockForModal(selectedCodeBlock);
    this.setModalVisibility(true);
  }

  @Action
  public async stopSyncJobForSelectedBlock() {
    const editBlockStore = this.context.rootState.project.editBlockPane;

    if (!editBlockStore) {
      throw new Error('Missing edit block store for stopping sync job');
    }

    // Don't try to stop the job is there isn't anything to do.
    if (editBlockStore.selectedNode === null || editBlockStore.selectedNode.type !== WorkflowStateType.LAMBDA) {
      return;
    }

    const selectedCodeBlock = editBlockStore.selectedNode as LambdaWorkflowState;

    const jobId = this.blockIdToJobIdLookup[selectedCodeBlock.id];

    if (!jobId) {
      // Job doesn't exist, so just return.
      return;
    }

    const jobState = this.jobIdToJobStateLookup[jobId];

    if (!jobState) {
      throw new Error('Unable to remove block watch job, job state was not found in lookup');
    }

    this.removeJobForBlock(jobState);

    const params: OpenProjectMutation = {
      markAsDirty: true,
      project: null,
      config: null
    };

    // This forces the Cytoscape graph elements to update, which gets rid of the file sync icon.
    // TODO: Clean up this hack by (probably) using a getter for the Cytoscape graph state.
    this.context.dispatch(`project/${ProjectViewActions.updateProject}`, params, { root: true });

    // Wait for the file sync job to finish
    await timeout(200);
  }
}
