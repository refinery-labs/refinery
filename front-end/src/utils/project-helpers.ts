import {
  RefineryProject,
  WorkflowRelationship,
  WorkflowRelationshipType,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import {
  nodeTypesWithSimpleTransitions,
  validBlockToBlockTransitionLookup,
  ValidTransitionConfig
} from '@/constants/project-editor-constants';
import { AvailableTransitionsByType, ProjectViewState } from '@/store/store-types';
import { GetSavedProjectResponse } from '@/types/api-types';
import uuid from 'uuid/v4';
import { deepJSONCopy } from '@/lib/general-utils';
import { createNewTransition } from '@/utils/block-utils';
import { BaseGraphHelper } from '@/lib/graph-helpers';
import { Graph } from 'graphlib';
import { addCytoscapeElementsToShadowGraph, recursiveSuccessorMark } from '@/lib/graph-helpers/utils';

export function getNodeDataById(project: RefineryProject, nodeId: string): WorkflowState | null {
  const targetStates = project.workflow_states;

  const results = targetStates.filter(workflowState => {
    return workflowState.id === nodeId;
  });

  if (results.length > 0) {
    return deepJSONCopy(results[0]);
  }

  return null;
}

export function getTransitionDataById(project: RefineryProject, transitionId: string): WorkflowRelationship | null {
  const targetRelationships = project.workflow_relationships;

  const results = targetRelationships.filter(workflowRelationship => {
    return workflowRelationship.id === transitionId;
  });

  if (results.length > 0) {
    return deepJSONCopy(results[0]);
  }

  return null;
}

export function isValidTransition(fromNode: WorkflowState, toNode: WorkflowState): boolean {
  const transitionData = findTransitionsBetweenNodes(fromNode, toNode);

  // The transition is to the same block.
  if (fromNode.id === toNode.id) {
    return false;
  }

  // If there are no simple or complex transitions, return false
  if (transitionData.complex.length === 0 && transitionData.simple.length === 0) {
    return false;
  }

  return true;
}

export function findTransitionsBetweenNodes(fromNode: WorkflowState, toNode: WorkflowState) {
  const validateTransition = (t: ValidTransitionConfig) => t.fromType === fromNode.type && t.toType === toNode.type;

  const simple = nodeTypesWithSimpleTransitions.filter(validateTransition);

  const complex = validBlockToBlockTransitionLookup.filter(validateTransition);

  return {
    simple,
    complex
  };
}

export function getTransitionsForNode(project: RefineryProject, node: WorkflowState) {
  const connectionTransitions = project.workflow_relationships.filter(
    transition => transition.next === node.id || transition.node === node.id
  );

  return connectionTransitions;
}

export function isComplexTransition(transitionType: WorkflowRelationshipType): boolean {
  return (
    transitionType === WorkflowRelationshipType.IF ||
    transitionType === WorkflowRelationshipType.ELSE ||
    transitionType === WorkflowRelationshipType.EXCEPTION ||
    transitionType === WorkflowRelationshipType.FAN_OUT ||
    transitionType === WorkflowRelationshipType.FAN_IN
  );
}

export function getValidTransitionsForEdge(
  project: RefineryProject,
  transition: WorkflowRelationship
): AvailableTransitionsByType {
  // Get edges that match the transition ID
  const edges = project.workflow_relationships.filter(e => e.id === transition.id);

  // Get the nodes connected to this edge
  const startNodeId: string = edges[0].node;
  const nextNodeId: string = edges[0].next;

  const startNode = getNodeDataById(project, startNodeId);

  const nextNode = getNodeDataById(project, nextNodeId);

  if (startNode === null || nextNode === null) {
    console.error("You've got a very borked transition!", startNode, nextNode);
    return {
      simple: [],
      complex: []
    };
  }

  const { simple, complex } = findTransitionsBetweenNodes(startNode, nextNode);

  const availableTransitions = [
    {
      // Simple boolean that we can filter on later.
      valid: simple.length > 0 || complex.length > 0,
      fromNode: startNode,
      toNode: nextNode,
      simple: simple.length > 0,
      transitionConfig: simple[0] || complex[0]
    }
  ];

  const validAvailableTransitions = availableTransitions.filter(t => t.valid);

  return {
    simple: validAvailableTransitions.filter(t => t.simple),
    complex: validAvailableTransitions.filter(t => !t.simple)
  };
}

export function getValidTransitionsForNode(
  project: RefineryProject,
  fromNode: WorkflowState,
  excludedNodeIDs: string[]
): AvailableTransitionsByType {
  const otherNodes = project.workflow_states.filter(n => n.id !== fromNode.id);

  const availableTransitions = otherNodes.map(toNode => {
    const { simple, complex } = findTransitionsBetweenNodes(fromNode, toNode);

    const isNotExcluded = !excludedNodeIDs.includes(toNode.id);

    return {
      // Simple boolean that we can filter on later.
      valid: isNotExcluded && (simple.length > 0 || complex.length > 0),
      fromNode,
      toNode,
      simple: simple.length > 0,
      transitionConfig: simple[0] || complex[0]
    };
  });

  const validAvailableTransitions = availableTransitions.filter(t => t.valid);

  return {
    simple: validAvailableTransitions.filter(t => t.simple),
    complex: validAvailableTransitions.filter(t => !t.simple)
  };
}

export function unwrapJson<T>(json: string | null) {
  if (json === null) {
    return null;
  }

  try {
    return JSON.parse(json) as T;
  } catch {
    return null;
  }
}

export function wrapJson(obj: any) {
  if (obj === null || obj === undefined) {
    return null;
  }

  try {
    return JSON.stringify(obj);
  } catch {
    return null;
  }
}

export function unwrapProjectJson(response: GetSavedProjectResponse): RefineryProject | null {
  try {
    const project = JSON.parse(response.project_json) as RefineryProject;

    // could probably have used spread, oh well
    return {
      name: project.name || 'Unknown Project',
      project_id: response.project_id || project.project_id || uuid(),
      workflow_relationships: project.workflow_relationships || [],
      workflow_states: project.workflow_states || [],
      workflow_files: project.workflow_files || [],
      workflow_file_links: project.workflow_file_links || [],
      global_handlers: project.global_handlers || {},
      version: project.version || 1,
      readme:
        project.readme ||
        '# Untitled Project README\n\nThis is a Refinery project README, update it to explain more about the project.',
      demo_walkthrough: project.demo_walkthrough || []
    };
  } catch {
    return null;
  }
}

export function getIDsOfBlockType(blockType: WorkflowStateType, project: RefineryProject) {
  const matchingWorkflowStates = project.workflow_states.filter(workflow_state => {
    return workflow_state.type === blockType;
  });

  return matchingWorkflowStates.map(workflow_state => {
    return workflow_state.id;
  });
}

/**
 * Returns the list of "next" valid blocks to select
 * @param state Vuex state object
 */
export function getValidBlockToBlockTransitions(state: ProjectViewState) {
  if (
    !state.openedProject ||
    !state.selectedResource ||
    !state.isAddingTransitionCurrently ||
    !state.availableTransitions
  ) {
    return null;
  }

  const selectedNode = getNodeDataById(state.openedProject, state.selectedResource);

  if (!selectedNode) {
    return null;
  }

  // Enabled all transitions
  if (state.newTransitionTypeSpecifiedInAddFlow === WorkflowRelationshipType.THEN) {
    return [...state.availableTransitions.simple, ...state.availableTransitions.complex];
  }

  // Return only complex transitions for anything else
  return [...state.availableTransitions.complex];
}

export function getSharedFilesForCodeBlock(nodeId: string, project: RefineryProject) {
  const sharedFileLinks = project.workflow_file_links.filter(workflow_file_link => workflow_file_link.node === nodeId);

  // Turn file links into a list of Shared Files
  return sharedFileLinks.map(
    shared_file_link => project.workflow_files.filter(workflow_file => workflow_file.id === shared_file_link.file_id)[0]
  );
}

export function getSharedFileById(fileId: string, state: ProjectViewState) {
  if (state.openedProject === null) {
    return null;
  }

  return deepJSONCopy(state.openedProject.workflow_files).filter(workflow_file => workflow_file.id === fileId)[0];
}

export function getSharedLinksForSharedFile(sharedFileId: string, project: RefineryProject) {
  return project.workflow_file_links.filter(workflow_file_link => workflow_file_link.file_id === sharedFileId);
}

export function getExceptionHandlerNodes(exceptionHandlerID: string, elements: cytoscape.ElementsDefinition): string[] {
  const graph = new Graph({
    multigraph: true,
    compound: true
  });

  addCytoscapeElementsToShadowGraph(graph, elements.nodes, elements.edges);
  return recursiveSuccessorMark(graph, exceptionHandlerID, [exceptionHandlerID]);
}

function getExceptionHandlerEdges(project: RefineryProject, excludedNodeIDs: string[]): WorkflowRelationship[] {
  if (!project.global_handlers.exception_handler) {
    return [];
  }
  const exceptionHandlerNode = project.global_handlers.exception_handler.id;

  function validNodeToAddExceptionHandler(w: WorkflowState) {
    const validWorkflowState = w.type === WorkflowStateType.LAMBDA || w.type === WorkflowStateType.API_GATEWAY;
    const nodeIsNotExcluded = !excludedNodeIDs.includes(w.id);
    return validWorkflowState && nodeIsNotExcluded;
  }

  return project.workflow_states.filter(validNodeToAddExceptionHandler).map(w => {
    return createNewTransition(WorkflowRelationshipType.EXCEPTION, w.id, exceptionHandlerNode, '');
  });
}

export function hookProjectDeployment(project: RefineryProject, excludedNodeIDs: string[]): RefineryProject {
  const exceptionHandlerEdges = getExceptionHandlerEdges(project, excludedNodeIDs);
  return {
    ...project,
    workflow_relationships: [...project.workflow_relationships, ...exceptionHandlerEdges]
  };
}

export function removeGlobalExceptionHandlerTransitions(project: RefineryProject): RefineryProject {
  if (!project.global_handlers.exception_handler) {
    return project;
  }
  const exceptionHandlerId = project.global_handlers.exception_handler.id;
  return {
    ...project,
    workflow_relationships: [...project.workflow_relationships.filter(r => r.next !== exceptionHandlerId)]
  };
}
