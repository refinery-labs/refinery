const isDevelopment = process.env.NODE_ENV !== 'production';

let shimsSet = false;
// Only shim the Monaco stuff if we're not in dev
if (!isDevelopment) {
  __webpack_public_path__ = `${process.env.VUE_APP_API_HOST}/manifest/`;

  setupMonacoShims();
}

async function setupMonacoShims() {
  if (shimsSet) {
    return;
  }

  shimsSet = true;

  await import('monaco-editor/esm/vs/editor/editor.api');
  (window as any).MonacoEnvironment = {
    getWorkerUrl: function(moduleId: any, label: string) {
      if (label === 'editorWorkerService') {
        return '/manifest/editor.worker.js';
      }

      if (label === 'json') {
        return '/manifest/json.worker.js';
      }
      if (label === 'css') {
        return '/manifest/css.worker.js';
      }
      if (label === 'html') {
        return '/manifest/html.worker.js';
      }
      if (label === 'typescript' || label === 'javascript') {
        return '/manifest/typescript.worker.js';
      }

      return '/manifest/editor.worker.js';
    },
    getWorker: function(moduleId: any, label: string) {
      if (label === 'editorWorkerService') {
        return new Worker('/manifest/editor.worker.js');
      }

      if (label === 'json') {
        return new Worker('/manifest/json.worker.js');
      }
      if (label === 'css') {
        return new Worker('/manifest/css.worker.js');
      }
      if (label === 'html') {
        return new Worker('/manifest/html.worker.js');
      }
      if (label === 'typescript' || label === 'javascript') {
        return new Worker('/manifest/typescript.worker.js');
      }

      return new Worker('/manifest/editor.worker.js');
    }
  };
}

// Needed to make Typescript happy?
export const foo = 'foo';
