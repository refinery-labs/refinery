import {HTTP_METHOD} from '@/constants/api-constants';

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

export const get = async <T>(
  path: string,
  args: RequestInit = {
    method: "get",
    mode: 'cors',
    headers: {
      'X-CSRF-Validation-Header': "False"
    }
  }
): Promise<IHttpResponse<T>> => {
  return await http<T>(new Request(path, args));
};

export const post = async <T>(
  path: string,
  body: any,
  args: RequestInit = {
    method: "post",
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Validation-Header': "False"
    },
    body: JSON.stringify(body)
  }
): Promise<IHttpResponse<T>> => {
  return await http<T>(new Request(path, args));
};

export const put = async <T>(
  path: string,
  body: any,
  args: RequestInit = {
    method: "put",
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Validation-Header': "False"
    },
    body: JSON.stringify(body)
  }
): Promise<IHttpResponse<T>> => {
  return await http<T>(new Request(path, args));
};

export const deleteRequest = async <T>(
  path: string,
  body: any,
  args: RequestInit = {
    method: "delete",
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Validation-Header': "False"
    },
    body: JSON.stringify(body)
  }
): Promise<IHttpResponse<T>> => {
  return await http<T>(new Request(path, args));
};

export type HttpMethodLookup = {
  [key in HTTP_METHOD]: <TReq, TRes>(path: string, req: TReq) => Promise<IHttpResponse<TRes>>
}

export const HttpUtil: HttpMethodLookup = {
  [HTTP_METHOD.GET]: async (path, args?) => await get(path, args),
  [HTTP_METHOD.POST]: async (path, body, args?) => await post(path, body, args),
  [HTTP_METHOD.DELETE]: async (path, body, args?) => await deleteRequest(path, body, args),
  [HTTP_METHOD.PUT]: async (path, body, args?) => await put(path, body, args)
};
