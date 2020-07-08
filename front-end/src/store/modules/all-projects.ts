import { Module } from 'vuex';
import LZString from 'lz-string';
import { AllProjectsState, RootState } from '@/store/store-types';
import { AllProjectsMutators } from '@/constants/store-constants';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import {
  AuthWithGithubRequest,
  AuthWithGithubResponse,
  DeleteSavedProjectRequest,
  DeleteSavedProjectResponse,
  GetProjectVersionsRequest,
  GetProjectVersionsResponse,
  SearchSavedProjectsRequest,
  SearchSavedProjectsResponse,
  SearchSavedProjectsResult,
  SearchSavedProjectVersionMetadata
} from '@/types/api-types';
import { createNewProjectFromConfig } from '@/utils/new-project-utils';
import { getFileFromEvent, readFileAsText } from '@/utils/dom-utils';
import { unwrapJson, wrapJson } from '@/utils/project-helpers';
import validate from '../../types/export-project.validator';
import ImportableRefineryProject from '@/types/export-project';
import { getProjectVersions, getShortlinkContents, renameProject } from '@/store/fetchers/api-helpers';
import { SelectProjectVersion } from '@/types/all-project-types';
import { getInitialCardStateForSearchResults } from '@/utils/all-projects-utils';

const moduleState: AllProjectsState = {
  availableProjects: [],
  searchBoxText: '',
  isSearching: false,

  cardStateByProjectId: {},

  deleteModalVisible: false,
  deleteProjectId: null,
  deleteProjectName: null,

  renameProjectId: null,
  renameProjectInput: null,
  renameProjectBusy: false,
  renameProjectError: null,

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
  getAllProjectVersions = 'getAllProjectVersions',
  createProject = 'createProject',
  uploadProject = 'uploadProject',
  getUploadFileContents = 'getUploadFileContents',
  importProject = 'importProject',
  importProjectFromDemo = 'importProjectFromDemo',
  openProjectShareLink = 'openProjectShareLink',
  startDeleteProject = 'startDeleteProject',
  deleteProject = 'deleteProject',
  renameProject = 'renameProject'
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

    [AllProjectsMutators.setCardStateLookup](state, cardStateLookup) {
      state.cardStateByProjectId = cardStateLookup;
    },
    [AllProjectsMutators.setCardSelectedVersion](state, { projectId, selectedVersion }: SelectProjectVersion) {
      const cardState = {
        ...state.cardStateByProjectId[projectId],
        selectedVersion: selectedVersion
      };

      // New object so that we make sure Vuex reads the update
      state.cardStateByProjectId = {
        ...state.cardStateByProjectId,
        [projectId]: cardState
      };
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

    [AllProjectsMutators.setRenameProjectId](state, id) {
      state.renameProjectId = id;
    },
    [AllProjectsMutators.setRenameProjectInput](state, name) {
      state.renameProjectInput = name;
    },
    [AllProjectsMutators.setRenameProjectBusy](state, busy) {
      state.renameProjectBusy = busy;
    },
    [AllProjectsMutators.setRenameProjectError](state, msg) {
      state.renameProjectError = msg;
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

      context.commit(AllProjectsMutators.setCardStateLookup, getInitialCardStateForSearchResults(result.results));
      context.commit(AllProjectsMutators.setAvailableProjects, result.results.reverse());
      context.commit(AllProjectsMutators.setSearchingStatus, false);
    },
    async [AllProjectsActions.getAllProjectVersions](context, projectId: string) {
      const versions = await getProjectVersions(projectId);

      if (versions === null) {
        return;
      }

      const newAvailableProjects = context.state.availableProjects.reduce((availableProjects, project) => {
        if (project.id === projectId) {
          const updatedProjectResult: SearchSavedProjectsResult = {
            ...project,
            versions
          };
          return [...availableProjects, updatedProjectResult];
        }
        return [...availableProjects, project];
      }, [] as SearchSavedProjectsResult[]);

      context.commit(AllProjectsMutators.setCardStateLookup, getInitialCardStateForSearchResults(newAvailableProjects));
      context.commit(AllProjectsMutators.setAvailableProjects, newAvailableProjects);
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
        const file = getFileFromEvent(e);

        if (!file) {
          context.commit(AllProjectsMutators.setUploadProjectErrorMessage, 'Unable to get file to read.');
          return;
        }

        const fileContents = await readFileAsText(file);
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
    },
    async [AllProjectsActions.renameProject](context, projectId: string) {
      if (context.state.renameProjectId !== null) {
        const renameProjectId = context.state.renameProjectId;

        if (renameProjectId !== projectId) {
          throw new Error('Attempted to finish renaming project with an invalid ID');
        }

        const projectName = context.state.renameProjectInput;

        if (projectName === null) {
          context.commit(AllProjectsMutators.setRenameProjectError, 'Must not set project name to empty value');
          throw new Error('Must not set project name to null value');
        }

        context.commit(AllProjectsMutators.setRenameProjectBusy, true);

        const errorMessage = await renameProject(renameProjectId, projectName);

        context.commit(AllProjectsMutators.setRenameProjectBusy, false);

        if (errorMessage) {
          context.commit(AllProjectsMutators.setRenameProjectError, errorMessage);
          console.error('Error renaming project', errorMessage);
          return;
        }

        // Reset state of the rename flow
        context.commit(AllProjectsMutators.setRenameProjectInput, null);
        context.commit(AllProjectsMutators.setRenameProjectId, null);

        // Refresh list of projects
        await context.dispatch(AllProjectsActions.performSearch);

        return;
      }

      if (!context.state.availableProjects) {
        throw new Error('Unable to rename project without any available projects');
      }

      const matchingProject = context.state.availableProjects.find(p => p.id === projectId);

      if (!matchingProject) {
        throw new Error(
          'Unable to rename project without matching project. Missing project with given ID: ' + projectId
        );
      }

      context.commit(AllProjectsMutators.setRenameProjectId, projectId);

      context.commit(AllProjectsMutators.setRenameProjectInput, matchingProject.name);
    }
  }
};

export default AllProjectsModule;
