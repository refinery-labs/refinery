
// Needed to have the "@" symbols in the paths resolve.
import 'module-alias/register';

import { remapProjectJsonProperties } from '@/utils/new-project-utils';

import * as fs from 'fs';

import { loadProjectFromDir } from '@/repo-compiler/one-to-one/git-to-refinery';
import { saveProjectToRepo } from '@/repo-compiler/one-to-one/refinery-to-git';

async function replaceGitBlockIds(gitFs, gitPath: string, projectId: string, gitRepoUrl: string) {
  const project = await loadProjectFromDir(gitFs, projectId, gitPath);

  const newProject = remapProjectJsonProperties(project, false);

  // We want to keep the same ProjectID for this step -- just change the blocks IDs.
  newProject.project_id = projectId;

  await saveProjectToRepo(gitFs, gitPath, newProject, gitRepoUrl);
}

async function readArgsAndConvertProject() {

  const scriptArgs = process.argv.slice(2);

  if (scriptArgs.length !== 2) {
    console.error('Need to specify the git repo path and ProjectID as arguments');
    process.exit(1);
  }

  const gitPath = scriptArgs[0];

  // TODO: Read this file dynamically
  const projectId = scriptArgs[1];

  await replaceGitBlockIds(fs, gitPath, projectId, '');
}

readArgsAndConvertProject();

