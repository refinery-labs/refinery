import { HTTP_METHOD } from '@/constants/api-constants';

export interface IHttpResponse<T> extends Response {
  parsedBody?: T;
}

export const http = <T>(request: RequestInfo): Promise<IHttpResponse<T>> => {
  return new Promise((resolve, reject) => {
    let response: IHttpResponse<T>;
    fetch(request)
      .then(res => {
        response = res;
        return res.json();
      })
      .then(body => {
        if (response.ok) {
          response.parsedBody = body;
          resolve(response);
        } else {
          reject(response);
        }
      })
      .catch(err => {
        reject(err);
      });
  });
};

export async function getRequest<T>(path: string, args: {}) {
  return await http<T>(
    new Request(path, {
      method: 'get',
      credentials: 'include',
      mode: 'cors',
      headers: {
        'X-CSRF-Validation-Header': 'False'
      },
      ...args
    })
  );
}

export async function postRequest<TReq, TRes>(path: string, body: TReq, args: {}) {
  return await http<TRes>(
    new Request(path, {
      method: 'post',
      credentials: 'include',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Validation-Header': 'False'
      },
      body: JSON.stringify(body),
      ...args
    })
  );
}

export async function putRequest<TReq, TRes>(path: string, body: TReq, args: {}) {
  return await http<TRes>(
    new Request(path, {
      method: 'put',
      credentials: 'include',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Validation-Header': 'False'
      },
      body: JSON.stringify(body),
      ...args
    })
  );
}

export async function deleteRequest<TReq, TRes>(path: string, body: TReq, args: {}) {
  return await http<TRes>(
    new Request(path, {
      method: 'delete',
      credentials: 'include',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Validation-Header': 'False'
      },
      body: JSON.stringify(body),
      ...args
    })
  );
}

export async function optionsRequest<TReq, TRes>(path: string, body: TReq, args: {}) {
  return await http<TRes>(
    new Request(path, {
      method: 'options',
      credentials: 'include',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Validation-Header': 'False'
      },
      body: JSON.stringify(body),
      ...args
    })
  );
}

export async function headRequest<TReq, TRes>(path: string, body: TReq, args: {}) {
  return await http<TRes>(
    new Request(path, {
      method: 'head',
      credentials: 'include',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Validation-Header': 'False'
      },
      ...args
    })
  );
}

export async function patchRequest<TReq, TRes>(path: string, body: TReq, args: {}) {
  return await http<TRes>(
    new Request(path, {
      method: 'options',
      credentials: 'include',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Validation-Header': 'False'
      },
      body: JSON.stringify(body),
      ...args
    })
  );
}

export type HttpMethodLookup = {
  [key in HTTP_METHOD]: <TReq, TRes>(path: string, req: TReq) => Promise<IHttpResponse<TRes>>
};

export const HttpUtil: HttpMethodLookup = {
  [HTTP_METHOD.GET]: async (path, args?) => await getRequest(path, args),
  [HTTP_METHOD.POST]: async (path, body, args?) => await postRequest(path, body, args),
  [HTTP_METHOD.DELETE]: async (path, body, args?) => await deleteRequest(path, body, args),
  [HTTP_METHOD.OPTIONS]: async (path, body, args?) => await optionsRequest(path, body, args),
  [HTTP_METHOD.HEAD]: async (path, body, args?) => await headRequest(path, body, args),
  [HTTP_METHOD.PATCH]: async (path, body, args?) => await patchRequest(path, body, args),
  [HTTP_METHOD.PUT]: async (path, body, args?) => await putRequest(path, body, args),
  ANY: async (path, body, args?) => {
    throw new Error('Not implemented');
  }
};
