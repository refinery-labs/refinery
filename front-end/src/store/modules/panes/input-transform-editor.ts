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
import { RefineryProject } from '@/types/graph';
import { getNodeDataById, getNodesUpstreamFromNode, getTransitionsToNode } from '@/utils/project-helpers';

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
  jqQuery: string;
  suggestedMethods: suggestedMethodResult[];
  cachedBlockInputs: BlockCachedInputResult[];
}

// Initial State
const moduleState: InputTransformEditorState = {
  isFullScreenEditorModalVisible: false,
  inputData: '{}',
  transformedInputData: '',
  jqQuery: '.',
  suggestedMethods: [],
  cachedBlockInputs: []
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
  const parsedTransformedInputData = JSON.parse(transformedInputData);

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
  if (project === null || project.openedProject === null) {
    console.error("Can't get cached inputs for selected block, no project open!");
    return [];
  }

  // Get selected block
  const selectedBlockId = project.selectedResource;

  if (selectedBlockId === null) {
    console.error("Can't get cached inputs for selected block, no block is selected!");
    return [];
  }

  const workflowState = getNodeDataById(project.openedProject, selectedBlockId);

  // Wow I love null checks, so let's do ANOTHER ONE!
  if (workflowState === null) {
    console.error("Can't get cached inputs for selected block, no block is selected!");
    return [];
  }

  // Pull all cached inputs for the current block
  const cachedBlockInputsPromise = makeApiRequest<GetBlockCachedInputsRequest, GetBlockCachedInputsResponse>(
    API_ENDPOINT.GetBlockCachedInputs,
    {
      block_ids: [selectedBlockId],
      io_type: BlockCachedInputIOTypes.Input
    }
  );

  // Get IDs of blocks with transitions pointing to the current block
  // Their RETURN data will logically be the INPUT data to this Code Block.
  // TODO: Address the `merge`, `fan-in`, `fan-out` cases.
  const upstreamBlocksWithNull = getNodesUpstreamFromNode(project.openedProject, workflowState);

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

@Module({ namespaced: true, name: storeName })
export class InputTransformEditorStore extends VuexModule<ThisType<InputTransformEditorState>, RootState>
  implements InputTransformEditorState {
  public isFullScreenEditorModalVisible: boolean = initialState.isFullScreenEditorModalVisible;
  public inputData: string = initialState.inputData;
  public transformedInputData: string = initialState.transformedInputData;
  public jqQuery: string = initialState.jqQuery;
  public suggestedMethods: suggestedMethodResult[] = initialState.suggestedMethods;
  public cachedBlockInputs: BlockCachedInputResult[] = initialState.cachedBlockInputs;

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setModalVisibility(value: boolean) {
    this.isFullScreenEditorModalVisible = value;
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
      return;
    }

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
  public async setModalVisibilityAction(isVisible: boolean) {
    this.setModalVisibility(isVisible);

    // Nothing further to do if we're not opening the modal
    if (isVisible !== true) {
      return;
    }

    const cachedBlockInputs = await getCachedInputsForSelectedBlock(this.context.rootState.project);
    this.setCachedBlockInputs(cachedBlockInputs);

    if (cachedBlockInputs.length > 0) {
      this.setCachedBlockInput(cachedBlockInputs[0].id);
      this.updateSuggestions();
    }
  }
}
