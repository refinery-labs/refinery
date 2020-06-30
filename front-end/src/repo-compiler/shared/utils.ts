import { REPO_DEFAULT_README } from '@/repo-compiler/shared/constants';

export function getPlaceholderReadmeContent(projectName: string) {
  return `
# ${projectName} 

${REPO_DEFAULT_README}
`;
}
