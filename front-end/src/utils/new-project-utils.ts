import uuid from 'uuid/v4';
import { createProject, importProject } from '@/store/fetchers/api-helpers';
import { viewProject } from '@/utils/router-utils';
import { NewProjectConfig } from '@/types/new-project-types';
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

export async function createNewProjectFromConfig(config: NewProjectConfig): Promise<string | null> {
  if (!config.json && !config.name) {
    config.setError('Cannot create project without either name or json');
    return null;
  }

  // Reset the error to nothing
  config.setError(null);

  // Sets the busy status to true
  config.setStatus(true);

  let response = await makeProjectApiCallForConfig(config);

  // Reset busy status.
  config.setStatus(false);

  if (!response) {
    config.setError(config.unknownError);
    return null;
  }

  if (!response.success) {
    config.setError(response.msg || null);
    return null;
  }

  if (config.navigateToNewProject) {
    viewProject(response.project_id);
  }
  return response.project_id;
}

async function makeProjectApiCallForConfig(config: NewProjectConfig) {
  if (config.json) {
    const response = await importRawProjectJson(config.json, false);

    // Attempt to make the project with a stupid and unique name.
    if (response && response.code === 'PROJECT_NAME_EXISTS') {
      // Reset the error because we know it's just the name being a dupe
      config.setError(null);
      return await importRawProjectJson(config.json, true);
    }

    return response;
  }

  if (config.name) {
    const response = await createProject(config.name);

    // Attempt to make the project with a stupid and unique name.
    if (response && response.code === 'PROJECT_NAME_EXISTS') {
      // Reset the error because we know it's just the name being a dupe
      config.setError(null);
      return await createProject(`${config.name} - ${generateStupidName()}`);
    }

    return response;
  }

  console.error('Both name and config were not specified. Invalid Project to import.');
  return null;
}

export async function importRawProjectJson(json: string, generateNewName: boolean) {
  const remappedJson = remapImportedProjectJsonProperties(json, generateNewName);

  if (!remappedJson) {
    return null;
  }

  return await importProject(remappedJson);
}

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

  project.project_id = uuid();

  project.version = 1;

  const baseName = project.name || 'Untitled Project';
  const needsNewName = !project.name || generateNewName;

  project.name = getProjectName(baseName, needsNewName);

  project.global_handlers = project.global_handlers || {};

  return JSON.stringify(reassignProjectIds(project));
}

function getProjectName(baseName: string, needsNewName: boolean) {
  if (needsNewName) {
    return `${baseName} - ${generateStupidName()}`;
  }
  return baseName;
}
