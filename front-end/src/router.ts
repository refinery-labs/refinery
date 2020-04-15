import Vue from 'vue';
import Router, { Route } from 'vue-router';
import Home from './views/Home.vue';
import Settings from './views/Settings';
import BlockRepository from './views/BlockRepository';
import AdminPanel from './views/Admin';
// import AllProjects from './views/AllProjects';
// import ViewProject from './views/ViewProject';
import OpenedWorkflowWrapper from '@/views/ProjectsNestedViews/OpenedWorkflowWrapper';
// import ProjectDeployments from '@/views/ProjectsNestedViews/ProjectDeployments';
import ViewProjectDeployment from '@/views/ProjectsNestedViews/ViewProjectDeployment';
import EditProjectDeployment from '@/views/ProjectsNestedViews/EditProjectDeployment';
import Layout from '@/components/Layout/Layout';
import { baseLinks, projectViewLinks } from '@/constants/router-constants';
import PageNotFound from '@/views/PageNotFound';
import ProjectNotFound from '@/views/ProjectsNestedViews/ProjectNotFound';
// import LoginPage from '@/views/Authentication/LoginPage';
// import RegistrationPage from '@/views/Authentication/RegistrationPage';
import HelpPage from '@/views/Help';
// import Billing from '@/views/Billing.vue';
// import ProjectSettings from '@/views/ProjectsNestedViews/ProjectSettings';
import { guardLoggedIn } from '@/utils/auth-utils';
// import ImportProject from '@/views/ImportProject';
// import TermsOfServicePage from '@/views/TermsOfService';

Vue.use(Router);

const router = new Router({
  mode: 'history',
  base: '/',
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import(/* webpackChunkName: "login" */ '@/views/Authentication/LoginPage')
    },
    {
      path: '/register',
      name: 'register',
      component: () => import(/* webpackChunkName: "register" */ '@/views/Authentication/RegistrationPage')
    },
    {
      path: '/terms-of-service',
      name: 'termsOfService',
      component: () => import(/* webpackChunkName: "termsOfService" */ '@/views/TermsOfService')
    },
    {
      path: baseLinks.help,
      component: Layout,
      children: [
        {
          path: '',
          component: HelpPage
        }
      ]
    },
    {
      path: '/import',
      component: Layout,
      // beforeEnter: (to: Route, from: Route, next: Function) => guardLoggedIn(to, from, next),
      children: [
        {
          path: '',
          component: () => import(/* webpackChunkName: "importProject" */ '@/views/ImportProject')
        }
      ]
    },
    {
      path: '/',
      component: Layout,
      beforeEnter: (to: Route, from: Route, next: Function) => guardLoggedIn(to, from, next),
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
          component: () => import(/* webpackChunkName: "about" */ './views/About.vue')
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
          component: () => import(/* webpackChunkName: "allProjects" */ './views/AllProjects')
        },
        // Everything specific to a project is nested under the projectId in the path.
        // A project is akin to a "website" or a collection of "workflows" which map to a collection of tasks.
        // Most people using Refinery will probably only have 1 project for a while, so we can hide this functionality.
        {
          path: projectViewLinks.viewProject,
          name: 'project',
          // components: {default: ViewProject, graph: RefineryGraph},
          component: () => import(/* webpackChunkName: "project" */ './views/ViewProject'),
          children: [
            // View all deployments for project
            {
              path: 'deployments',
              name: 'deployment',
              // View all deployments
              component: () =>
                import(/* webpackChunkName: "deployment" */ '@/views/ProjectsNestedViews/ProjectDeployments')
            },
            // View deployment by ID
            {
              path: 'd/:deploymentId',
              component: OpenedWorkflowWrapper,

              children: [
                // Overview of deployment
                {
                  path: '',
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
            // View settings for a project
            {
              path: 'settings',
              name: 'projectSettings',
              component: () =>
                import(/* webpackChunkName: "projectSettings" */ '@/views/ProjectsNestedViews/ProjectSettings')
            },
            {
              path: '*',
              component: ProjectNotFound
            }
          ]
        },
        {
          path: baseLinks.blockRepository,
          name: 'blockRepository',
          component: BlockRepository
        },
        {
          path: baseLinks.billing,
          name: 'billing',
          component: () => import(/* webpackChunkName: "billing" */ '@/views/Billing.vue')
        },
        {
          path: baseLinks.admin,
          name: 'admin',
          component: AdminPanel
        }
      ]
    },
    {
      path: '*',
      component: Layout,
      children: [
        {
          path: '',
          component: PageNotFound
        }
      ]
    }
  ]
});

export default router;
