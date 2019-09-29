import { Module } from 'vuex';
import deepEqual from 'fast-deep-equal';
import { RootState } from '../../store-types';
import {
  ApiEndpointWorkflowState,
  LambdaWorkflowState,
  SavedBlockMetadata,
  ScheduleTriggerWorkflowState,
  SqsQueueWorkflowState,
  SupportedLanguage,
  WorkflowRelationship,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { getNodeDataById, getTransitionsForNode } from '@/utils/project-helpers';
import { ProjectViewActions } from '@/constants/store-constants';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import { DEFAULT_LANGUAGE_CODE } from '@/constants/project-editor-constants';
import { HTTP_METHOD } from '@/constants/api-constants';
import { safelyDuplicateBlock, updateBlockWithNewSavedBlockVersion, validatePath } from '@/utils/block-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { getSavedBlockStatus, libraryBuildArguments, startLibraryBuild } from '@/store/fetchers/api-helpers';
import { SavedBlockStatusCheckResult } from '@/types/api-types';
import { downloadBlockAsZip } from '@/utils/project-debug-utils';

const cronRegex = new RegExp(
  //'cron\(^\\s*($|#|\\w+\\s*=|(\\?|\\*|(?:[0-5]?\\d)(?:(?:-|/|\\,)(?:[0-5]?\\d))?(?:,(?:[0-5]?\\d)(?:(?:-|/|\\,)(?:[0-5]?\\d))?)*)\\s+(\\?|\\*|(?:[0-5]?\\d)(?:(?:-|/|\\,)(?:[0-5]?\\d))?(?:,(?:[0-5]?\\d)(?:(?:-|/|\\,)(?:[0-5]?\\d))?)*)\\s+(\\?|\\*|(?:[01]?\\d|2[0-3])(?:(?:-|/|\\,)(?:[01]?\\d|2[0-3]))?(?:,(?:[01]?\\d|2[0-3])(?:(?:-|/|\\,)(?:[01]?\\d|2[0-3]))?)*)\\s+(\\?|\\*|(?:0?[1-9]|[12]\\d|3[01])(?:(?:-|/|\\,)(?:0?[1-9]|[12]\\d|3[01]))?(?:,(?:0?[1-9]|[12]\\d|3[01])(?:(?:-|/|\\,)(?:0?[1-9]|[12]\\d|3[01]))?)*)\\s+(\\?|\\*|(?:[1-9]|1[012])(?:(?:-|/|\\,)(?:[1-9]|1[012]))?(?:L|W)?(?:,(?:[1-9]|1[012])(?:(?:-|/|\\,)(?:[1-9]|1[012]))?(?:L|W)?)*|\\?|\\*|(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(?:(?:-)(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))?(?:,(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(?:(?:-)(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))?)*)\\s+(\\?|\\*|(?:[0-6])(?:(?:-|/|\\,|#)(?:[0-6]))?(?:L)?(?:,(?:[0-6])(?:(?:-|/|\\,|#)(?:[0-6]))?(?:L)?)*|\\?|\\*|(?:MON|TUE|WED|THU|FRI|SAT|SUN)(?:(?:-)(?:MON|TUE|WED|THU|FRI|SAT|SUN))?(?:,(?:MON|TUE|WED|THU|FRI|SAT|SUN)(?:(?:-)(?:MON|TUE|WED|THU|FRI|SAT|SUN))?)*)(|\\s)+(\\?|\\*|(?:|\\d{4})(?:(?:-|/|\\,)(?:|\\d{4}))?(?:,(?:|\\d{4})(?:(?:-|/|\\,)(?:|\\d{4}))?)*))\)$'
  'cron(.*)'
);

const rateRegex = /^rate\(\d+ (minute|minutes|hour|hours|day|days)\)$/;

// Enums
export enum EditBlockMutators {
  resetState = 'resetState',

  setSelectedNode = 'setSelectedNode',
  setSelectedNodeOriginal = 'setSelectedNodeOriginal',
  setSelectedNodeMetadata = 'setSelectedNodeMetadata',
  setIsLoadingMetadata = 'setIsLoadingMetadata',

  setConfirmDiscardModalVisibility = 'setConfirmDiscardModalVisibility',

  // Inputs
  setBlockName = 'setBlockName',

  // Code Block Inputs
  setCodeLanguage = 'setCodeLanguage',
  setDependencyImports = 'setDependencyImports',
  setCodeInput = 'setCodeInput',
  setExecutionMemory = 'setExecutionMemory',
  setMaxExecutionTime = 'setMaxExecutionTime',
  setLayers = 'setLayers',
  setEnvironmentVariables = 'setEnvironmentVariables',
  setSavedInputData = 'setSavedInputData',

  setCodeModalVisibility = 'setCodeModalVisibility',
  setLibrariesModalVisibility = 'setLibrariesModalVisibility',

  setEnteredLibrary = 'setEnteredLibrary',
  deleteDependencyImport = 'deleteDependencyImport',
  addDependencyImport = 'addDependencyImport',

  setConcurrencyLimit = 'setConcurrencyLimit',

  setChangeLanguageWarningVisible = 'setChangeLanguageWarningVisible',
  setNextLanguageToChangeTo = 'setNextLanguageToChangeTo',
  resetChangeLanguageModal = 'resetChangeLanguageModal',
  setReplaceCodeWithTemplateChecked = 'setReplaceCodeWithTemplateChecked',

  // Sync file with block
  setFileSyncModalVisibility = 'setFileSyncModalVisibility',
  setFileToSyncWithBlock = 'setFileToSyncWithBlock',

  // Timer Block Inputs
  setScheduleExpression = 'setScheduleExpression',
  setInputData = 'setInputData',

  // Queue Block Inputs
  setBatchSize = 'setBatchSize',

  // API Endpoint Inputs
  setHTTPMethod = 'setHTTPMethod',
  setHTTPPath = 'setHTTPPath'
}

export enum EditBlockActions {
  selectNodeFromOpenProject = 'selectNodeFromOpenProject',
  selectCurrentlySelectedProjectNode = 'selectCurrentlySelectedProjectNode',

  // Shared Actions
  saveBlock = 'saveBlock',
  tryToCloseBlock = 'tryToCloseBlock',
  cancelAndResetBlock = 'cancelAndResetBlock',
  runCodeBlock = 'runCodeBlock',
  duplicateBlock = 'duplicateBlock',
  deleteBlock = 'deleteBlock',
  deleteTransition = 'deleteTransition',
  kickOffLibraryBuild = 'kickOffLibraryBuild',
  // Code Block specific
  saveCodeBlockToDatabase = 'saveCodeBlockToDatabase',
  updateSavedBlockVersion = 'updateSavedBlockVersion',
  saveInputData = 'saveInputData',
  showChangeLanguageWarning = 'showChangeLanguageWarning',
  changeBlockLanguage = 'changeBlockLanguage',
  downloadBlockAsZip = 'downloadBlockAsZip',
  syncBlockWithFile = 'syncBlockWithFile'
}

export enum EditBlockGetters {
  isStateDirty = 'isStateDirty',
  isEditedBlockValid = 'isEditedBlockValid',
  scheduleExpressionValid = 'scheduleExpressionValid',
  collidingApiEndpointBlocks = 'collidingApiEndpointBlocks',
  isApiEndpointPathValid = 'isApiEndpointPathValid'
}

// Types
export interface EditBlockPaneState {
  selectedNode: WorkflowState | null;
  selectedNodeOriginal: WorkflowState | null;

  selectedNodeMetadata: SavedBlockStatusCheckResult | null;
  isLoadingMetadata: boolean;

  confirmDiscardModalVisibility: false;
  showCodeModal: boolean;

  // This doesn't really make sense here
  // but neither does having it in a selectedNode...
  librariesModalVisibility: boolean;
  enteredLibrary: string;

  changeLanguageWarningVisible: boolean;
  nextLanguageToChangeTo: SupportedLanguage | null;
  replaceCodeWithTemplateChecked: boolean;

  fileSyncModalVisible: boolean;
  fileToSyncBlockWith: string | null;
}

// Initial State
const moduleState: EditBlockPaneState = {
  selectedNode: null,
  selectedNodeOriginal: null,
  selectedNodeMetadata: null,
  isLoadingMetadata: false,

  confirmDiscardModalVisibility: false,
  showCodeModal: false,
  librariesModalVisibility: false,
  enteredLibrary: '',

  changeLanguageWarningVisible: false,
  nextLanguageToChangeTo: null,
  replaceCodeWithTemplateChecked: false,

  fileSyncModalVisible: false,
  fileToSyncBlockWith: null
};

function modifyBlock<T extends WorkflowState>(state: EditBlockPaneState, fn: (block: T) => void) {
  const block = state.selectedNode as T;
  fn(block);
  // Vue.set(state, 'selectedNode', block);
  state.selectedNode = deepJSONCopy(block);
}

function getBlockAsType<T extends WorkflowState>(
  state: EditBlockPaneState,
  type: WorkflowStateType,
  fn: (block: T) => void
) {
  if (!state.selectedNode || state.selectedNode.type !== type) {
    return null;
  }
  modifyBlock<T>(state, fn);
}

function lambdaChange(state: EditBlockPaneState, fn: (block: LambdaWorkflowState) => void) {
  getBlockAsType<LambdaWorkflowState>(state, WorkflowStateType.LAMBDA, fn);
}

function scheduleExpressionChange(state: EditBlockPaneState, fn: (block: ScheduleTriggerWorkflowState) => void) {
  getBlockAsType<ScheduleTriggerWorkflowState>(state, WorkflowStateType.SCHEDULE_TRIGGER, fn);
}

function sqsQueueChange(state: EditBlockPaneState, fn: (block: SqsQueueWorkflowState) => void) {
  getBlockAsType<SqsQueueWorkflowState>(state, WorkflowStateType.SQS_QUEUE, fn);
}

function apiEndpointChange(state: EditBlockPaneState, fn: (block: ApiEndpointWorkflowState) => void) {
  getBlockAsType<ApiEndpointWorkflowState>(state, WorkflowStateType.API_ENDPOINT, fn);
}

const EditBlockPaneModule: Module<EditBlockPaneState, RootState> = {
  namespaced: true,
  state: deepJSONCopy(moduleState),
  getters: {
    [EditBlockGetters.isStateDirty]: state =>
      state.selectedNode && state.selectedNodeOriginal && !deepEqual(state.selectedNode, state.selectedNodeOriginal),
    [EditBlockGetters.isEditedBlockValid]: (state, getters) => {
      if (!state.selectedNode) {
        return true;
      }

      if (state.selectedNode.type === WorkflowStateType.API_ENDPOINT) {
        // Not a huge fan of this being here...
        // But this prevents painful server issues from existing so it feels like the best move.
        const collidingBlocks: WorkflowState[] | null = getters[EditBlockGetters.collidingApiEndpointBlocks];

        const validApiEndpointConfig = !collidingBlocks || collidingBlocks.length === 0;

        return validApiEndpointConfig && getters[EditBlockGetters.isApiEndpointPathValid];
      }

      if (state.selectedNode.type === WorkflowStateType.SCHEDULE_TRIGGER) {
        return getters[EditBlockGetters.scheduleExpressionValid];
      }

      return true;
    },
    [EditBlockGetters.scheduleExpressionValid]: state => {
      if (!state.selectedNode || state.selectedNode.type !== WorkflowStateType.SCHEDULE_TRIGGER) {
        return true;
      }

      const scheduleTrigger = state.selectedNode as ScheduleTriggerWorkflowState;

      if (scheduleTrigger.schedule_expression === null || scheduleTrigger.schedule_expression === undefined) {
        return false;
      }

      return rateRegex.test(scheduleTrigger.schedule_expression) || cronRegex.test(scheduleTrigger.schedule_expression);
    },
    [EditBlockGetters.collidingApiEndpointBlocks]: (state, getters, rootState) => {
      if (
        !rootState.project.openedProject ||
        !state.selectedNode ||
        state.selectedNode.type !== WorkflowStateType.API_ENDPOINT
      ) {
        return null;
      }

      const selectedNode = state.selectedNode as ApiEndpointWorkflowState;

      return rootState.project.openedProject.workflow_states
        .filter(w => w.type === WorkflowStateType.API_ENDPOINT)
        .filter(w => w.id !== selectedNode.id)
        .filter(w => {
          const apiW = w as ApiEndpointWorkflowState;
          // If both of these match, we have an invalid ApiEndpoint configuration
          return apiW.api_path === selectedNode.api_path && apiW.http_method === selectedNode.http_method;
        });
    },
    [EditBlockGetters.isApiEndpointPathValid]: state => {
      if (!state.selectedNode || state.selectedNode.type !== WorkflowStateType.API_ENDPOINT) {
        return true;
      }
      // If we have invalid characters, this will return false.
      return /^\/[a-zA-Z0-9/]*$/.test((state.selectedNode as ApiEndpointWorkflowState).api_path);
    }
  },
  mutations: {
    /**
     * Resets the state of the pane back to it's default.
     */
    [EditBlockMutators.resetState](state) {
      resetStoreState(state, moduleState);
    },
    [EditBlockMutators.setSelectedNode](state, node) {
      state.selectedNode = deepJSONCopy(node);
    },
    [EditBlockMutators.setSelectedNodeOriginal](state, node) {
      state.selectedNodeOriginal = deepJSONCopy(node);
    },
    [EditBlockMutators.setSelectedNodeMetadata](state, metadata) {
      state.selectedNodeMetadata = deepJSONCopy(metadata);
    },
    [EditBlockMutators.setIsLoadingMetadata](state, loading) {
      state.isLoadingMetadata = loading;
    },
    [EditBlockMutators.setConfirmDiscardModalVisibility](state, visibility) {
      state.confirmDiscardModalVisibility = visibility;
    },

    // Shared mutations
    [EditBlockMutators.setBlockName](state, name) {
      modifyBlock(state, block => (block.name = name));
    },

    // Code Block specific mutations
    [EditBlockMutators.setCodeInput](state, code) {
      lambdaChange(state, block => (block.code = code));
    },
    [EditBlockMutators.setCodeLanguage](state, language) {
      lambdaChange(state, block => {
        block.language = language;
      });
    },
    [EditBlockMutators.setDependencyImports](state, libraries) {
      lambdaChange(state, block => (block.libraries = libraries));
    },
    [EditBlockMutators.deleteDependencyImport](state, library: string) {
      lambdaChange(state, block => {
        const newLibrariesArray = block.libraries.filter(existingLibrary => {
          return existingLibrary !== library;
        });
        block.libraries = newLibrariesArray;
      });
    },
    [EditBlockMutators.addDependencyImport](state, library: string) {
      lambdaChange(state, block => {
        const canonicalizedLibrary = library.trim();
        if (!block.libraries.includes(canonicalizedLibrary)) {
          const newLibrariesArray = deepJSONCopy(block.libraries).concat(canonicalizedLibrary);
          block.libraries = newLibrariesArray;
        }
      });
    },
    [EditBlockMutators.setMaxExecutionTime](state, maxExecTime) {
      lambdaChange(state, block => (block.max_execution_time = parseInt(maxExecTime, 10)));
    },
    [EditBlockMutators.setExecutionMemory](state, memory) {
      memory = Math.min(memory, 3008);
      memory = Math.max(memory, 128);

      // Always make the value be an increment of 64
      memory = memory % 64 !== 0 ? memory - (memory % 64) : memory;

      lambdaChange(state, block => (block.memory = memory));
    },
    [EditBlockMutators.setSavedInputData](state, inputData) {
      lambdaChange(state, block => (block.saved_input_data = inputData));
    },
    [EditBlockMutators.setConcurrencyLimit](state, concurrencyLimit) {
      if (concurrencyLimit !== false) {
        concurrencyLimit = Math.min(concurrencyLimit, 100);
        concurrencyLimit = Math.max(concurrencyLimit, 1);
      }

      lambdaChange(state, block => (block.reserved_concurrency_count = concurrencyLimit));
    },
    [EditBlockMutators.setLayers](state, layers) {
      lambdaChange(state, block => (block.layers = layers));
    },
    [EditBlockMutators.setEnvironmentVariables](state, environmentVariables) {
      lambdaChange(state, block => (block.environment_variables = environmentVariables));
    },
    [EditBlockMutators.setCodeModalVisibility](state, visible) {
      state.showCodeModal = visible;
    },
    [EditBlockMutators.setScheduleExpression](state, expression: string) {
      scheduleExpressionChange(state, block => (block.schedule_expression = expression));
    },
    [EditBlockMutators.setInputData](state, input_string: string) {
      scheduleExpressionChange(state, block => (block.input_string = input_string));
    },
    [EditBlockMutators.setBatchSize](state, batch_size: number) {
      sqsQueueChange(state, block => (block.batch_size = batch_size));
    },
    [EditBlockMutators.setHTTPMethod](state, http_method: HTTP_METHOD) {
      apiEndpointChange(state, block => (block.http_method = http_method));
    },
    [EditBlockMutators.setHTTPPath](state, api_path: string) {
      apiEndpointChange(state, block => (block.api_path = validatePath(api_path)));
    },
    [EditBlockMutators.setLibrariesModalVisibility](state, visibility) {
      state.librariesModalVisibility = visibility;
    },
    [EditBlockMutators.setEnteredLibrary](state, libraryName: string) {
      state.enteredLibrary = libraryName;
    },
    [EditBlockMutators.setChangeLanguageWarningVisible](state, value: boolean) {
      state.changeLanguageWarningVisible = value;
    },
    [EditBlockMutators.setNextLanguageToChangeTo](state, nextLanguage) {
      state.nextLanguageToChangeTo = nextLanguage;
    },
    [EditBlockMutators.resetChangeLanguageModal](state) {
      state.nextLanguageToChangeTo = null;
      state.changeLanguageWarningVisible = false;
      state.replaceCodeWithTemplateChecked = false;
    },
    [EditBlockMutators.setReplaceCodeWithTemplateChecked](state, checked) {
      state.replaceCodeWithTemplateChecked = checked;
    },
    [EditBlockMutators.setFileToSyncWithBlock](state, fileToSync) {
      state.fileToSyncBlockWith = fileToSync;
    },
    [EditBlockMutators.setFileSyncModalVisibility](state, visible) {
      state.fileSyncModalVisible = visible;
    }
  },
  actions: {
    async [EditBlockActions.selectNodeFromOpenProject](context, nodeId: string) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit block pane without loaded project');
        return;
      }

      await context.commit(EditBlockMutators.resetState);

      const node = getNodeDataById(projectStore.openedProject, nodeId);

      if (!node) {
        console.error('Attempted to select unknown block in edit block pane');
        return;
      }

      context.commit(EditBlockMutators.setSelectedNode, node);
      context.commit(EditBlockMutators.setSelectedNodeOriginal, node);

      context.commit(EditBlockMutators.setIsLoadingMetadata, true);

      const savedBlockStatus = await getSavedBlockStatus(node);

      if (savedBlockStatus && context.state.selectedNode) {
        const hasNode = context.state.selectedNode;
        const nodeIdIsSameAsRequestId =
          context.state.selectedNode.saved_block_metadata &&
          context.state.selectedNode.saved_block_metadata.id === savedBlockStatus.id;

        // Check that we still have the same selected node as when this request went out...
        // On slow connections this check is important.
        if (hasNode && nodeIdIsSameAsRequestId) {
          context.commit(EditBlockMutators.setSelectedNodeMetadata, savedBlockStatus);
        }
      }

      context.commit(EditBlockMutators.setIsLoadingMetadata, false);
    },
    async [EditBlockActions.selectCurrentlySelectedProjectNode](context) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject || !projectStore.selectedResource) {
        console.error('Attempted to open edit block pane without loaded project or selected resource');
        return;
      }

      await context.dispatch(EditBlockActions.selectNodeFromOpenProject, projectStore.selectedResource);
    },
    async [EditBlockActions.saveBlock](context, closeAfter?: boolean) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit block pane without loaded project');
        throw new Error('Attempted to open edit block pane without loaded project');
      }

      const node = context.state.selectedNode;

      if (!node) {
        console.error('Missing selected node to save');
        throw new Error('Missing selected node to save');
      }

      if (!context.getters.isEditedBlockValid) {
        console.error('State of block is invalid to save, aborting save');
        throw new Error('State of block is invalid to save, aborting save');
      }

      if (!context.getters.isStateDirty) {
        if (closeAfter) {
          await context.dispatch(EditBlockActions.tryToCloseBlock);
        }

        return;
      }

      await context.dispatch(`project/${ProjectViewActions.updateExistingBlock}`, context.state.selectedNode, {
        root: true
      });

      // Set the "original" to the new block.
      context.commit(EditBlockMutators.setSelectedNodeOriginal, context.state.selectedNode);

      if (closeAfter) {
        await context.dispatch(EditBlockActions.tryToCloseBlock);
      }
    },
    async [EditBlockActions.duplicateBlock](context) {
      if (!context.state.selectedNode) {
        console.error('Cannot duplicate block without a selected block');
        return;
      }

      const projectConfig = context.rootState.project.openedProjectConfig;

      if (!projectConfig) {
        console.error('Missing project config, cannot duplicate block');
        return;
      }

      // Save the block first.
      await context.dispatch(EditBlockActions.saveBlock);

      await safelyDuplicateBlock(context.dispatch, projectConfig, context.state.selectedNode);
    },
    async [EditBlockActions.deleteBlock](context) {
      const projectStore = context.rootState.project;

      if (!projectStore.openedProject) {
        console.error('Attempted to open edit block pane without loaded project');
        return;
      }

      if (!context.state.selectedNode) {
        console.error('Unable to perform delete -- state is invalid of edited block');
        return;
      }

      await context.dispatch('blockLocalCodeSync/stopSyncJobForSelectedBlock', null, { root: true });

      // The array of transitions we need to delete
      const transitions_to_delete: WorkflowRelationship[] = getTransitionsForNode(
        projectStore.openedProject,
        context.state.selectedNode
      );

      // Dispatch an action to delete all of them.
      await Promise.all(
        transitions_to_delete.map(async transition => {
          await context.dispatch(`project/${ProjectViewActions.deleteExistingTransition}`, transition, {
            root: true
          });
        })
      );

      await context.dispatch(`project/${ProjectViewActions.deleteExistingBlock}`, context.state.selectedNode, {
        root: true
      });

      // We need to close the pane and reset the state
      await context.dispatch(EditBlockActions.cancelAndResetBlock);
    },
    async [EditBlockActions.tryToCloseBlock](context) {
      // We don't have a selected node, so we don't need to do anything.
      if (!context.state.selectedNode) {
        return;
      }

      // If we have changes that we are going to discard, then ask the user to confirm destruction.
      if (context.getters.isStateDirty) {
        context.commit(EditBlockMutators.setConfirmDiscardModalVisibility, true);
        return;
      }

      // Otherwise, close the pane!
      await context.dispatch(EditBlockActions.cancelAndResetBlock);
    },
    async [EditBlockActions.cancelAndResetBlock](context) {
      // Reset this pane state
      context.commit(EditBlockMutators.resetState);

      // Close this pane
      await context.dispatch(`project/${ProjectViewActions.closePane}`, PANE_POSITION.right, { root: true });
    },
    async [EditBlockActions.runCodeBlock](context) {
      await context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.runEditorCodeBlock, {
        root: true
      });

      // Matt is upset at me for this. Please call him silly names to ease my pain.
      // await context.dispatch(`runLambda/${RunLambdaActions.runLambdaCode}`, null, { root: true });
    },
    async [EditBlockActions.updateSavedBlockVersion](context) {
      const selectedBlock = context.state.selectedNode;

      if (!selectedBlock) {
        console.error('Attempted to update saved block without a selected block');
        return;
      }

      const savedBlockMetadata = selectedBlock.saved_block_metadata;
      const selectedNodeMetadata = context.state.selectedNodeMetadata;

      if (!savedBlockMetadata || !selectedNodeMetadata) {
        console.error('Attempted to update a saved block without valid saved block metadata state');
        return;
      }

      const newMetadata: SavedBlockMetadata = {
        id: selectedNodeMetadata.id,
        version: selectedNodeMetadata.version,
        timestamp: selectedNodeMetadata.timestamp,
        added_timestamp: Date.now()
      };

      const updatedBlock = updateBlockWithNewSavedBlockVersion(selectedBlock, selectedNodeMetadata);

      const newBlock: WorkflowState = {
        ...updatedBlock,
        saved_block_metadata: newMetadata
      };

      context.commit(EditBlockMutators.setSelectedNode, newBlock);
    },
    async [EditBlockActions.kickOffLibraryBuild](context) {
      context.commit(EditBlockMutators.setLibrariesModalVisibility, false);

      // Only perform this action if we are currently authenticated.
      if (!context.rootState.user.authenticated) {
        return;
      }

      if (context.state.selectedNode === null || context.state.selectedNode.type !== WorkflowStateType.LAMBDA) {
        console.error("You don't have a node currently selected so I can't check the build status!");
        return;
      }

      const codeBlock = context.state.selectedNode as LambdaWorkflowState;

      const libraries = deepJSONCopy(codeBlock.libraries);
      const params: libraryBuildArguments = {
        language: codeBlock.language,
        libraries: libraries
      };

      startLibraryBuild(params);
    },
    async [EditBlockActions.showChangeLanguageWarning](context, language: SupportedLanguage) {
      if (!context.state.selectedNode || context.state.selectedNode.type !== WorkflowStateType.LAMBDA) {
        throw new Error('Cannot change language of block that is not a Code Block');
      }

      const selectedBlock = context.state.selectedNode as LambdaWorkflowState;

      // Check if the current block is python and if the next language is python too
      const isCurrentBlockPython =
        selectedBlock.language === SupportedLanguage.PYTHON_2 || selectedBlock.language === SupportedLanguage.PYTHON_3;
      const isNextBlockPython = language === SupportedLanguage.PYTHON_2 || language === SupportedLanguage.PYTHON_3;

      // If we are just swapping Python versions, then leave code + libraries alone.
      if (isCurrentBlockPython && isNextBlockPython) {
        context.commit(EditBlockMutators.setCodeLanguage, language);
        return;
      }

      // Check if the code in the block matches the default code for that language. And that we don't have libraries.
      // If it does, don't prompt a modal when changing the code.
      if (
        selectedBlock.code === DEFAULT_LANGUAGE_CODE[selectedBlock.language] &&
        selectedBlock.libraries.length === 0
      ) {
        // We need to reset the libraries
        // Otherwise you'll have npm libraries when you switch to Python :/
        context.commit(EditBlockMutators.setDependencyImports, []);
        context.commit(EditBlockMutators.setCodeLanguage, language);
        context.commit(EditBlockMutators.setCodeInput, DEFAULT_LANGUAGE_CODE[language]);
        return;
      }

      // Display the modal asking the user if they want to discard their changes.
      context.commit(EditBlockMutators.setNextLanguageToChangeTo, language);
      context.commit(EditBlockMutators.setChangeLanguageWarningVisible, true);
    },
    async [EditBlockActions.changeBlockLanguage](context) {
      const language = context.state.nextLanguageToChangeTo;

      if (!language) {
        throw new Error('No language specified to change to');
      }

      // We need to reset the libraries
      // Otherwise you'll have npm libraries when you switch to Python :/
      context.commit(EditBlockMutators.setDependencyImports, []);
      context.commit(EditBlockMutators.setCodeLanguage, language);

      if (context.state.replaceCodeWithTemplateChecked) {
        context.commit(EditBlockMutators.setCodeInput, DEFAULT_LANGUAGE_CODE[language]);
      }

      // Reset the state
      context.commit(EditBlockMutators.resetChangeLanguageModal);
    },
    async [EditBlockActions.downloadBlockAsZip](context) {
      if (context.rootState.project.openedProject === null) {
        throw new Error('No project is open to download block as zip');
      }

      if (context.state.selectedNode === null || context.state.selectedNode.type !== WorkflowStateType.LAMBDA) {
        throw new Error('No node selected to download');
      }

      const openedProject = context.rootState.project.openedProject;

      const selectedCodeBlock = context.state.selectedNode as LambdaWorkflowState;

      await downloadBlockAsZip(openedProject, selectedCodeBlock);
    },
    async [EditBlockActions.syncBlockWithFile](context) {}
  }
};

export default EditBlockPaneModule;
