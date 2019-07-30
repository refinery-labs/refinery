import { Module } from 'vuex';
import LZString from 'lz-string';
import { AllProjectsState, RootState } from '@/store/store-types';
import { AllProjectsMutators } from '@/constants/store-constants';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import {
  DeleteSavedProjectRequest,
  DeleteSavedProjectResponse,
  SearchSavedProjectsRequest,
  SearchSavedProjectsResponse,
  SearchSavedProjectsResult
} from '@/types/api-types';
import { createNewProjectFromConfig } from '@/utils/new-project-utils';
import { readFileAsText } from '@/utils/dom-utils';
import { unwrapJson, wrapJson } from '@/utils/project-helpers';
import validate from '../../types/export-project.validator';
import ImportableRefineryProject from '@/types/export-project';
import { getShortlinkContents } from '@/store/fetchers/api-helpers';

const moduleState: AllProjectsState = {
  availableProjects: [],
  searchBoxText: '',
  isSearching: false,

  deleteModalVisible: false,
  deleteProjectId: null,
  deleteProjectName: null,

  newProjectInput: null,
  newProjectErrorMessage: null,
  newProjectBusy: false,

  uploadProjectInput: null,
  uploadProjectErrorMessage: null,
  uploadProjectBusy: false,

  importProjectInput: null,
  importProjectErrorMessage: null,
  importProjectBusy: false,

  importProjectFromUrlContent: null,
  importProjectFromUrlError: null,
  importProjectFromUrlBusy: false
};

export enum AllProjectsGetters {
  newProjectInputValid = 'newProjectInputValid',
  uploadProjectInputValid = 'uploadProjectInputValid',
  importProjectInputValid = 'importProjectInputValid',
  importProjectFromUrlValid = 'importProjectFromUrlValid',
  importProjectFromUrlJson = 'importProjectFromUrlJson'
}

export enum AllProjectsActions {
  performSearch = 'performSearch',
  createProject = 'createProject',
  uploadProject = 'uploadProject',
  getUploadFileContents = 'getUploadFileContents',
  importProject = 'importProject',
  importProjectFromDemo = 'importProjectFromDemo',
  openProjectShareLink = 'openProjectShareLink',
  startDeleteProject = 'startDeleteProject',
  deleteProject = 'deleteProject'
}

