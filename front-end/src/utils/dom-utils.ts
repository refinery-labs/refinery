import { syncFileIdPrefix } from '@/store/modules/panes/block-local-code-sync';

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

export function getFileFromElementByQuery(query: string) {
  const fileInputElement = document.querySelector(query);

  if (!fileInputElement) {
    return null;
  }

  return getFileFromElement(fileInputElement as HTMLInputElement);
}

/**
 * Given an event emitted by a File Input element change event, grab the file associated.
 * @param e Event emmited by a File input element change event
 */
export function getFileFromEvent(e: Event): File | null {
  if (!e.target) {
    return null;
  }

  return getFileFromElement(e.target as HTMLInputElement);
}

export function getFileFromElement(element: HTMLInputElement) {
  if (element.type !== 'file' || element.files === null || element.files.length === 0) {
    return null;
  }

  return element.files[0];
}

/**
 * Wraps up the file reader API into an async friendly helper function.
 * @param file Input file from element to read contents from.
 * @return Null if the file contents are empty or invalid. String otherwise.
 */
export async function readFileAsText(file: File): Promise<string | null> {
  if (!file) {
    return null;
  }

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

export function copyElementToDocumentBody(selector: string) {
  const elementToMove = document.querySelector(selector);
  const body = document.querySelector('body');

  if (!body || !elementToMove) {
    throw new Error('Unable to move element to body: ' + selector);
  }

  body.appendChild(elementToMove);
}
