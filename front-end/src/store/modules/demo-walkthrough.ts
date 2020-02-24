import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import {
  AddDeploymentExecutionOptions,
  DemoTooltip,
  DemoTooltipAction,
  DemoTooltipActionType,
  SetCodeRunnerOutputOptions,
  TooltipType,
  ViewExecutionLogsOptions
} from '@/types/demo-walkthrough-types';
import { DeploymentViewActions, DeploymentViewMutators, ProjectViewActions } from '@/constants/store-constants';
import router from '@/router';
import { RefineryProject, WorkflowRelationshipType } from '@/types/graph';
import { GetLatestProjectDeploymentResult, RunLambdaResult } from '@/types/api-types';
import {
  DeploymentExecutionsActions,
  DeploymentExecutionsMutators
} from '@/store/modules/panes/deployment-executions-pane';
import {
  AddBlockExecutionsPayload,
  BlockExecutionLogContentsByLogId,
  ProjectExecutionsByExecutionId
} from '@/types/deployment-executions-types';
import { ExecutionStatusType } from '@/types/execution-logs-types';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import { RunLambdaMutators } from '@/store/modules/run-lambda';
import { EditBlockActions } from '@/store/modules/panes/edit-block-pane';
import { error } from 'util';

export interface DemoWalkthroughState {
  currentTooltip: number;
  tooltips: DemoTooltip[];
  tooltipsLoaded: boolean;
}

export const baseState: DemoWalkthroughState = {
  currentTooltip: 0,
  tooltips: [],
  tooltipsLoaded: false
};

const INITIAL_TOOLTIP: DemoTooltip = {
  type: TooltipType.HTMLTooltip,
  visible: false,
  target: 'li[data-tooltip-id="editor-nav-item"]',
  header: 'Start the walkthrough',
  body: 'Get to know this project and Refinery a little better by clicking through this demo.'
};

