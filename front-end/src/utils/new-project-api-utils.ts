import { createProject, importProject } from '@/store/fetchers/api-helpers';
import { NewProjectConfig } from '@/types/new-project-types';
import generateStupidName from '@/lib/silly-names';
import { remapImportedProjectJsonProperties } from '@/utils/new-project-utils';
import { viewProject } from '@/utils/router-utils';

export async function makeProjectApiCallForConfig(config: NewProjectConfig) {
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

export async function createNewProjectFromConfig(config: NewProjectConfig) {
  if (!config.json && !config.name) {
    config.setError('Cannot create project without either name or json');
    return;
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
    return;
  }

  if (!response.success) {
    config.setError(response.msg || null);
    return;
  }

  if (config.navigateToNewProject) {
    viewProject(response.project_id);
  }
}
