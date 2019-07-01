export function deepJSONCopy<T>(input_object: T) {
  try {
    return JSON.parse(JSON.stringify(input_object)) as T;
  } catch (e) {
    console.error('An error occurred while performing a deep JSON copy of the object: ', e);
    throw e;
  }
}
