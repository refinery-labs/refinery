import { RefineryGitRepoConfig } from '@/repo-compiler/one-to-many/types';
import LightningFS from '@isomorphic-git/lightning-fs';
import { cloneGitRepo } from '@/repo-compiler/shared/clone-repo';

export async function compileGitToRefinery(repo: RefineryGitRepoConfig) {
  await cloneGitRepo(repo);
}