const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: StoreType.demoWalkthrough })
export class DemoWalkthroughStore extends VuexModule<ThisType<DemoWalkthroughState>, RootState>
  implements DemoWalkthroughState {
  public currentTooltip: number = initialState.currentTooltip;
  public tooltips: DemoTooltip[] = initialState.tooltips;
  public tooltipsLoaded: boolean = initialState.tooltipsLoaded;
  public actionLookup: Record<DemoTooltipActionType, (action: DemoTooltipAction) => void> = {
    [DemoTooltipActionType.openBlockEditorPane]: this.openBlockEditorPane,
    [DemoTooltipActionType.closeBlockEditorPane]: this.closeBlockEditorPane,
    [DemoTooltipActionType.viewDeployment]: this.viewExampleProjectDeployment,
    [DemoTooltipActionType.openExecutionsPane]: this.openExecutionsPane,
    [DemoTooltipActionType.addDeploymentExecution]: this.addDeploymentExecution,
    [DemoTooltipActionType.viewExecutionLogs]: this.viewExecutionLogs,
    [DemoTooltipActionType.openCodeRunner]: this.openCodeRunner,
    [DemoTooltipActionType.setCodeRunnerOutput]: this.setCodeRunnerOutput,
    [DemoTooltipActionType.closeEditPane]: this.closeEditPane,
    [DemoTooltipActionType.closeLeftPane]: this.closeLeftPane,
    [DemoTooltipActionType.promptUserSignup]: this.promptUserSignup
  };

  get currentCyTooltips(): DemoTooltip[] {
    return this.tooltips.filter(t => t.type == TooltipType.CyTooltip);
  }

  get visibleHtmlTooltips(): DemoTooltip[] {
    return this.tooltips.filter(t => t.visible && t.type == TooltipType.HTMLTooltip);
  }

  get areTooltipsLoaded(): boolean {
    return this.tooltipsLoaded;
  }

  get showingDemoWalkthrough(): boolean {
    return this.tooltips.filter(t => t.visible).length > 0;
  }

  @Mutation
  public setCurrentTooltips(tooltips: DemoTooltip[]) {
    resetStoreState(this, baseState);

    if (tooltips.length == 0) {
      this.tooltips = [];
      return;
    }

    tooltips = [INITIAL_TOOLTIP, ...tooltips];

    tooltips[this.currentTooltip].visible = true;
    this.tooltipsLoaded = false;
    this.tooltips = tooltips;
    this.currentTooltip = 0;
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public loadCyTooltips(cy: cytoscape.Core) {
    if (this.tooltipsLoaded) {
      return;
    }

    const tooltips = [...this.tooltips];

    for (let i = 0; i < tooltips.length; i++) {
      const t = tooltips[i];
      if (t.type !== TooltipType.CyTooltip) {
        continue;
      }

      const pos = cy.getElementById(t.target).position();
      const tooltipConfig = tooltips[i].config;
      if (pos && tooltipConfig) {
        tooltips[i].config = {
          ...tooltipConfig,
          ...pos
        };
      } else {
        console.error('unable to locate element by ID', t.target);
      }
    }

    this.tooltipsLoaded = true;
    this.tooltips = tooltips;
  }

  @Mutation
  public nextTooltip() {
    const tooltips = [...this.tooltips];

    tooltips[this.currentTooltip].visible = false;

    const nextCurrentTooltip = this.currentTooltip + 1;
    if (nextCurrentTooltip < this.tooltips.length) {
      tooltips[nextCurrentTooltip].visible = true;

      this.currentTooltip = nextCurrentTooltip;
      this.tooltips = tooltips;
    }
  }

  @Action
  private async performTooltipAction(tooltipAction: DemoTooltipAction | undefined) {
    if (tooltipAction) {
      if (!(tooltipAction.action in this.actionLookup)) {
        console.error('Unable to find setup action in lookup', tooltipAction.action);
        return;
      }
      await this.actionLookup[tooltipAction.action].call(this, tooltipAction);
    }
  }

  @Action
  public async doTooltipSetupAction() {
    await this.performTooltipAction(this.tooltips[this.currentTooltip].setup);
  }

  @Action
  public async doTooltipTeardownAction() {
    await this.performTooltipAction(this.tooltips[this.currentTooltip].teardown);
  }

  @Action
  public async closeEditPane() {
    await this.context.dispatch(`project/editBlockPane/${EditBlockActions.cancelAndResetBlock}`, null, {
      root: true
    });
  }

  @Action
  public async openBlockEditorPane() {
    await this.context.dispatch(`project/${ProjectViewActions.selectNode}`, this.tooltips[this.currentTooltip].target, {
      root: true
    });
  }

  @Action
  public async closeBlockEditorPane() {
    await this.context.dispatch(`project/${ProjectViewActions.clearSelection}`, null, {
      root: true
    });
  }

  @Action
  public async openExecutionsPane() {
    await this.context.dispatch(`deploymentExecutions/${DeploymentExecutionsActions.selectLogByLogId}`, 'demo', {
      root: true
    });
    await this.context.dispatch(`deploymentExecutions/${DeploymentExecutionsActions.doOpenExecutionGroup}`, 'demo', {
      root: true
    });
    await this.context.dispatch(`deployment/${DeploymentViewActions.openViewExecutionsPane}`, null, {
      root: true
    });
  }

  @Action
  public async openCodeRunner() {
    await this.context.dispatch(`project/${ProjectViewActions.openLeftSidebarPane}`, SIDEBAR_PANE.runEditorCodeBlock, {
      root: true
    });
  }

  @Action
  public async closeLeftPane() {
    await this.context.dispatch(`project/${ProjectViewActions.closePane}`, PANE_POSITION.left, {
      root: true
    });
  }

  @Action
  public async promptUserSignup() {
    console.log('pls signup');
  }

  @Action
  public async setCodeRunnerOutput(action: DemoTooltipAction) {
    const codeRunnerAction = action.options as SetCodeRunnerOutputOptions;
    const result: RunLambdaResult = {
      ...codeRunnerAction,
      is_error: false,
      version: '1',
      truncated: false,
      status_code: 200,
      arn: 'test'
    };
    await this.context.commit(`runLambda/${RunLambdaMutators.setDevLambdaRunResult}`, result, {
      root: true
    });
  }

  @Action
  public async viewExecutionLogs(action: DemoTooltipAction) {
    const execLogsAction = action.options as ViewExecutionLogsOptions;

    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    const blockId = openedProject.workflow_states[0].id;
    const payload: AddBlockExecutionsPayload = {
      blockId: blockId,
      logs: {
        demo: {
          function_name: 'asdf',
          log_id: 'test',
          s3_key: 'test',
          timestamp: 0,
          type: ExecutionStatusType.SUCCESS
        }
      }
    };
    const logContents: BlockExecutionLogContentsByLogId = {
      test: {
        ...execLogsAction,
        arn: 'asdf',
        log_id: 'test',
        project_id: openedProject.project_id,
        timestamp: 0,
        type: ExecutionStatusType.SUCCESS
      }
    };

    await this.context.commit(
      `deploymentExecutions/${DeploymentExecutionsMutators.addBlockExecutionLogMetadata}`,
      payload,
      {
        root: true
      }
    );
    await this.context.commit(
      `deploymentExecutions/${DeploymentExecutionsMutators.addBlockExecutionLogContents}`,
      logContents,
      {
        root: true
      }
    );
    await this.context.dispatch(
      `deploymentExecutions/${DeploymentExecutionsActions.warmLogCacheAndSelectDefault}`,
      payload,
      {
        root: true
      }
    );
  }

  @Action
  public async addDeploymentExecution(action: DemoTooltipAction) {
    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    const addExecAction = action.options as AddDeploymentExecutionOptions;

    const blockExecutionGroup = addExecAction.executions.reduce((group, execution) => {
      const block = openedProject.workflow_states[execution.blockIndex];
      return {
        [block.id]: {
          executionStatus: execution.status,
          executionResult: {
            arn: '',
            SUCCESS: 0,
            EXCEPTION: 0,
            CAUGHT_EXCEPTION: 0
          },
          timestamp: 0,
          totalExecutionCount: 1,
          executionId: 'demo',
          blockId: block.id,
          blockName: block.name,
          blockArn: ''
        }
      };
    }, {});

    const errorExecs = addExecAction.executions.filter(e => e.status == ExecutionStatusType.EXCEPTION).length;
    const caughtExecs = addExecAction.executions.filter(e => e.status == ExecutionStatusType.CAUGHT_EXCEPTION).length;
    const successfulExecs = addExecAction.executions.filter(e => e.status == ExecutionStatusType.SUCCESS).length;
    const projectExecutions: ProjectExecutionsByExecutionId = {
      demo: {
        errorCount: errorExecs,
        caughtErrorCount: caughtExecs,
        successCount: successfulExecs,
        oldestTimestamp: 0,
        executionId: 'demo',
        numberOfLogs: addExecAction.executions.length,
        blockExecutionGroupByBlockId: blockExecutionGroup
      }
    };
    await this.context.commit(
      `deploymentExecutions/${DeploymentExecutionsMutators.setProjectExecutions}`,
      projectExecutions,
      {
        root: true
      }
    );
  }

  @Action
  public async viewExampleProjectDeployment() {
    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    const latestDeploymentResponse: GetLatestProjectDeploymentResult = {
      deployment_json: {
        ...openedProject,
        workflow_states: openedProject.workflow_states.map(s => {
          return {
            ...s,
            transitions: {
              [WorkflowRelationshipType.THEN]: [],
              [WorkflowRelationshipType.IF]: [],
              [WorkflowRelationshipType.FAN_IN]: [],
              [WorkflowRelationshipType.FAN_OUT]: [],
              [WorkflowRelationshipType.EXCEPTION]: [],
              [WorkflowRelationshipType.ELSE]: [],
              [WorkflowRelationshipType.MERGE]: []
            }
          };
        })
      },
      project_id: openedProject.project_id,
      id: 'asdf',
      timestamp: 0
    };

    this.context.commit(`deployment/${DeploymentViewMutators.setOpenedDeployment}`, latestDeploymentResponse, {
      root: true
    });

    router.push({
      name: 'deployment',
      params: {
        projectId: openedProject.project_id
      }
    });
  }
}
