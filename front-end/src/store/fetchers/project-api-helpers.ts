import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { SearchSavedProjectsRequest, SearchSavedProjectsResponse } from '@/types/api-types';
import { API_ENDPOINT } from '@/constants/api-constants';
import { RefineryProject } from '@/types/graph';
import { openProject } from '@/store/fetchers/api-helpers';

export async function searchSavedProjects(searchString: string | null) {
  const result = await makeApiRequest<SearchSavedProjectsRequest, SearchSavedProjectsResponse>(
    API_ENDPOINT.SearchSavedProjects,
    {
      query: searchString
    }
  );

  if (!result || !result.success) {
    return null;
  }

  return result;
}

/**
 * Figures out if a newer version of the project is available.
 * @param project {RefineryProject} Instance of the project to query the server against.
 */
export async function isNewerVersionAvailableForProject(project: RefineryProject) {
  // Check if a new version has been created during edit phase
  const currentProject = await openProject({
    demo_project: false,
    version: project.version + 1,
    project_id: project.project_id
  });

  if (!currentProject) {
    // Probably the project was deleted
    return true;
  }

  return currentProject.version !== project.version;
}
