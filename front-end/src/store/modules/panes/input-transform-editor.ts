import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import {
  BlockCachedInputResult,
  DeleteCachedBlockIORequest,
  DeleteCachedBlockIOResponse,
  GetLatestProjectDeploymentRequest,
  GetLatestProjectDeploymentResponse
} from '@/types/api-types';
import {
  InputTransform,
  InputTransformTypes,
  LambdaWorkflowState,
  SupportedLanguage,
  WorkflowStateType
} from '@/types/graph';
import RunLambdaModule from '@/store/modules/run-lambda';
import {
  getCachedInputsForSelectedBlock,
  getJqOutput,
  getSuggestedMethodResultFromQueries,
  getSuggestionMethodQueriesFromResult,
  runQueryAgainstAllCachedBlockInputs
} from '@/utils/transform-utils';
import { EditBlockMutators } from '@/store/modules/panes/edit-block-pane';
import { ProjectViewActions } from '@/constants/store-constants';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import { getLanguageFromFileName } from '@/utils/editor-utils';

const storeName = StoreType.inputTransformEditor;

export interface suggestedMethodResult {
  suggestedQuery: string;
  queryResult: string;
}

export interface jqOutputResult {
  error: boolean;
  result: string;
}

export interface cachedBlockInputTransformRunResult {
  succeeded: boolean;
  cachedBlockInput: BlockCachedInputResult;
}

// Types
export interface InputTransformEditorState {
  isFullScreenEditorModalVisible: boolean;
  inputData: string;
  transformedInputData: string;
  targetInputData: string;
  jqQuery: string;
  suggestedMethods: suggestedMethodResult[];
  cachedBlockInputs: BlockCachedInputResult[];
  isValidQuery: boolean | null;
  inputTransform: InputTransform | null;
  cachedInputTransformRunResults: cachedBlockInputTransformRunResult[];
  cachedInputId: string | null;
}

// Initial State
const moduleState: InputTransformEditorState = {
  isFullScreenEditorModalVisible: false,
  inputData: '{}',
  transformedInputData: '',
  targetInputData: '{}',
  jqQuery: '.',
  suggestedMethods: [],
  cachedBlockInputs: [],
  isValidQuery: null,
  inputTransform: null,
  cachedInputTransformRunResults: [],
  cachedInputId: null
};

const initialState = deepJSONCopy(moduleState);

