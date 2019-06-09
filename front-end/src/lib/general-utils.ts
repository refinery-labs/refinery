export function deepJSONCopy(input_object: Object) {
  return JSON.parse(
    JSON.stringify(
        input_object
    )
  );
}