import * as R from 'ramda';

export function sortByTimestamp<T>(fn: (i: T) => number, arr: T[]): T[] {
  return R.sort((a: T, b: T) => fn(a) - fn(b), arr);
}

export function sortByTimestampWith<T>(fn: (i: T) => number): (t: T[]) => T[] {
  return (arr: T[]) => sortByTimestamp(fn, arr);
}

export function mapTuple<T1, T2, T3>(fn: (a: T1, b: T2) => T3, tuple: [T1, T2]) {
  return fn(tuple[0], tuple[1]);
}

export function mapTupleWith<T1, T2, T3>(fn: (a: T1, b: T2) => T3) {
  return (tuple: [T1, T2]) => mapTuple(fn, tuple);
}

/**
 * Takes an object and calls a specified function with the key/value as first two arguments.
 * @param arr Array to turn in key/value tuples
 * @param fn Converter function that takes in key/value and returns a new type.
 */
export function mapObjToKeyValueTuple<T1, T2>(arr: { [key: string]: T1 }, fn: (key: string, a: T1) => T2) {
  /**
   * Creates a key/value pair for each entry in the object
   */
  const keyValueTuples = R.toPairs(arr);

  /**
   * Unpacks each tuple and invokes the converter function
   */
  return R.map(mapTupleWith(fn), keyValueTuples);
}
