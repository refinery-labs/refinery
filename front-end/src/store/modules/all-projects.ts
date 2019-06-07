/**
 * Setting store to control layout behavior
 */
import { Module } from 'vuex';
import { AllProjectsState, RootState } from '@/store/store-types';
import { AllProjectsMutators } from '@/constants/store-constants';
import { getApiClient, makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import {
  DeleteSavedProjectRequest,
  DeleteSavedProjectResponse,
  SaveProjectRequest,
  SaveProjectResponse,
  SearchSavedProjectsRequest,
  SearchSavedProjectsResponse,
  SearchSavedProjectsResult
} from '@/types/api-types';
import router from '@/router';
import { DEFAULT_PROJECT_CONFIG } from '@/constants/project-editor-constants';
import { RefineryProject } from '@/types/graph';

const moduleState: AllProjectsState = {
  availableProjects: [],
  searchBoxText: '',
  isSearching: false,

  deleteModalVisible: false,
  deleteProjectId: null,
  deleteProjectName: null,

  newProjectInput: '',
  newProjectInputValid: null,
  newProjectErrorMessage: null
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
    },

    [AllProjectsMutators.setDeleteModalVisibility](state, visible) {
      state.deleteModalVisible = visible;
    },
    [AllProjectsMutators.setDeleteProjectId](state, id) {
      state.deleteProjectId = id;
    },
    [AllProjectsMutators.setDeleteProjectName](state, name) {
      state.deleteProjectName = name;
    },

    [AllProjectsMutators.setNewProjectInput](state, text) {
      state.newProjectInputValid = true;
      state.newProjectInput = text;
    },
    [AllProjectsMutators.setNewProjectInputValid](state, val) {
      state.newProjectInputValid = val;
    },
    [AllProjectsMutators.setNewProjectErrorMessage](state, val) {
      state.newProjectErrorMessage = val;
    }
  },
  actions: {
    async performSearch(context) {
      context.commit(AllProjectsMutators.setSearchingStatus, true);

      const result = await makeApiRequest<SearchSavedProjectsRequest, SearchSavedProjectsResponse>(
        API_ENDPOINT.SearchSavedProjects,
        {
          query: context.state.searchBoxText
        }
      );

      if (!result.success) {
        // TODO: Handle this error case
        console.error('Failure to retrieve available projects');
        context.commit(AllProjectsMutators.setSearchingStatus, false);
        return;
      }

      context.commit(AllProjectsMutators.setAvailableProjects, result.results);
      context.commit(AllProjectsMutators.setSearchingStatus, false);
    },
    async createProject(context) {
      if (context.state.newProjectInput === '') {
        context.commit(AllProjectsMutators.setNewProjectInputValid, false);
        return;
      }

      context.commit(AllProjectsMutators.setNewProjectInputValid, true);
      context.commit(AllProjectsMutators.setSearchingStatus, true);

      try {
        const response = await makeApiRequest<SaveProjectRequest, SaveProjectResponse>(API_ENDPOINT.SaveProject, {
          version: false,
          project_id: false,
          diagram_data: JSON.stringify({ name: context.state.newProjectInput }),
          config: JSON.stringify(DEFAULT_PROJECT_CONFIG)
        });

        context.commit(AllProjectsMutators.setSearchingStatus, false);

        if (!response || !response.success) {
          context.commit(AllProjectsMutators.setNewProjectErrorMessage, 'Error creating project!');
          return;
        }

        router.push({
          name: 'project',
          params: {
            projectId: response.project_id
          }
        });
      } catch (e) {
        context.commit(AllProjectsMutators.setNewProjectErrorMessage, 'Error creating project!');
      }
    },
    startDeleteProject(context, project: SearchSavedProjectsResult) {
      context.commit(AllProjectsMutators.setDeleteProjectId, project.id);
      context.commit(AllProjectsMutators.setDeleteProjectName, project.name);
      context.commit(AllProjectsMutators.setDeleteModalVisibility, true);
    },
    async deleteProject(context) {
      const projectId = context.state.deleteProjectId;

      if (!projectId) {
        console.error('Attempted to delete project but did not specify an ID');
        return;
      }

      context.commit(AllProjectsMutators.setDeleteProjectId, null);
      context.commit(AllProjectsMutators.setDeleteProjectName, null);
      context.commit(AllProjectsMutators.setDeleteModalVisibility, false);

      context.commit(AllProjectsMutators.setSearchingStatus, true);

      try {
        const response = await makeApiRequest<DeleteSavedProjectRequest, DeleteSavedProjectResponse>(
          API_ENDPOINT.DeleteSavedProject,
          {
            id: projectId
          }
        );

        context.commit(AllProjectsMutators.setSearchingStatus, false);

        if (!response || !response.success) {
          console.error('Unable to delete project');
          return;
        }

        await context.dispatch('performSearch');
      } catch (e) {
        console.error('Unable to delete project');
      }
    }
  }
};

export default AllProjectsModule;
