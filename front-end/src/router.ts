import Vue from 'vue';
import Router from 'vue-router';
import Home from './views/Home.vue';
import Settings from './views/Settings.vue';
import Marketplace from './views/Marketplace.vue';
import AdminPanel from './views/Admin';
import AllProjects from './views/AllProjects';
import ViewProject from './views/ViewProject';
import OpenedProjectOverview from './views/ProjectsNestedViews/OpenedProjectOverview';
import AllProjectWorkflows from './views/ProjectsNestedViews/AllProjectWorkflows';
import ViewWorkflow from '@/views/ProjectsNestedViews/ViewWorkflow';
import OpenedWorkflowWrapper from '@/views/ProjectsNestedViews/OpenedWorkflowWrapper';
import EditWorkflow from '@/views/ProjectsNestedViews/EditWorkflow';
import ProjectDeployments from '@/views/ProjectsNestedViews/ProjectDeployments';
import ViewProjectDeployment from '@/views/ProjectsNestedViews/ViewProjectDeployment';
import EditProjectDeployment from '@/views/ProjectsNestedViews/EditProjectDeployment';
import Layout from '@/components/Layout/Layout.vue';

Vue.use(Router);

export default new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/',
      component: Layout,
      children: [
        {
          path: '',
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
        // Account-level settings page
        {
          path: '/settings',
          name: 'settings',
          component: Settings
        },
        // Gives info about billing and usage on the platform.
        // Will likely contain children for pages like billing and specific endpoint hits.
        {
          path: '/stats',
          name: 'stats',
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
          component: ViewProject,
    
          children: [
            // Opened project overview page
            {
              path: '',
              name: 'opened project overview',
              // Example syntax for how to load multiple components
              // components: {default: OpenedProjectOverview, home: Home }
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
              component: OpenedWorkflowWrapper,
        
              children: [
                // Overview of specific workflow
                {
                  path: '',
                  name: 'workflow overview',
                  component: ViewWorkflow
                },
                // Edit a specific workflow
                {
                  path: 'edit',
                  name: 'edit workflow',
                  component: EditWorkflow
                }
              ]
            },
            // View all deployments for project
            {
              path: 'deployments',
              name: 'all deployments',
              // View all deployments
              component: ProjectDeployments
            },
            // View deployment by ID
            {
              path: 'd/:deploymentId',
              component: OpenedWorkflowWrapper,
        
              children: [
                // Overview of deployment
                {
                  path: '',
                  name: 'deployment overview',
                  component: ViewProjectDeployment
                },
                // Edit deployment
                {
                  path: 'edit',
                  name: 'edit deployment',
                  component: EditProjectDeployment
                }
              ]
            }
          ]
        },
        {
          path: '/marketplace',
          name: 'marketplace',
          // This will likely need to have children eventually... but not today.
          component: Marketplace
        },
        {
          path: '/admin',
          name: 'admin',
          component: AdminPanel
        }
      ]
    },
    
  ]
});

