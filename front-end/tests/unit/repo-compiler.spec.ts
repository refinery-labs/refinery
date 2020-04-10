import * as Path from 'path';
import LightningFS from '@isomorphic-git/lightning-fs';
import { PromiseFsClient } from 'isomorphic-git';
import * as Fs from 'fs';

const repoCompilerFixtures = Path.join('fixtures', 'repo-compiler');

async function walkDir(dir: string, callback: (path: string) => Promise<void>) {
  await Promise.all(
    Fs.readdirSync(dir).map(async (f: string) => {
      let dirPath = Path.join(dir, f);
      let isDirectory = Fs.statSync(dirPath).isDirectory();
      isDirectory ? await walkDir(dirPath, callback) : await callback(Path.join(dir, f));
    })
  );
}

async function setupFixtures(): Promise<PromiseFsClient> {
  const fs = new LightningFS('tests') as PromiseFsClient;
  await fs.promises.mkdir('tests');
  await walkDir(repoCompilerFixtures, async (path: string) => {
    await fs.promises.writeFile(Path.join('/tests', path), Fs.readFileSync(path));
  });
  return fs;
}

describe('Repo Compiler', () => {
  it('compiler drops from project json to repo', () => {
    expect('').toMatch('');
  });
  it('compiler lifts from project repo to json', () => {
    expect('').toMatch('');
  });
});
