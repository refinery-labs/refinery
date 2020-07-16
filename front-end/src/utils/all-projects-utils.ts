import { SearchSavedProjectsResult } from '@/types/api-types';
import { ProjectCardStateLookup } from '@/types/all-project-types';

export function getInitialCardStateForSearchResults(results: SearchSavedProjectsResult[]): ProjectCardStateLookup {
  return results.reduce((output, result) => {
    output[result.id] = {
      selectedVersion: result.versions[0] && result.versions[0].version
    };

    return output;
  }, {} as ProjectCardStateLookup);
}
