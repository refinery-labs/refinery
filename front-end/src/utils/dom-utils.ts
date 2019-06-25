export function onInputChangedHandler(fn: Function, e: Event) {
  if (!e || !e.target) {
    return;
  }

  // This is certainly annoying
  fn((e.target as HTMLInputElement).value);
}

export function preventDefaultWrapper(fn: Function) {
  return (e: Event) => {
    e.preventDefault();
    fn.call(null);
    return;
  };
}

/**
 * Wraps up the file reader API into an async friendly helper function.
 * @param e Event from a file input value change event
 * @return Null if the file contents are empty or invalid. String otherwise.
 */
export async function readFileAsText(e: Event): Promise<string | null> {
  if (!e.target) {
    return null;
  }

  const element = e.target as HTMLInputElement;

  if (element.type !== 'file' || element.files === null || element.files.length === 0) {
    return null;
  }

  const file = element.files[0];

  return await new Promise<string | null>((resolve, reject) => {
    const fr = new FileReader();

    fr.onload = () => {
      resolve(fr.result ? (fr.result as string) : null);
    };
    fr.onabort = () => reject();
    fr.onerror = () => reject();
    fr.readAsText(file);
  });
}
