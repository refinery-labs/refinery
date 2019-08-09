import { Module } from 'vuex';
import { RootState } from '../../store-types';
import { WorkflowState } from '@/types/graph';
import { getNodeDataById } from '@/utils/project-helpers';
import { ProductionLambdaWorkflowState, ProductionWorkflowState } from '@/types/production-workflow-types';
import {
  getCloudWatchLinkForCodeBlockArn,
  getLinkForArn,
  getMonitorLinkForCodeBlockArn
} from '@/utils/code-block-utils';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { DeploymentViewActions } from '@/constants/store-constants';
import { SIDEBAR_PANE } from '@/types/project-editor-types';
import { RunLambdaActions } from '@/store/modules/run-lambda';

// Enums
export enum ViewBlockMutators {
  resetState = 'resetState',
  setSelectedNode = 'setSelectedNode',
  setCodeModalVisibility = 'setCodeModalVisibility',
  setLibrariesModalVisibility = 'setLibrariesModalVisibility'
}

export enum ViewBlockActions {
  selectNodeFromOpenProject = 'selectNodeFromOpenProject',
  selectCurrentlySelectedProjectNode = 'selectCurrentlySelectedProjectNode',
  openAwsConsoleForBlock = 'openAwsConsoleForBlock',
  openAwsMonitorForCodeBlock = 'openAwsMonitorForCodeBlock',
  openAwsCloudwatchForCodeBlock = 'openAwsCloudwatchForCodeBlock',
  runCodeBlock = 'runCodeBlock'
}

// Types
export interface ViewBlockPaneState {
  selectedNode: WorkflowState | null;
  showCodeModal: boolean;

  // This doesn't really make sense here
  // but neither does having it in a selectedNode...
  librariesModalVisibility: boolean;
}

// Initial State
const moduleState: ViewBlockPaneState = {
  selectedNode: null,
  showCodeModal: false,
  librariesModalVisibility: false
};

function getLinkForBlock(getLink: (arn: string) => string | null) {
  return (state: ViewBlockPaneState) => {
    if (!state.selectedNode) {
      return null;
    }

    const block = state.selectedNode as ProductionWorkflowState;

    if (!block.arn) {
      return null;
    }

    return getLink(block.arn);
  };
}

function openLinkForBlock(block: ProductionWorkflowState, getLink: (arn: string) => string | null) {
  if (!block.arn) {
    console.error('Unable to open block in AWS console due to missing ARN data');
    return;
  }

  const consoleLink = getLink(block.arn);

  if (!consoleLink) {
    console.error('Unable to read AWS console link for block, likely invalid ARN supplied');
    return;
  }

  window.open(consoleLink, '_blank');
}

const ViewBlockPaneModule: Module<ViewBlockPaneState, RootState> = {
  namespaced: true,
  state: deepJSONCopy(moduleState),
  getters: {
    getAwsConsoleUri: getLinkForBlock(getLinkForArn),
    getLambdaMonitorUri: getLinkForBlock(getMonitorLinkForCodeBlockArn),
    getLambdaCloudWatchUri: getLinkForBlock(getCloudWatchLinkForCodeBlockArn)
  },
  mutations: {
    [ViewBlockMutators.resetState](state, keepSomeSettings = true) {
      resetStoreState(state, moduleState);
    },
    [ViewBlockMutators.setSelectedNode](state, node) {
      state.selectedNode = node;
    },
    [ViewBlockMutators.setLibrariesModalVisibility](state, visibility) {
      state.librariesModalVisibility = visibility;
    },
    [ViewBlockMutators.setCodeModalVisibility](state, visible) {
      state.showCodeModal = visible;
    }
  },
  actions: {
    async [ViewBlockActions.selectNodeFromOpenProject](context, nodeId: string) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment) {
        console.error('Attempted to open edit block pane without loaded project');
        return;
      }

      const node = getNodeDataById(deploymentStore.openedDeployment, nodeId);

      if (!node) {
        console.error('Attempted to select unknown block in edit block pane');
        return;
      }

      context.commit(ViewBlockMutators.setSelectedNode, node);
    },
    async [ViewBlockActions.selectCurrentlySelectedProjectNode](context) {
      const deploymentStore = context.rootState.deployment;

      if (!deploymentStore.openedDeployment) {
        console.error('Attempted to open view block pane without loaded deployment');
        return;
      }

      if (!deploymentStore.selectedResource) {
        context.commit(ViewBlockMutators.setSelectedNode, null);
        return;
      }

      await context.dispatch(ViewBlockActions.selectNodeFromOpenProject, deploymentStore.selectedResource);
    },
    async [ViewBlockActions.openAwsConsoleForBlock](context) {
      if (!context.state.selectedNode) {
        console.error('Attempted to view Block in AWS Console without selected node');
        return;
      }

      openLinkForBlock(context.state.selectedNode as ProductionWorkflowState, getLinkForArn);
    },
    async [ViewBlockActions.openAwsMonitorForCodeBlock](context) {
      if (!context.state.selectedNode) {
        console.error('Attempted to view Block in AWS Console without selected node');
        return;
      }

      openLinkForBlock(context.state.selectedNode as ProductionLambdaWorkflowState, getMonitorLinkForCodeBlockArn);
    },
    async [ViewBlockActions.openAwsCloudwatchForCodeBlock](context) {
      if (!context.state.selectedNode) {
        console.error('Attempted to view Block in AWS Console without selected node');
        return;
      }

      openLinkForBlock(context.state.selectedNode as ProductionLambdaWorkflowState, getCloudWatchLinkForCodeBlockArn);
    },
    async [ViewBlockActions.runCodeBlock](context) {
      await context.dispatch(
        `deployment/${DeploymentViewActions.openLeftSidebarPane}`,
        SIDEBAR_PANE.runDeployedCodeBlock,
        { root: true }
      );

      // Matt is upset at me for this. Please call him silly names to ease my pain.
      // await context.dispatch(`runLambda/${RunLambdaActions.runSelectedDeployedCodeBlock}`, null, { root: true });
    }
  }
};

export default ViewBlockPaneModule;
