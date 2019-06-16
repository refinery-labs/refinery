export function deepJSONCopy(input_object: Object) {
  try {
    return JSON.parse(JSON.stringify(input_object));
  } catch (e) {
    console.error('An error occurred while performing a deep JSON copy of the object: ', e);
    throw e;
  }
}