const AllProjectsModule: Module<AllProjectsState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {
    [AllProjectsGetters.newProjectInputValid]: state => state.newProjectInput !== '',
    [AllProjectsGetters.uploadProjectInputValid]: state =>
      state.uploadProjectInput !== '' && unwrapJson(state.uploadProjectInput) !== null,
    [AllProjectsGetters.importProjectInputValid]: state =>
      state.importProjectInput !== '' && unwrapJson(state.importProjectInput) !== null,
    [AllProjectsGetters.importProjectFromUrlValid]: state => {
      if (state.importProjectFromUrlBusy) {
        return true;
      }

      if (!state.importProjectFromUrlContent) {
        return false;
      }

      try {
        validate(state.importProjectFromUrlContent);
        return true;
      } catch (e) {
        console.error('Invalid JSON schema detected:', e);
        return false;
      }
    },
    [AllProjectsGetters.importProjectFromUrlJson]: state => state.importProjectFromUrlContent
  },
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
      state.newProjectInput = text;
    },
    [AllProjectsMutators.setNewProjectErrorMessage](state, val) {
      state.newProjectErrorMessage = val;
    },
    [AllProjectsMutators.setNewProjectBusy](state, val) {
      state.newProjectBusy = val;
    },

    [AllProjectsMutators.setUploadProjectInput](state, text) {
      state.uploadProjectInput = text;
    },
    [AllProjectsMutators.setUploadProjectErrorMessage](state, val) {
      state.uploadProjectErrorMessage = val;
    },
    [AllProjectsMutators.setUploadProjectBusy](state, val) {
      state.uploadProjectBusy = val;
    },

    [AllProjectsMutators.setImportProjectInput](state, text) {
      state.importProjectInput = text;
    },
    [AllProjectsMutators.setImportProjectErrorMessage](state, val) {
      state.importProjectErrorMessage = val;
    },
    [AllProjectsMutators.setImportProjectBusy](state, val) {
      state.importProjectBusy = val;
    },

    [AllProjectsMutators.setImportProjectFromUrlContent](state, val) {
      state.importProjectFromUrlContent = val;
    },
    [AllProjectsMutators.setImportProjectFromUrlError](state, error) {
      state.importProjectFromUrlError = error;
    },
    [AllProjectsMutators.setImportProjectFromUrlBusy](state, val) {
      state.importProjectFromUrlBusy = val;
    }
  },
  actions: {
    async [AllProjectsActions.performSearch](context) {
      context.commit(AllProjectsMutators.setSearchingStatus, true);

      const result = await makeApiRequest<SearchSavedProjectsRequest, SearchSavedProjectsResponse>(
        API_ENDPOINT.SearchSavedProjects,
        {
          query: context.state.searchBoxText
        }
      );

      if (!result || !result.success) {
        // TODO: Handle this error case
        console.error('Failure to retrieve available projects');
        context.commit(AllProjectsMutators.setSearchingStatus, false);
        return;
      }

      context.commit(AllProjectsMutators.setAvailableProjects, result.results);
      context.commit(AllProjectsMutators.setSearchingStatus, false);
    },
    async [AllProjectsActions.createProject](context) {
      if (!context.getters[AllProjectsGetters.newProjectInputValid] || context.state.newProjectInput === null) {
        return;
      }

      await createNewProjectFromConfig({
        setStatus: status => context.commit(AllProjectsMutators.setNewProjectBusy, status),
        setError: (message: string | null) => context.commit(AllProjectsMutators.setNewProjectErrorMessage, message),
        unknownError: 'Error creating project!',
        navigateToNewProject: true,
        name: context.state.newProjectInput
      });

      // Reset if we didn't hit any errors
      if (!context.state.newProjectErrorMessage) {
        context.commit(AllProjectsMutators.setNewProjectInput, null);
      }
    },
    async [AllProjectsActions.uploadProject](context) {
      if (!context.getters[AllProjectsGetters.uploadProjectInputValid] || context.state.uploadProjectInput === null) {
        return;
      }

      await createNewProjectFromConfig({
        setStatus: status => context.commit(AllProjectsMutators.setUploadProjectBusy, status),
        setError: (message: string | null) => context.commit(AllProjectsMutators.setUploadProjectErrorMessage, message),
        unknownError: 'Error uploading project!',
        navigateToNewProject: true,
        json: context.state.uploadProjectInput
      });

      // Reset if we didn't hit any errors
      if (!context.state.uploadProjectErrorMessage) {
        context.commit(AllProjectsMutators.setUploadProjectInput, null);
      }
    },
    async [AllProjectsActions.importProject](context) {
      if (!context.getters[AllProjectsGetters.importProjectInputValid] || context.state.importProjectInput === null) {
        return;
      }

      await createNewProjectFromConfig({
        setStatus: status => context.commit(AllProjectsMutators.setImportProjectBusy, status),
        setError: (message: string | null) => context.commit(AllProjectsMutators.setImportProjectErrorMessage, message),
        unknownError: 'Error importing project!',
        navigateToNewProject: true,
        json: context.state.importProjectInput
      });

      // Reset if we didn't hit any errors
      if (!context.state.importProjectErrorMessage) {
        context.commit(AllProjectsMutators.setImportProjectInput, null);
      }
    },
    async [AllProjectsActions.importProjectFromDemo](context) {
      const projectContents = context.rootState.project.openedProject;

      if (!projectContents) {
        context.commit(AllProjectsMutators.setImportProjectFromUrlError);
        return;
      }

      const projectJson = wrapJson(projectContents);

      if (!projectJson) {
        throw new Error('Unable to serialize project for import');
      }

      await createNewProjectFromConfig({
        setStatus: status => context.commit(AllProjectsMutators.setImportProjectBusy, status),
        setError: (message: string | null) => context.commit(AllProjectsMutators.setImportProjectFromUrlError, message),
        unknownError: 'Error importing project!',
        navigateToNewProject: true,
        json: projectJson
      });

      // Reset if we didn't hit any errors
      if (!context.state.importProjectFromUrlError) {
        context.commit(AllProjectsMutators.setImportProjectFromUrlError, null);
      }
    },
    async [AllProjectsActions.openProjectShareLink](context) {
      const urlParams = new URLSearchParams(document.location.search);

      const shortlink = urlParams.get('q');
      if (shortlink) {
        context.commit(AllProjectsMutators.setImportProjectFromUrlBusy, true);

        const response = await getShortlinkContents(shortlink);

        context.commit(AllProjectsMutators.setImportProjectFromUrlBusy, false);

        if (!response) {
          context.commit(AllProjectsMutators.setImportProjectFromUrlError, 'Invalid project shortlink');
          return;
        }

        context.commit(AllProjectsMutators.setImportProjectFromUrlContent, response);

        return;
      }

      const rawHash = window.location.hash;
      if (rawHash && rawHash.length > 0) {
        const compressedData = window.location.hash.slice(1);
        try {
          const importProjectHashContent = LZString.decompressFromEncodedURIComponent(compressedData);

          const parsed = unwrapJson<ImportableRefineryProject>(importProjectHashContent);

          context.commit(AllProjectsMutators.setImportProjectFromUrlContent, parsed);
        } catch (e) {
          context.commit(AllProjectsMutators.setImportProjectFromUrlError, 'Invalid project data');
          console.error('Invalid project hash data', e);
        }
        return;
      }

      context.commit(AllProjectsMutators.setImportProjectFromUrlError, 'Missing project data');
    },
    async [AllProjectsActions.getUploadFileContents](context, e: Event) {
      try {
        const fileContents = await readFileAsText(e);
        context.commit(AllProjectsMutators.setUploadProjectInput, fileContents);
      } catch (e) {
        context.commit(AllProjectsMutators.setUploadProjectErrorMessage, 'Unable to read file.');
      }
    },
    [AllProjectsActions.startDeleteProject](context, project: SearchSavedProjectsResult) {
      context.commit(AllProjectsMutators.setDeleteProjectId, project.id);
      context.commit(AllProjectsMutators.setDeleteProjectName, project.name);
      context.commit(AllProjectsMutators.setDeleteModalVisibility, true);
    },
    async [AllProjectsActions.deleteProject](context) {
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

        await context.dispatch(AllProjectsActions.performSearch);
      } catch (e) {
        console.error('Unable to delete project');
      }
    }
  }
};

export default AllProjectsModule;
