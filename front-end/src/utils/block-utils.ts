import uuid from 'uuid/v4';
import { WorkflowRelationship, WorkflowRelationshipType, WorkflowState, WorkflowStateType } from '@/types/graph';
import { CURRENT_BLOCK_SCHEMA, CURRENT_TRANSITION_SCHEMA } from '@/constants/graph-constants';
import { BlockTypeToDefaultState, blockTypeToDefaultStateMapping } from '@/constants/project-editor-constants';

function validatePathHasLeadingSlash(apiPath: string) {
  const pathHead = apiPath.startsWith('/') ? '' : '/';
  return `${pathHead}${apiPath}`;
}

function validatePathTail(apiPath: string) {
  if (apiPath != '/' && apiPath.endsWith('/')) {
    return apiPath.slice(0, -1);
  }
  return apiPath;
}

export function validatePath(apiPath: string) {
  return validatePathTail(validatePathHasLeadingSlash(apiPath));
}

export function nopWrite() {
  // Does nothing on purpose
}

export function createNewBlock<K extends keyof BlockTypeToDefaultState>(blockType: K, name: string): WorkflowState {
  return {
    ...blockTypeToDefaultStateMapping[blockType](),
    id: uuid(),
    name: name,
    type: blockType,
    version: CURRENT_BLOCK_SCHEMA
  };
}

export function createNewTransition(
  transitionType: WorkflowRelationshipType,
  fromNode: string,
  nextNode: string,
  expression: string
): WorkflowRelationship {
  return {
    node: fromNode,
    next: nextNode,
    type: transitionType,
    name: transitionType,
    expression: expression,
    id: uuid(),
    version: CURRENT_TRANSITION_SCHEMA
  };
}
