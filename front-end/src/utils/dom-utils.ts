export function onInputChangedHandler(fn: Function, e: Event) {
  if (!e || !e.target) {
    return;
  }

  // This is certainly annoying
  fn((e.target as HTMLInputElement).value);
}
