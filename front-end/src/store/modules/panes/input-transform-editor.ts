import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { BlockCachedInputResult } from '@/types/api-types';
import { InputTransform, InputTransformTypes, LambdaWorkflowState, WorkflowStateType } from '@/types/graph';
import { namespace } from 'vuex-class';
import RunLambdaModule from '@/store/modules/run-lambda';
import {
  getCachedInputsForSelectedBlock,
  getJqOutput,
  getSuggestedMethodResultFromQueries,
  getSuggestionMethodQueriesFromResult,
  runQueryAgainstAllCachedBlockInputs
} from '@/utils/transform-utils';
import { EditBlockMutators } from '@/store/modules/panes/edit-block-pane';

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
  cachedInputTransformRunResults: []
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
    this.cachedBlockInputs = cachedBlockInputs;
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
  public async setCachedBlockInput(cachedBlockInputId: string) {
    const matchingCachedBlockInput = this.cachedBlockInputs.filter(cachedBlockInput => {
      return cachedBlockInput.id === cachedBlockInputId;
    });

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
      this.setCachedBlockInput(cachedBlockInputs[0].id);
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
  public async saveCodeBlockInputTransform() {
    // Update the code of the currently selected block
    await this.context.commit(`project/editBlockPane/${EditBlockMutators.setInputTransform}`, this.inputTransform, {
      root: true
    });
  }
}
