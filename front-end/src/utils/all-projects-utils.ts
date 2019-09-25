import { SearchSavedProjectsResult } from '@/types/api-types';
import { ProjectCardStateLookup } from '@/types/all-project-types';

export function getInitialCardStateForSearchResults(results: SearchSavedProjectsResult[]): ProjectCardStateLookup {
  const initialState: ProjectCardStateLookup = {};

  return results.reduce((output, result) => {
    output[result.id] = {
      selectedVersion: result.versions[0]
    };

    return output;
  }, initialState);
}
