/* eslint-env browser */

import { GitHttpRequest } from 'isomorphic-git';

export function fromValue(value: object) {
  let queue = [value];
  return {
    next() {
      return Promise.resolve({ done: queue.length === 0, value: queue.pop() });
    },
    return() {
      queue = [];
      return {};
    },
    [Symbol.asyncIterator]() {
      return this;
    }
  };
}

export function getIterator(iterable: any) {
  if (iterable[Symbol.asyncIterator]) {
    return iterable[Symbol.asyncIterator]();
  }
  if (iterable[Symbol.iterator]) {
    return iterable[Symbol.iterator]();
  }
  if (iterable.next) {
    return iterable;
  }
  return fromValue(iterable);
}

// Currently 'for await' upsets my linters.
export async function forAwait(iterable: any, cb: any) {
  const iter = getIterator(iterable);
  for (;;) {
    const { value, done } = await iter.next();
    if (value) await cb(value);
    if (done) break;
  }
  if (iter.return) iter.return();
}

export async function collect(iterable: any) {
  let size = 0;
  const buffers: any[] = [];
  // This will be easier once `for await ... of` loops are available.
  await forAwait(iterable, (value: any) => {
    buffers.push(value);
    size += value.byteLength;
  });
  const result = new Uint8Array(size);
  let nextIndex = 0;
  for (const buffer of buffers) {
    result.set(buffer, nextIndex);
    nextIndex += buffer.byteLength;
  }
  return result;
}

export function fromStream(stream: any) {
  // Use native async iteration if it's available.
  if (stream[Symbol.asyncIterator]) return stream;
  const reader = stream.getReader();
  return {
    next() {
      return reader.read();
    },
    return() {
      reader.releaseLock();
      return {};
    },
    [Symbol.asyncIterator]() {
      return this;
    }
  };
}

// Sorry for the copy & paste from typedefs.js but if we import typedefs.js we'll get a whole bunch of extra comments
// in the rollup output

/**
 * @typedef {Object} GitHttpRequest
 * @property {string} url - The URL to request
 * @property {string} [method='GET'] - The HTTP method to use
 * @property {Object<string, string>} [headers={}] - Headers to include in the HTTP request
 * @property {AsyncIterableIterator<Uint8Array>} [body] - An async iterator of Uint8Arrays that make up the body of POST requests
 * @property {string} [core] - If your `http` plugin needs access to other plugins, it can do so via `git.cores.get(core)`
 * @property {GitEmitterPlugin} [emitter] - If your `http` plugin emits events, it can do so via `emitter.emit()`
 * @property {string} [emitterPrefix] - The `emitterPrefix` passed by the user when calling a function. If your plugin emits events, prefix the event name with this.
 */

/**
 * @typedef {Object} GitHttpResponse
 * @property {string} url - The final URL that was fetched after any redirects
 * @property {string} [method] - The HTTP method that was used
 * @property {Object<string, string>} [headers] - HTTP response headers
 * @property {AsyncIterableIterator<Uint8Array>} [body] - An async iterator of Uint8Arrays that make up the body of the response
 * @property {number} statusCode - The HTTP status code
 * @property {string} statusMessage - The HTTP status message
 */

/**
 * HttpClient
 *
 * @param {GitHttpRequest} request
 * @returns {Promise<GitHttpResponse>}
 */
export async function request({ body, url, method, headers }: GitHttpRequest) {
  // streaming uploads aren't possible yet in the browser
  if (body) {
    body = (await collect(body)) as Uint8Array;
  }
  const credentials = 'include';
  const res = await fetch(url, { method, headers, body, credentials });
  const iter = res.body && res.body.getReader ? fromStream(res.body) : [new Uint8Array(await res.arrayBuffer())];
  // convert Header object to ordinary JSON
  headers = {};
  for (const [key, value] of res.headers.entries()) {
    // @ts-ignore
    headers[key] = value;
  }
  return {
    url: res.url,
    // @ts-ignore
    method: res.method,
    statusCode: res.status,
    statusMessage: res.statusText,
    body: iter,
    headers: headers
  };
}

export default { request };
