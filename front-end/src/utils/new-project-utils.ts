import uuid from 'uuid/v4';
import { unwrapJson } from '@/utils/project-helpers';
import {
  GlobalExceptionHandler,
  GlobalHandlers,
  RefineryProject,
  WorkflowFile,
  WorkflowFileLink,
  WorkflowRelationship,
  WorkflowState
} from '@/types/graph';
import generateStupidName from '@/lib/silly-names';
import { CyTooltip, DemoTooltip, TooltipType } from '@/types/demo-walkthrough-types';

function reassignDemoWalkthrough(
  demoWalkthrough: DemoTooltip[] | undefined,
  oldIdToNewIdLookup: { [key: string]: string }
): DemoTooltip[] {
  if (!demoWalkthrough) {
    return [];
  }
  return demoWalkthrough.reduce((outputTooltips, tooltip) => {
    if (tooltip.type === TooltipType.CyTooltip) {
      const cyTooltip = tooltip as CyTooltip;
      cyTooltip.config.blockId = oldIdToNewIdLookup[cyTooltip.config.blockId];

      tooltip = cyTooltip;
    }

    outputTooltips.push(tooltip);
    return outputTooltips;
  }, [] as DemoTooltip[]);
}

function reassignProjectIds(project: RefineryProject): RefineryProject {
  // Keep this lookup so that we can remap the IDs in edges/relationships
  const oldIdToNewIdLookup: { [key: string]: string } = {};

  // Assign new Ids to all of the workflow states
  const newStates = project.workflow_states.reduce((outputStates, state) => {
    const newId = uuid();

    oldIdToNewIdLookup[state.id] = newId;

    outputStates.push({
      ...state,
      id: newId
    });

    return outputStates;
  }, [] as WorkflowState[]);

  // Go through existing relationships and ensure that they point to the new node Ids.
  const newRelationships = project.workflow_relationships.reduce((outputRelationships, relationship) => {
    outputRelationships.push({
      ...relationship,
      id: uuid(),
      node: oldIdToNewIdLookup[relationship.node],
      next: oldIdToNewIdLookup[relationship.next]
    });

    return outputRelationships;
  }, [] as WorkflowRelationship[]);

  // Update the IDs of every file
  const newWorkflowFiles = project.workflow_files.reduce((outputFiles, file) => {
    const newId = uuid();

    oldIdToNewIdLookup[file.id] = newId;

    outputFiles.push({
      ...file,
      id: newId
    });

    return outputFiles;
  }, [] as WorkflowFile[]);

  // Update the IDs of every walkthrough tooltip
  const newDemoWalkthrough = reassignDemoWalkthrough(project.demo_walkthrough, oldIdToNewIdLookup);

  // Update the file links using the new ID lookups.
  const newWorkflowFileLinks = project.workflow_file_links.reduce((outputFileLinks, fileLink) => {
    const missingFileForLink = oldIdToNewIdLookup[fileLink.file_id] === undefined;
    const missingNodeForLink = oldIdToNewIdLookup[fileLink.node] === undefined;

    // Don't propagate bad state -- deal with it here and move on.
    if (missingFileForLink || missingNodeForLink) {
      console.warn('Skipping adding file link, detected invalid state at import.', fileLink);
      return outputFileLinks;
    }

    outputFileLinks.push({
      ...fileLink,
      id: uuid(),
      file_id: oldIdToNewIdLookup[fileLink.file_id],
      node: oldIdToNewIdLookup[fileLink.node]
    });

    // Don't propagate bad state -- deal with it here and move on.
    if (missingFileForLink || missingNodeForLink) {
      console.warn('Skipping adding file link, detected invalid state at import.', fileLink);
      return outputFileLinks;
    }

    outputFileLinks.push({
      ...fileLink,
      id: uuid(),
      file_id: oldIdToNewIdLookup[fileLink.file_id],
      node: oldIdToNewIdLookup[fileLink.node]
    });

    return outputFileLinks;
  }, [] as WorkflowFileLink[]);

  // Finally, update the ids in the global handlers
  const remapGlobalHandlerId = (handler: GlobalExceptionHandler | undefined): GlobalHandlers => {
    if (!handler) {
      return {};
    }
    const newHandlerId = oldIdToNewIdLookup[handler.id];
    if (newHandlerId === undefined) {
      console.warn(`Unable to remap global handler with id: ${handler.id}`);
      return {};
    }
    return {
      exception_handler: {
        id: newHandlerId
      }
    };
  };
  const newGlobalHandlers = {
    ...remapGlobalHandlerId(project.global_handlers.exception_handler)
  };

  // Return a new project with the new ids in place.
  return {
    ...project,
    workflow_files: newWorkflowFiles,
    workflow_file_links: newWorkflowFileLinks,
    workflow_relationships: newRelationships,
    workflow_states: newStates,
    global_handlers: newGlobalHandlers,
    demo_walkthrough: newDemoWalkthrough
  };
}
export function remapImportedProjectJsonProperties(json: string, generateNewName: boolean) {
  const project = unwrapJson<RefineryProject>(json);

  if (!project) {
    return null;
  }

  const newProject = remapProjectJsonProperties(project, generateNewName);

  return JSON.stringify(newProject);
}

export function remapProjectJsonProperties(project: RefineryProject, generateNewName: boolean) {
  project.project_id = uuid();

  project.version = 1;

  const baseName = project.name || 'Untitled Project';
  const needsNewName = !project.name || generateNewName;

  project.name = getProjectName(baseName, needsNewName);

  project.global_handlers = project.global_handlers || {};

  return reassignProjectIds(project);
}

function getProjectName(baseName: string, needsNewName: boolean) {
  if (needsNewName) {
    return `${baseName} - ${generateStupidName()}`;
  }
  return baseName;
}
