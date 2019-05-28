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
import Layout from '@/components/Layout/Layout';
import {baseLinks, projectViewLinks} from '@/constants/router-constants';
import OpenedProjectGraphContainer from '@/containers/OpenedProjectGraphContainer';
import PageNotFound from '@/views/PageNotFound';
import ProjectNotFound from '@/views/ProjectsNestedViews/ProjectNotFound';

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
          path: baseLinks.about,
          name: 'about',
          // route level code-splitting
          // this generates a separate chunk (about.[hash].js) for this route
          // which is lazy-loaded when the route is visited.
          component: () =>
            import(/* webpackChunkName: "about" */ './views/About.vue')
        },
        // Account-level settings page
        {
          path: baseLinks.settings,
          name: 'settings',
          component: Settings
        },
        // Gives info about billing and usage on the platform.
        // Will likely contain children for pages like billing and specific endpoint hits.
        {
          path: baseLinks.stats,
          name: 'stats',
          component: Settings
        },
        // View all available projects
        {
          path: baseLinks.projects,
          name: 'allProjects',
          component: AllProjects
        },
        // Everything specific to a project is nested under the projectId in the path.
        // A project is akin to a "website" or a collection of "workflows" which map to a collection of tasks.
        // Most people using Refinery will probably only have 1 project for a while, so we can hide this functionality.
        {
          path: projectViewLinks.viewProject,
          name: 'project',
          // components: {default: ViewProject, graph: RefineryGraph},
          component: ViewProject,
          children: [
            // View all deployments for project
            {
              path: 'deployments',
              name: 'allDeployments',
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
                  name: 'deployment',
                  component: ViewProjectDeployment
                },
                // Edit deployment
                {
                  path: 'edit',
                  name: 'editDeployment',
                  component: EditProjectDeployment
                }
              ]
            },
            // View Usage information for project
            {
              path: 'usage',
              name: 'projectUsage',
              component: ProjectDeployments
            },
            // View settings for a project
            {
              path: 'settings',
              name: 'projectSettings',
              component: ProjectDeployments
            },
            {
              path: '*',
              component: ProjectNotFound
            }
          ]
        },
        {
          path: baseLinks.marketplace,
          name: 'marketplace',
          // This will likely need to have children eventually... but not today.
          component: Marketplace
        },
        {
          path: baseLinks.help,
          name: 'help',
          component: Marketplace
        },
        {
          path: baseLinks.admin,
          name: 'admin',
          component: AdminPanel
        },
        {
          path: '*',
          component: PageNotFound
        }
      ]
    }
  ]
});

