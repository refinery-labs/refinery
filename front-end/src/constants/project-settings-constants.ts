import { NewGitRepoStateType } from '@/types/project-settings-types';

export const newGitRepoStateToLabel: Record<NewGitRepoStateType, string> = {
  [NewGitRepoStateType.REPO_NOT_CREATED]: 'Creating a new repository',
  [NewGitRepoStateType.REPO_CREATED]: 'New repository created, compiling project',
  [NewGitRepoStateType.PROJECT_COMPILED]: 'Pushing project to new repository',
  [NewGitRepoStateType.PROJECT_PUSHED]: ''
};
