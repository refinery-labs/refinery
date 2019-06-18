// This code comes from this module:
// https://www.npmjs.com/package/merge-k-sorted-arrays
// License: MIT

import TinyQueue from 'tinyqueue';

export type ComparatorFn = (a: number, b: number) => 1 | 0 | -1;

const defaultComparator: ComparatorFn = (a, b) => {
  return a < b ? -1 : a > b ? 1 : 0;
};

function mergeSortedArrays(
  arrays: any[],
  options?: ComparatorFn | { comparator: ComparatorFn; outputMetadata: boolean }
) {
  let comparator;
  let outputMetadata;
  if (typeof options === 'function') {
    comparator = options;
  } else if (options) {
    comparator = options.comparator;
    outputMetadata = options.outputMetadata;
  }
  const finalComparator = comparator || defaultComparator;

  function entryComparator(a: any[], b: any[]) {
    return finalComparator(a[2], b[2]);
  }

  const totalLength = arrays.reduce((length, array) => length + array.length, 0);
  const output = new Array(totalLength);
  let outputIndex = 0;

  const initQueue = arrays.reduce((initQueue, array, index) => {
    if (array.length) {
      initQueue.push([index, 0, array[0]]);
    }
    return initQueue;
  }, []);

  const queue = new TinyQueue(initQueue, entryComparator);
  while (queue.length) {
    const entry = queue.pop();
    if (!entry) {
      continue;
    }

    output[outputIndex++] = outputMetadata ? entry : entry[2];
    const array = arrays[entry[0]];
    const nextIndex = entry[1] + 1;
    if (nextIndex < array.length) {
      queue.push([entry[0], nextIndex, array[nextIndex]]);
    }
  }

  return output;
}

export default mergeSortedArrays;
