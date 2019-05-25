/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import {RootState, ProjectViewState} from '@/store/store-types';

// @ts-ignore
import complexProject from '../fake-project-data/complex-data';
import {
  BaseRefineryResource,
  CyElements,
  CyStyle,
  RefineryProject
} from '@/types/graph';
import {generateCytoscapeElements, generateCytoscapeStyle} from '@/lib/refinery-to-cytoscript-converter';
import {LayoutOptions} from 'cytoscape';
import cytoscape from '@/components/CytoscapeGraph';

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
    setOpenedProject(state, project) {
      state.openedProject = project;
    },
    selectedResource(state, resource: BaseRefineryResource) {
      state.selectedResource = resource;
    },
    setCytoscapeElements(state, elements: CyElements) {
      state.cytoscapeElements = elements;
    },
    setCytoscapeStyle(state, stylesheet: CyStyle) {
      state.cytoscapeStyle = stylesheet;
    },
    setCytoscapeLayout(state, layout: LayoutOptions) {
      state.cytoscapeLayoutOptions = layout;
    },
    setCytoscapeConfig(state, config: cytoscape.CytoscapeOptions) {
      state.cytoscapeConfig = config;
    }
  },
  actions: {
    openProject(context, projectId: string) {
      // TODO: Fetch the project from the server
      
      const project = complexProject;
      
      const elements = generateCytoscapeElements(project);
  
      const stylesheet = generateCytoscapeStyle();
  
      context.commit('setOpenedProject', project);
      context.commit('setCytoscapeElements', elements);
      context.commit('setCytoscapeStyle', stylesheet);
    },
    selectNode(context, nodeId: string) {
      if (!context.state.openedProject) {
        console.error('Attempted to select node without opened project', nodeId);
        context.commit('selectedResource', null);
        return;
      }
  
      const nodes = context.state.openedProject.workflow_states.filter(e => e.id === nodeId);
  
      if (nodes.length === 0) {
        console.error('No node was found with id', nodeId);
        context.commit('selectedResource', null);
        return;
      }
      
      // TODO: Figure out how to check for "dirty" state, likely via using:
      // context.rootState
      
      context.commit('selectedResource', nodes[0].id);
    },
    selectEdge(context, edgeId: string) {
      if (!context.state.openedProject) {
        context.commit('selectedResource', null);
        return;
      }
      
      const edges = context.state.openedProject.workflow_relationships.filter(e => e.id === edgeId);
  
      if (edges.length === 0) {
        console.error('No edge was found with id', edgeId);
        context.commit('selectedResource', null);
        return;
      }
      
      context.commit('selectedResource', edges[0].id);
    }
  }
};

export default SettingModule;
