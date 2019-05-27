/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import {ProjectViewState, RootState} from '@/store/store-types';
// @ts-ignore
import complexProject from '../fake-project-data/complex-data';
import {BaseRefineryResource, CyElements, CyStyle, RefineryProject} from '@/types/graph';
import {generateCytoscapeElements, generateCytoscapeStyle} from '@/lib/refinery-to-cytoscript-converter';
import {LayoutOptions} from 'cytoscape';
import cytoscape from '@/components/CytoscapeGraph';
import {ProjectViewMutators} from '@/constants/store-constants';
import {getApiClient} from '@/store/fetchers/refinery-api';
import {API_ENDPOINT} from '@/constants/api-constants';
import {GetSavedProjectRequest, GetSavedProjectResponse} from '@/types/api-types';

export function unwrapProjectJson(response: GetSavedProjectResponse) {
  try {
    return JSON.parse(response.project_json) as RefineryProject;
  } catch {
    return null;
  }
}

const moduleState: ProjectViewState = {
  openedProject: null,
  selectedResource: null,
  cytoscapeElements: null,
  cytoscapeStyle: null,
  cytoscapeLayoutOptions: null,
  cytoscapeConfig: null
};

const SettingModule: Module<ProjectViewState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [ProjectViewMutators.setOpenedProject](state, project) {
      state.openedProject = project;
    },
    [ProjectViewMutators.selectedResource](state, resource: BaseRefineryResource) {
      state.selectedResource = resource;
    },
    [ProjectViewMutators.setCytoscapeElements](state, elements: CyElements) {
      state.cytoscapeElements = elements;
    },
    [ProjectViewMutators.setCytoscapeStyle](state, stylesheet: CyStyle) {
      state.cytoscapeStyle = stylesheet;
    },
    [ProjectViewMutators.setCytoscapeLayout](state, layout: LayoutOptions) {
      state.cytoscapeLayoutOptions = layout;
    },
    [ProjectViewMutators.setCytoscapeConfig](state, config: cytoscape.CytoscapeOptions) {
      state.cytoscapeConfig = config;
    }
  },
  actions: {
    async openProject(context, request: GetSavedProjectRequest) {
      const getProjectClient = getApiClient(API_ENDPOINT.GetSavedProject);
      
      const projectResult = await getProjectClient(request) as GetSavedProjectResponse;
      
      if (!projectResult.success) {
        // TODO: Handle error gracefully
        console.error('Unable to open project!');
        return;
      }
      
      const project = unwrapProjectJson(projectResult);
      
      if (!project) {
        // TODO: Handle error gracefully
        console.error('Unable to read project from server');
        return;
      }
      
      const elements = generateCytoscapeElements(project);
  
      const stylesheet = generateCytoscapeStyle();
  
      context.commit(ProjectViewMutators.setOpenedProject, project);
      context.commit(ProjectViewMutators.setCytoscapeElements, elements);
      context.commit(ProjectViewMutators.setCytoscapeStyle, stylesheet);
    },
    selectNode(context, nodeId: string) {
      if (!context.state.openedProject) {
        console.error('Attempted to select node without opened project', nodeId);
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }
  
      const nodes = context.state.openedProject.workflow_states.filter(e => e.id === nodeId);
  
      if (nodes.length === 0) {
        console.error('No node was found with id', nodeId);
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }
      
      // TODO: Figure out how to check for "dirty" state, likely via using:
      // context.rootState
      
      context.commit(ProjectViewMutators.selectedResource, nodes[0].id);
    },
    selectEdge(context, edgeId: string) {
      if (!context.state.openedProject) {
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }
      
      const edges = context.state.openedProject.workflow_relationships.filter(e => e.id === edgeId);
  
      if (edges.length === 0) {
        console.error('No edge was found with id', edgeId);
        context.commit(ProjectViewMutators.selectedResource, null);
        return;
      }
      
      context.commit(ProjectViewMutators.selectedResource, edges[0].id);
    }
  }
};

export default SettingModule;
