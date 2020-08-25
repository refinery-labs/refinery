import slugify from 'slugify';
import { PromiseFsClient } from 'isomorphic-git';
import yaml from 'js-yaml';

export function getFolderName(name: string) {
  return slugify(name).toLowerCase();
}

export async function writeConfig(fs: PromiseFsClient, out: string, data: any) {
  const serializedConfig = yaml.safeDump(data);
  await fs.promises.writeFile(out, serializedConfig);
}

export async function maybeMkdir(fs: PromiseFsClient, path: string) {
  try {
    await fs.promises.lstat(path);
  } catch (e) {
    try {
      await fs.promises.mkdir(path);
    } catch (e) {
      if (e.code !== 'EEXIST') {
        throw e;
      }
    }
  }
}

export async function getUniqueLambdaIdentifier(
  fs: PromiseFsClient,
  lambdaDir: string,
  lambdaId: string
): Promise<string> {
  try {
    await fs.promises.stat(lambdaDir);
    return lambdaId.split('-')[0];
  } catch (e) {
    return '';
  }
}
