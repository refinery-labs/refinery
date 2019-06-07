export const baseLinks = {
  home: '/',
  about: '/about',
  settings: '/settings',
  stats: '/stats',
  projects: '/projects',
  marketplace: '/marketplace',
  billing: '/billing',
  help: '/help',
  admin: '/admin'
};

export const projectViewLinks = {
  viewProject: '/p/:projectId'
};

export const linkFormatterUtils = {
  viewProjectFormatter(projectId: string) {
    return projectViewLinks.viewProject.replace(':projectId', projectId);
  }
};
