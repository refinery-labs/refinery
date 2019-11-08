import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { ProjectViewState, RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import {
  BlockCachedInputIOTypes,
  BlockCachedInputResult,
  GetBlockCachedInputsRequest,
  GetBlockCachedInputsResponse
} from '@/types/api-types';
import { API_ENDPOINT } from '@/constants/api-constants';
import { InputTransformTypes, LambdaWorkflowState } from '@/types/graph';
import { getNodeDataById, getNodesUpstreamFromNode, getSelectedLambdaWorkflowState } from '@/utils/project-helpers';
import { namespace } from 'vuex-class';
import RunLambdaModule from '@/store/modules/run-lambda';
import { ProjectViewActions } from '@/constants/store-constants';

const jq = require('jq-web');

const storeName = StoreType.inputTransformEditor;

export interface suggestedMethodResult {
  suggestedQuery: string;
  queryResult: string;
}

export interface jqOutputResult {
  error: boolean;
  result: string;
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
  selectedLambdaWorkflowState: LambdaWorkflowState | null;
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
  selectedLambdaWorkflowState: null
};

const initialState = deepJSONCopy(moduleState);

async function getJqOutput(jqQuery: string, inputText: string): Promise<jqOutputResult> {
  try {
    const jqOutput = await jq.promised.raw(inputText, jqQuery);
    return {
      error: false,
      result: jqOutput
    };
  } catch (errorDetails) {
    return {
      error: true,
      result: errorDetails.stack.toString()
    };
  }
}

function getSuggestionMethodQueriesFromResult(
  currentJQQuery: string,
  transformedInputData: string,
  inputData: string
): string[] {
  const parsedTransformedInputData = getJSONParsedValue(transformedInputData);

  if (parsedTransformedInputData === null) {
    return [];
  }

  if (currentJQQuery === '.') {
    currentJQQuery = '';
  }
  if (currentJQQuery.endsWith('.')) {
    currentJQQuery.slice(0, -1);
  }

  if (Array.isArray(parsedTransformedInputData) && parsedTransformedInputData.length > 0) {
    return [currentJQQuery + '[0]', currentJQQuery + '[-1]'];
  } else if (typeof parsedTransformedInputData === 'object' && parsedTransformedInputData !== null) {
    return Object.keys(parsedTransformedInputData).map(objectKey => {
      return currentJQQuery + '.' + objectKey;
    });
  }

  return [];
}

async function getSuggestedMethodResultFromQueries(queries: string[], inputData: string) {
  return Promise.all(
    queries.map(async query => {
      const jqOutput = await getJqOutput(query, inputData);
      return {
        suggestedQuery: query,
        queryResult: jqOutput.result
      };
    })
  );
}

async function getCachedInputsForSelectedBlock(project: ProjectViewState | null) {
  const selectedWorkflowState = getSelectedLambdaWorkflowState(project);

  if (selectedWorkflowState === null || project === null || project.openedProject === null) {
    return [];
  }

  // Pull all cached inputs for the current block
  const cachedBlockInputsPromise = makeApiRequest<GetBlockCachedInputsRequest, GetBlockCachedInputsResponse>(
    API_ENDPOINT.GetBlockCachedInputs,
    {
      block_ids: [selectedWorkflowState.id],
      io_type: BlockCachedInputIOTypes.Input
    }
  );

  // Get IDs of blocks with transitions pointing to the current block
  // Their RETURN data will logically be the INPUT data to this Code Block.
  // TODO: Address the `merge`, `fan-in`, `fan-out` cases.
  const upstreamBlocksWithNull = getNodesUpstreamFromNode(project.openedProject, selectedWorkflowState);

  const upstreamBlockIds = upstreamBlocksWithNull
    .filter(upstreamBlock => upstreamBlock !== null)
    .map(blockData => {
      // TypeScript is wrong? We filter for nulls above.
      // @ts-ignore
      return blockData.id;
    });

  const cachedBlockReturnsPromise = makeApiRequest<GetBlockCachedInputsRequest, GetBlockCachedInputsResponse>(
    API_ENDPOINT.GetBlockCachedInputs,
    {
      block_ids: upstreamBlockIds,
      io_type: BlockCachedInputIOTypes.Return
    }
  );

  // Did this so they'd be done in parallel
  const cachedBlockInputs = await cachedBlockInputsPromise;
  const cachedBlockReturns = await cachedBlockReturnsPromise;

  if (cachedBlockInputs === null || cachedBlockReturns === null) {
    return [];
  }

  // Now we enrich the cachedBlocksReturns to add the block name if it exists
  const enrichedCachedBlockReturns = cachedBlockReturns.results.map(cachedBlockReturn => {
    if (project.openedProject === null) {
      return cachedBlockReturn;
    }

    const matchingWorkflowState = getNodeDataById(project.openedProject, cachedBlockReturn.block_id);

    if (matchingWorkflowState === null) {
      return cachedBlockReturn;
    }

    return {
      ...cachedBlockReturn,
      name: matchingWorkflowState.name
    };
  });

  // TODO: Filter by JSON parseable?

  // Only return logged inputs to the block in prod.
  return cachedBlockInputs.results.concat(enrichedCachedBlockReturns);
}

function getJSONParsedValue(inputJSON: string) {
  try {
    return JSON.parse(inputJSON);
  } catch (e) {
    return null;
  }
}

function getInputObjectKeys(inputObjectKeys: string[], targetInputObjectKeys: string[]) {
  // Handle the case of having more keys in the inputObject than the targetObject
  if (inputObjectKeys.length < targetInputObjectKeys.length) {
    // Calculate the difference in number of keys
    const keyCountDifference = targetInputObjectKeys.length - inputObjectKeys.length;

    // Fill the result by just repeating the last input object key
    // Still conveys the idea well enough.
    const finalKey = inputObjectKeys[inputObjectKeys.length - 1];

    return inputObjectKeys.concat(Array(keyCountDifference).fill(finalKey));
  }

  // Handle the case of having more keys in the inputObject than the targetObject
  if (inputObjectKeys.length > targetInputObjectKeys.length) {
    // In this case just cut off the inputObject keys array being returned. Easy.
    return inputObjectKeys.slice(0, targetInputObjectKeys.length);
  }

  // If they are the same number, this is easy
  return inputObjectKeys;
}

export function getExampleMapObjectKeysToTargetKeysQuery(inputData: string, targetInputData: string) {
  const inputDataObject = getJSONParsedValue(inputData);
  const targetInputDataObject = getJSONParsedValue(targetInputData);

  // Both must be parsable.
  if (inputDataObject === null || targetInputDataObject === null) {
    return null;
  }

  // Both must be objects not arrays (even though arrays ARE objects in JavaScript - *deep sigh*)
  if (Array.isArray(inputDataObject) || Array.isArray(targetInputDataObject)) {
    return null;
  }

  // Both must have at least 1 key
  const inputObjectKeys = Object.keys(inputDataObject);
  const targetInputObjectKeys = Object.keys(targetInputDataObject);

  if (inputObjectKeys.length === 0 && targetInputObjectKeys.length === 0) {
    return null;
  }

  // If we have more targetInputObject keys than our inputObject
  // we have to fill in the rest of the keys.
  const updatedInputObjectKeys = getInputObjectKeys(inputObjectKeys, targetInputObjectKeys);

  // Generate parts of the JQ query
  const queryStringParts = targetInputObjectKeys.map((targetInputObjectKey, index) => {
    return `${JSON.stringify(targetInputObjectKey)}: .${updatedInputObjectKeys[index]}`;
  });

  const queryString = `{ ${queryStringParts.join(', ')} }`;

  return queryString;
}

const runLambda = namespace('runLambda');

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
  public selectedLambdaWorkflowState: LambdaWorkflowState | null = initialState.selectedLambdaWorkflowState;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setSelectedLambdaWorkflowState(value: LambdaWorkflowState | null) {
    this.selectedLambdaWorkflowState = deepJSONCopy(value);
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
  public setLambdaWorkflowStateQuery(value: string) {
    if (this.selectedLambdaWorkflowState === null) {
      return;
    }

    this.selectedLambdaWorkflowState.transform = {
      type: InputTransformTypes.JQ,
      transform: value
    };
  }

  @Action
  public async setDefaultInputData() {
    this.setInputData('{}');
    this.setTransformedInputData('{}');
  }

  @Action async updateInputData(newInput: string) {
    this.setInputData(newInput);
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
    this.setLambdaWorkflowStateQuery(this.jqQuery);

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
  public async initializeTransformEditor() {
    const lambdaWorkflowState = getSelectedLambdaWorkflowState(this.context.rootState.project);

    if (lambdaWorkflowState === null) {
      console.error('Error, no Code Block is selected!');
      return;
    }

    // Pull the transform contents if they exist
    if (lambdaWorkflowState.transform !== null && lambdaWorkflowState.transform.type === InputTransformTypes.JQ) {
      this.setJqQuery(lambdaWorkflowState.transform.transform);
    }

    // Pull selected block and copy to store for later use
    this.setSelectedLambdaWorkflowState(lambdaWorkflowState);

    // Set up cached block inputs
    const cachedBlockInputs = await getCachedInputsForSelectedBlock(this.context.rootState.project);
    this.setCachedBlockInputs(cachedBlockInputs);

    if (cachedBlockInputs.length > 0) {
      this.setCachedBlockInput(cachedBlockInputs[0].id);
      this.updateSuggestions();
    }

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

    // Nothing further to do if we're not opening the modal
    if (isVisible !== true) {
      return;
    }

    this.initializeTransformEditor();
  }

  @Action
  public async saveCodeBlockInputTransform() {
    console.log('Saving change to block...');
    await this.context.dispatch(
      `project/${ProjectViewActions.updateExistingBlock}`,
      deepJSONCopy(this.selectedLambdaWorkflowState),
      {
        root: true
      }
    );
  }
}
