import { jqOutputResult } from '@/store/modules/panes/input-transform-editor';
import { ProjectViewState } from '@/store/store-types';
import { getNodeDataById, getNodesUpstreamFromNode, getSelectedLambdaWorkflowState } from '@/utils/project-helpers';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import {
  BlockCachedInputIOTypes,
  BlockCachedInputResult,
  GetBlockCachedInputsRequest,
  GetBlockCachedInputsResponse
} from '@/types/api-types';
import { API_ENDPOINT } from '@/constants/api-constants';
const jq = require('jq-web');

/*
    Runs the jq query against all of the known cached block inputs. This is so we can display a
    warning if one of them fails other than the one being immediately displayed.
 */
export async function runQueryAgainstAllCachedBlockInputs(
  jqQuery: string,
  cachedBlockInputs: BlockCachedInputResult[]
) {
  const jqQueryPromises = cachedBlockInputs.map(async cachedBlockInput => {
    const jqResult = await getJqOutput(jqQuery, cachedBlockInput.body);
    return {
      succeeded: !jqResult.error,
      cachedBlockInput: cachedBlockInput
    };
  });

  return Promise.all(jqQueryPromises);
}

// Returns `null` if parsable, otherwise returns string of the error.
export function getJSONParseError(inputText: string) {
  try {
    JSON.parse(inputText);
    return null;
  } catch (e) {
    return e.toString();
  }
}

export async function getJqOutput(jqQuery: string, inputText: string): Promise<jqOutputResult> {
  // If the input is just an empty string treat it as a '.'
  const jqQueryString = jqQuery.trim() === '' ? '.' : jqQuery;
  const JSONParseError = getJSONParseError(inputText);

  // Due to a bug in jq-web we can't pass invalid JSON to it.
  // If we do the future jq-web results will all be empty.
  // To mitigate this bug we validate the JSON first and return
  // the validation error if there is one.
  if (JSONParseError !== null) {
    return {
      error: true,
      result: JSONParseError
    };
  }

  try {
    const jqOutput = await jq.promised.raw(inputText, jqQueryString);
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

export function getSuggestionMethodQueriesFromResult(
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

export async function getSuggestedMethodResultFromQueries(queries: string[], inputData: string) {
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

export async function getCachedInputsForSelectedBlock(project: ProjectViewState | null) {
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

export function getJSONParsedValue(inputJSON: string) {
  try {
    return JSON.parse(inputJSON);
  } catch (e) {
    return null;
  }
}

export function getInputObjectKeys(inputObjectKeys: string[], targetInputObjectKeys: string[]) {
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

  // It is extremely hard to ensure an object is actually a plain object in JavaScript
  if (typeof inputDataObject !== 'object' || typeof targetInputDataObject !== 'object') {
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
