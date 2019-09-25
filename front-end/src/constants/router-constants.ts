export const baseLinks = {
  home: '/',
  about: '/about',
  settings: '/settings',
  stats: '/stats',
  projects: '/projects',
  blockRepository: '/block-repository',
  billing: '/billing',
  documentation: 'https://docs.refinery.io/',
  help: '/help',
  admin: '/admin'
};

export const projectViewLinks = {
  viewProject: '/p/:projectId'
};

export const linkFormatterUtils = {
  getVersionString(version?: number) {
    if (version !== undefined) {
      const searchParams = new URLSearchParams();
      searchParams.append('version', version.toString(10));
      return '?' + searchParams.toString();
    }

    return '';
  },

  viewProjectFormatter(projectId: string, version?: number) {
    return projectViewLinks.viewProject.replace(':projectId', projectId) + this.getVersionString(version);
  }
};
