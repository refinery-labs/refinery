import Vue from 'vue';
import Router, { Route } from 'vue-router';
import store from './store/index';
import Home from './views/Home.vue';
import Settings from './views/Settings.vue';
import Marketplace from './views/Marketplace.vue';
import AdminPanel from './views/Admin';
import AllProjects from './views/AllProjects';
import ViewProject from './views/ViewProject';
import OpenedWorkflowWrapper from '@/views/ProjectsNestedViews/OpenedWorkflowWrapper';
import ProjectDeployments from '@/views/ProjectsNestedViews/ProjectDeployments';
import ViewProjectDeployment from '@/views/ProjectsNestedViews/ViewProjectDeployment';
import EditProjectDeployment from '@/views/ProjectsNestedViews/EditProjectDeployment';
import Layout from '@/components/Layout/Layout';
import { baseLinks, projectViewLinks } from '@/constants/router-constants';
import PageNotFound from '@/views/PageNotFound';
import ProjectNotFound from '@/views/ProjectsNestedViews/ProjectNotFound';
import LoginPage from '@/views/Authentication/LoginPage';
import { UserMutators } from '@/constants/store-constants';
import RegistrationPage from '@/views/Authentication/RegistrationPage';
import HelpPage from '@/views/Help';
import Billing from '@/views/Billing.vue';
import ProjectSettings from '@/views/ProjectsNestedViews/ProjectSettings';

Vue.use(Router);

async function guardLoggedIn(to: Route, from: Route, next: Function) {
  if (store.state.user.authenticated) {
    // allow to enter route
    next();
    return;
  }

  await store.dispatch(`user/fetchAuthenticationState`);

  // We haven't any login data, so go fetch it and keep going...
  if (store.state.user.authenticated) {
    // allow to enter route
    next();
    return;
  }

  // Throw the data into the store for later redirect usage
  store.commit(`user/${UserMutators.setRedirectState}`, to.fullPath);

  // go to '/login';
  next('/login');
}

const router = new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginPage
    },
    {
      path: '/register',
      name: 'register',
      component: RegistrationPage
    },
    {
      path: '/',
      component: Layout,
      beforeEnter: guardLoggedIn,
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
              name: 'deployment',
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
              component: ProjectSettings
            },
            {
              path: '*',
              component: ProjectNotFound
            }
          ]
        },
        // Disabled until we implement this page
        // {
        //   path: baseLinks.marketplace,
        //   name: 'marketplace',
        //   // This will likely need to have children eventually... but not today.
        //   component: Marketplace
        // },
        {
          path: baseLinks.billing,
          name: 'billing',
          component: Billing
        },
        {
          path: baseLinks.help,
          name: 'help',
          component: HelpPage
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

export default router;
