function validatePathHasLeadingSlash(apiPath: string) {
  const pathHead = apiPath.startsWith('/') ? '' : '/';
  return `${pathHead}${apiPath}`;
}

function validatePathTail(apiPath: string) {
  if (apiPath != '/' && apiPath.endsWith('/')) {
    return apiPath.slice(0, -1);
  }
  return apiPath;
}

export function validatePath(apiPath: string) {
  return validatePathTail(validatePathHasLeadingSlash(apiPath));
}

export function nopWrite() {
  // Does nothing on purpose
}
