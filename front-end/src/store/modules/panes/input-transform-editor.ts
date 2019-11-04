import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState, StoreType } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import { resetStoreState } from '@/utils/store-utils';
import { Watch } from 'vue-property-decorator';
import * as monaco from 'monaco-editor';
const jq = require('jq-web');

const storeName = StoreType.inputTransformEditor;

// Just for debug
const defaultInputData = JSON.stringify(
  {
    example: {
      test: [1, 2, 3, 4],
      pewpew: {
        ok: 'lol',
        another: {
          yep: "it's another one",
          array: [2, 4, 6, 8, 10]
        }
      }
    }
  },
  null,
  4
);

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
}

// Initial State
const moduleState: InputTransformEditorState = {
  isFullScreenEditorModalVisible: false,
  inputData: defaultInputData,
  transformedInputData: '',
  jqQuery: '.',
  suggestedMethods: []
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

@Module({ namespaced: true, name: storeName })
export class InputTransformEditorStore extends VuexModule<ThisType<InputTransformEditorState>, RootState>
  implements InputTransformEditorState {
  public isFullScreenEditorModalVisible: boolean = initialState.isFullScreenEditorModalVisible;
  public inputData: string = initialState.inputData;
  public transformedInputData: string = initialState.transformedInputData;
  public jqQuery: string = initialState.jqQuery;
  public suggestedMethods: suggestedMethodResult[] = initialState.suggestedMethods;

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
  public async setModalVisibilityAction(isVisible: boolean) {
    // Perform initial update
    if (isVisible === true) {
      this.updateSuggestions();
    }
    this.setModalVisibility(isVisible);
  }
}
