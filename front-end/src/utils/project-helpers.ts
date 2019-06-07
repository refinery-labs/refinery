import { RefineryProject, WorkflowRelationshipType, WorkflowState } from '@/types/graph';
import {
  nodeTypesWithSimpleTransitions,
  validBlockToBlockTransitionLookup,
  ValidTransitionConfig
} from '@/constants/project-editor-constants';
import { AvailableTransitionsByType, ProjectViewState } from '@/store/store-types';
import { GetSavedProjectResponse } from '@/types/api-types';
import uuid from 'uuid/v4';

export function getNodeDataById(project: RefineryProject, nodeId: string) {
  const targetStates = project.workflow_states;

  const results = targetStates.filter(workflowState => {
    return workflowState.id === nodeId;
  });

  if (results.length > 0) {
    return results[0];
  }

  return null;
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

export function getValidTransitionsForNode(
  project: RefineryProject,
  fromNode: WorkflowState
): AvailableTransitionsByType {
  const otherNodes = project.workflow_states.filter(n => n.id !== fromNode.id);

  const availableTransitions = otherNodes.map(toNode => {
    const { simple, complex } = findTransitionsBetweenNodes(fromNode, toNode);

    return {
      // Simple boolean that we can filter on later.
      valid: simple.length > 0 || complex.length > 0,
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
      version: project.version || 1
    };
  } catch {
    return null;
  }
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
