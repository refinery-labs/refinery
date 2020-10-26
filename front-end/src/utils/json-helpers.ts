import { GetSavedProjectResponse } from '@/types/api-types';
import { RefineryProject } from '@/types/graph';
import uuid from 'uuid/v4';

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
