import router from '@/router';

export function viewProject(projectId: string) {
  router.push({
    name: 'project',
    params: { projectId }
  });
}