@Module({ namespaced: true, name: storeName })
export class InputTransformEditorStore extends VuexModule<ThisType<InputTransformEditorState>, RootState>
  implements InputTransformEditorState {
  public isFullScreenEditorModalVisible: boolean = initialState.isFullScreenEditorModalVisible;
  public inputData: string = initialState.inputData;
  public transformedInputData: string = initialState.transformedInputData;
  public targetInputData: string = initialState.targetInputData;
  public jqQuery: string = initialState.jqQuery;
  public suggestedMethods: suggestedMethodResult[] = initialState.suggestedMethods;
  public cachedBlockInputs: BlockCachedInputResult[] = initialState.cachedBlockInputs;
  public isValidQuery: boolean | null = initialState.isValidQuery;
  public inputTransform: InputTransform | null = initialState.inputTransform;
  public cachedInputTransformRunResults: cachedBlockInputTransformRunResult[] =
    initialState.cachedInputTransformRunResults;
  public cachedInputId: string | null = initialState.cachedInputId;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setInputTransform(value: InputTransform | null) {
    this.inputTransform = deepJSONCopy(value);
  }

  @Mutation
  public setModalVisibility(value: boolean) {
    this.isFullScreenEditorModalVisible = value;
  }

  @Mutation
  public setIsValidQuery(value: boolean | null) {
    this.isValidQuery = value;
  }

  @Mutation
  public setJqQuery(value: string) {
    this.jqQuery = value;
  }

  @Mutation
  public setTransformedInputData(value: string) {
    this.transformedInputData = value;
  }

  @Mutation
  public setSuggestedMethods(value: suggestedMethodResult[]) {
    this.suggestedMethods = deepJSONCopy(value);
  }

  @Mutation
  public setCachedBlockInputs(cachedBlockInputs: BlockCachedInputResult[]) {
    this.cachedBlockInputs = deepJSONCopy(cachedBlockInputs);
  }

  @Mutation
  public setInputData(value: string) {
    this.inputData = value;
  }

  @Mutation
  public setTargetInputData(value: string) {
    this.targetInputData = value;
  }

  @Mutation
  public setInputTransformQuery(value: string) {
    const noOpJQTransforms = ['', '.'];

    if (noOpJQTransforms.includes(value.trim())) {
      this.inputTransform = null;
      return;
    }

    this.inputTransform = {
      type: InputTransformTypes.JQ,
      transform: value
    };
  }

  @Mutation
  public setCachedInputTransformRunResult(cachedInputTransformRunResults: cachedBlockInputTransformRunResult[]) {
    this.cachedInputTransformRunResults = deepJSONCopy(cachedInputTransformRunResults);
  }

  @Mutation
  public setCachedInputId(cachedInputId: string) {
    this.cachedInputId = cachedInputId;
  }

  @Action
  public async setDefaultInputData() {
    this.setInputData('{}');
    this.setTransformedInputData('{}');
  }

  @Action
  updateInputData(newInput: string) {
    this.setInputData(newInput);
  }

  @Action
  updateTargetInputData(newInput: string) {
    this.setTargetInputData(newInput);
  }

  @Action
  public async updateCachedBlockInputTransformRunResults() {
    const cachedBlockInputTransformResults = await runQueryAgainstAllCachedBlockInputs(
      this.jqQuery,
      this.cachedBlockInputs
    );

    this.setCachedInputTransformRunResult(cachedBlockInputTransformResults);
  }

  @Action
  public async updateSuggestions() {
    // Run query through JQ
    const jqOutput = await getJqOutput(this.jqQuery, this.inputData);

    // Set the transformed input data text box
    this.setTransformedInputData(jqOutput.result);

    // Don't go any further if the result was an error
    if (jqOutput.error || jqOutput.result === null) {
      this.setSuggestedMethods([]);
      this.setIsValidQuery(false);
      return;
    }

    this.setIsValidQuery(true);

    // Update internal LambdaWorkflowState
    this.setInputTransformQuery(this.jqQuery);

    // Get array of suggested JQ query strings
    const suggestedQueries = await getSuggestionMethodQueriesFromResult(
      this.jqQuery,
      this.transformedInputData,
      this.inputData
    );

    // Evaluate all of the expressions and get the result.
    const suggestedQueriesResults = await getSuggestedMethodResultFromQueries(suggestedQueries, this.inputData);

    // Update suggested methods
    this.setSuggestedMethods(suggestedQueriesResults);
  }

  @Action
  public async setJqQueryAction(value: string) {
    this.setJqQuery(value);
    this.updateSuggestions();

    // Run jq against all of the cached block inputs
    // If any result in an error that is used to warn the
    // user that there may be an issue upon deploying.
    this.updateCachedBlockInputTransformRunResults();
  }

  @Action
  public async setCachedBlockInput(cachedBlockInput: BlockCachedInputResult | null) {
    if (cachedBlockInput === null) {
      this.setDefaultInputData();
      return;
    }

    const cachedInputId = cachedBlockInput.id;

    const matchingCachedBlockInput = this.cachedBlockInputs.filter(cachedBlockInput => {
      return cachedBlockInput.id === cachedInputId;
    });

    this.setCachedInputId(cachedInputId);

    if (matchingCachedBlockInput.length > 0) {
      this.setInputData(matchingCachedBlockInput[0].body);
    }
  }

  @Action
  public async initializeJqQuery(lambdaWorkflowState: LambdaWorkflowState) {
    if (lambdaWorkflowState.transform === null) {
      this.setJqQueryAction('.');
      return;
    }

    if (lambdaWorkflowState.transform.type === InputTransformTypes.JQ) {
      this.setJqQueryAction(lambdaWorkflowState.transform.transform);
    }
  }

  @Action
  public async initializeTransformEditor() {
    // Pull the transform contents if they exist
    const editBlockStore = this.context.rootState.project.editBlockPane;
    if (!editBlockStore) {
      console.error('Edit block pane state is null');
      return;
    }

    if (!editBlockStore.selectedNode || editBlockStore.selectedNode.type !== WorkflowStateType.LAMBDA) {
      console.error('Edit block pane state is null or is an invalid block type.');
      return;
    }
    const lambdaWorkflowState = editBlockStore.selectedNode as LambdaWorkflowState;

    // Set up cached block inputs
    const cachedBlockInputs = await getCachedInputsForSelectedBlock(this.context.rootState.project);
    this.setCachedBlockInputs(cachedBlockInputs);

    if (cachedBlockInputs.length > 0) {
      this.setCachedBlockInput(cachedBlockInputs[0]);
      this.updateSuggestions();
    }

    // Pull existing JQ transform if one exists
    await this.initializeJqQuery(lambdaWorkflowState);

    // Pull selected block input transform and copy to store for later use
    this.setInputTransform(lambdaWorkflowState.transform);

    // Set the setTargetInputData to the Saved Input data for the block
    const selectedResource = this.context.rootState.project.selectedResource;

    // No idea why I have to do this.
    if (RunLambdaModule.getters === undefined) {
      return;
    }

    this.setTargetInputData(
      // Absolutely disgusting, but have no idea how else to do this.
      selectedResource
        ? RunLambdaModule.getters.getDevLambdaInputData(
            this.context.rootState.runLambda,
            this.context.getters,
            this.context.rootState,
            this.context.rootGetters
          )(selectedResource)
        : '{}'
    );
  }

  @Action
  public async setModalVisibilityAction(isVisible: boolean) {
    this.setModalVisibility(isVisible);

    // Reset the state if we close the modal
    if (isVisible !== true) {
      this.resetState();
      return;
    }

    this.initializeTransformEditor();
  }

  @Action
  public async deleteCachedBlockIOById(cachedBlockIOId: string) {
    const deleteCachedBlockIOResponse = await makeApiRequest<DeleteCachedBlockIORequest, DeleteCachedBlockIOResponse>(
      API_ENDPOINT.DeleteCachedBlockIO,
      {
        cached_block_input_id: cachedBlockIOId
      }
    );

    // Remove the deleted cached input and cached transform result from the client side
    const newCachedBlockInputs = this.cachedBlockInputs.filter(
      cachedBlockInput => cachedBlockInput.id !== cachedBlockIOId
    );
    const newCachedBlockInputTransformRunResults = this.cachedInputTransformRunResults.filter(
      cachedInputTransformRunResult => cachedInputTransformRunResult.cachedBlockInput.id !== cachedBlockIOId
    );
    this.setCachedBlockInputs(newCachedBlockInputs);
    this.setCachedInputTransformRunResult(newCachedBlockInputTransformRunResults);

    if (newCachedBlockInputs.length > 0 && newCachedBlockInputs[0] !== null) {
      this.setCachedBlockInput(newCachedBlockInputs[0]);
      return;
    }

    this.setCachedBlockInput(null);
    return;
  }

  @Action
  public async saveCodeBlockInputTransform() {
    const projectStore = this.context.rootState.project;

    if (!projectStore.openedProject) {
      throw new Error("No project is opened, can't save transform!");
    }

    const project = projectStore.openedProject;
    const selectedResource = this.context.rootState.project.selectedResource;

    const block = project.workflow_states.find(block => block.id === selectedResource);

    if (!block || block.type !== WorkflowStateType.LAMBDA) {
      throw new Error('Block selected is not a Code Block, cannot set input transform.');
    }

    const codeBlock = block as LambdaWorkflowState;

    const newBlock: LambdaWorkflowState = {
      ...codeBlock,
      transform: {
        type: InputTransformTypes.JQ,
        transform: this.jqQuery
      }
    };

    await this.context.dispatch(`project/${ProjectViewActions.updateExistingBlock}`, newBlock, { root: true });
    await this.context.commit(`project/editBlockPane/${EditBlockMutators.setInputTransform}`, this.inputTransform, {
      root: true
    });
  }
}
