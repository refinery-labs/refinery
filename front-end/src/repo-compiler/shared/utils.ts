import { REPO_DEFAULT_README } from '@/repo-compiler/shared/constants';
import { RefineryProject } from '@/types/graph';

export function getPlaceholderReadmeContent(project: RefineryProject, gitURL: string) {
  const shareRepoByURLLink = `${process.env.VUE_APP_API_HOST}/import?i=${project.project_id}&r=${gitURL}`;
  return `
# ${project.name}

[Deploy to Refinery](${shareRepoByURLLink})

${REPO_DEFAULT_README}
`;
}
