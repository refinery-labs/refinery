import {RefineryProject} from '@/types/graph';
import LightningFS from "@isomorphic-git/lightning-fs";
import git from 'isomorphic-git';
import http from 'isomorphic-git/http/web';

class RepoCompilationError extends Error {}

function

function compileProjectRepo(projectID: string, gitURL: string): RefineryProject {
  const repoDir = '/test-clone';
  const fs = new LightningFS();

  const repo = git.clone(
    {
      fs, http, dir,
      url: 'https://github.com/isomorphic-git/lightning-fs.git',
      corsProxy: 'http://localhost:8003'
    }).then((e) => {
    console.log(fs.readdir(repoDir, console.log));
    const refineryProject = {
      ...loadProjectFromDir(repoDir),
      project_id: projectID
    } as RefineryProject;
    return refineryProject;
  });

  return repo;

  // TODO cleanup fs?
}