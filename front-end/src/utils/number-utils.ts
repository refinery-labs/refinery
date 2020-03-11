export function tryParseInt(rawValue: string | string[], defaultValue: any) {
  // Use the first value in the array if there are multiple values handed
  if (Array.isArray(rawValue)) {
    rawValue = rawValue[0];
  }

  try {
    const outputValue = parseInt(rawValue);

    // If we parsed the input as NaN, then return the default.
    if (isNaN(outputValue)) {
      return defaultValue;
    }

    return outputValue;
  } catch (e) {
    return defaultValue;
  }
}

// Taken from: https://stackoverflow.com/a/8076436
export function hashCode(str: string): number {
  let hash = 0,
    i,
    chr;
  if (str.length === 0) return hash;
  for (i = 0; i < str.length; i++) {
    chr = str.charCodeAt(i);
    hash = (hash << 5) - hash + chr;
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
}
