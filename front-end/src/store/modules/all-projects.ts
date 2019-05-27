/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import {AllProjectsState, RootState} from '@/store/store-types';
import {AllProjectsMutators} from '@/constants/store-constants';
import {apiClientMap, getApiClient} from '@/store/fetchers/refinery-api';
import {API_ENDPOINT} from '@/constants/api-constants';
import {SearchSavedProjectsResponse} from '@/types/api-types';

const moduleState: AllProjectsState = {
  availableProjects: [],
  searchBoxText: '',
  isSearching: false
};

const AllProjectsModule: Module<AllProjectsState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [AllProjectsMutators.setSearchingStatus](state, isSearching) {
      state.isSearching = isSearching;
    },
    [AllProjectsMutators.setAvailableProjects](state, results) {
      state.availableProjects = results;
    },
    [AllProjectsMutators.setSearchBoxInput](state, text) {
      state.searchBoxText = text;
    }
  },
  actions: {
    async performSearch(context) {
      context.commit(AllProjectsMutators.setSearchingStatus, true);
  
      const searchSavedProjects = getApiClient(API_ENDPOINT.SearchSavedProjects);
      
      const result = await searchSavedProjects({
        query: context.state.searchBoxText
      }) as SearchSavedProjectsResponse;
      
      if (!result.success) {
        // TODO: Handle this error case
        console.error('Failure to retrieve available projects');
        context.commit(AllProjectsMutators.setSearchingStatus, false);
        return;
      }
      
      context.commit(AllProjectsMutators.setAvailableProjects, result.results);
      context.commit(AllProjectsMutators.setSearchingStatus, false);
    }
  }
};

export default AllProjectsModule;
