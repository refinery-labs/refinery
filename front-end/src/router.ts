import Vue from 'vue';
import Router from 'vue-router';
import Home from './views/Home.vue';
import Settings from './views/Settings.vue';
import AllProjects from './views/AllProjects';
import ViewProject from './views/ViewProject';
import OpenedProjectOverview from './views/ProjectsNestedViews/OpenedProjectOverview';
import AllProjectWorkflows from './views/ProjectsNestedViews/AllProjectWorkflows';
import ViewWorkflow from '@/views/ProjectsNestedViews/ViewWorkflow';

Vue.use(Router);

export default new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (about.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () =>
        import(/* webpackChunkName: "about" */ './views/About.vue')
    },
    {
      path: '/settings',
      name: 'settings',
      component: Settings
    },
    // View all available projects
    {
      path: '/projects',
      name: 'all projects',
      component: AllProjects
    },
    // Everything specific to a project is nested under the projectId in the path.
    // A project is akin to a "website" or a collection of "workflows" which map to a collection of tasks.
    // Most people using Refinery will probably only have 1 project for a while, so we can hide this functionality.
    {
      path: '/p/:projectId',
      name: 'project',
      component: ViewProject,
      
      children: [
        // Opened project overview page
        {
          path: '',
          name: 'opened project overview',
          component: OpenedProjectOverview
        },
        // View all workflows
        {
          path: 'workflows',
          name: 'all workflows',
          component: AllProjectWorkflows
        },
        // View workflow by ID
        {
          path: 'w/:workflowId',
          name: 'view workflow',
          component: ViewWorkflow,
    
          children: [
            // Overview of specific workflow
            {
              path: '',
              name: 'workflow overview',
              component: Home
            },
            // Edit a specific workflow
            {
              path: 'edit',
              name: 'edit workflow',
              component: Home
            }
          ]
        },
        // View all deployments for project
        {
          path: 'deployments',
          name: 'all deployments',
          component: Home // View all deployments
        },
        // View deployment by ID
        {
          path: 'd/:deploymentId',
          name: 'deployment',
          component: Home,
    
          children: [
            // Overview of deployment
            {
              path: '',
              name: 'deployment overview',
              component: Home
            },
            // Edit deployment
            {
              path: 'edit',
              name: 'edit deployment',
              component: Home
            }
          ]
        }
      ]
    },
    {
      path: '/marketplace',
      name: 'marketplace',
      component: Home // This will likely need to have children eventually... but not today.
    },
    {
      path: '/admin',
      name: 'admin',
      component: Home
    },
  ]
});
