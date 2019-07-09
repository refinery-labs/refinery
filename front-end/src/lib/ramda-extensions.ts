import * as R from 'ramda';
import {StringIndexable} from '@/types/generic-types';

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
export function mapObjToKeyValueTuple<T1, T2>(fn: (key: string, a: T1) => T2, arr: { [key: string]: T1 }) {
  /**
   * Creates a key/value pair for each entry in the object
   */
  const keyValueTuples = R.toPairs(arr);

  /**
   * Unpacks each tuple and invokes the converter function
   */
  return R.map(mapTupleWith(fn), keyValueTuples);
}

export function groupToArrayBy<T1>(fn: (t: T1) => string | number, arr: T1[]): StringIndexable<T1[]> {
  const outArr: StringIndexable<T1[]> = {};

  return arr.reduce(((previousValue, currentValue) => {
    const key = fn(currentValue);

    // Create an array to hold the values
    if (!previousValue[key]) {
      previousValue[key] = [];
    }

    previousValue[key].push(currentValue);

    return previousValue;
  }), outArr);
}
