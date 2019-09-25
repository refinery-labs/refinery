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
