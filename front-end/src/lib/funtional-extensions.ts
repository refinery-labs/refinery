import { StringIndexable } from '@/types/generic-types';

export function groupToArrayBy<T1>(fn: (t: T1) => string | number, arr: T1[]): StringIndexable<T1[]> {
  const outArr: StringIndexable<T1[]> = {};

  return arr.reduce((previousValue, currentValue) => {
    const key = fn(currentValue);

    // Create an array to hold the values
    if (!previousValue[key]) {
      previousValue[key] = [];
    }

    previousValue[key].push(currentValue);

    return previousValue;
  }, outArr);
}

export function removeKeyFromObject<T1 extends keyof T3, T2, T3 extends { [key in keyof T3]: T2 }>(
  lookup: T3,
  removedKey: T1
): T3 {
  return Object.keys(lookup).reduce(
    (out, key) => {
      // Add back every item that isn't the one we want to remove.
      if (key !== removedKey) {
        out[key as keyof typeof lookup] = lookup[key as keyof typeof lookup];
      }

      return out;
    },
    {} as T3
  );
}
