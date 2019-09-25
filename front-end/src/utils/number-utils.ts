export function tryParseInt(rawValue: string | string[], defaultValue: any) {
  // Use the first value in the array if there are multiple values handed
  if (Array.isArray(rawValue)) {
    rawValue = rawValue[0];
  }

  try {
    return parseInt(rawValue);
  } catch (e) {
    return defaultValue;
  }
}
