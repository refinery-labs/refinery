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
import {
  GetLatestProjectDeploymentResponse,
  GetLatestProjectDeploymentResult,
  RunLambdaResult
} from '@/types/api-types';
import { DeploymentExecutionsActions } from '@/store/modules/panes/deployment-executions-pane';
import {
  BlockExecutionLogContentsByLogId,
  BlockExecutionLogData,
  ProductionExecutionResponse
} from '@/types/deployment-executions-types';
import { ExecutionStatusType } from '@/types/execution-logs-types';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import { RunLambdaMutators } from '@/store/modules/run-lambda';
import { EditBlockActions } from '@/store/modules/panes/edit-block-pane';
import { debug } from 'util';
import { ViewBlockActions, ViewBlockMutators } from '@/store/modules/panes/view-block-pane';
import cytoscape from 'cytoscape';
import { DemoWalkthroughStoreModule, UnauthViewProjectStoreModule } from '@/store';

export interface DemoWalkthroughState {
  currentIndex: number;
  tooltips: DemoTooltip[];
  tooltipsLoaded: boolean;
}

export const baseState: DemoWalkthroughState = {
  currentIndex: 0,
  tooltips: [],
  tooltipsLoaded: false
};

const INITIAL_TOOLTIP: DemoTooltip = {
  type: TooltipType.HTMLTooltip,
  visible: false,
  target: 'li[data-tooltip-id="editor-nav-item"]',
  header: 'Start the walkthrough',
  body: 'Get to know this project and Refinery a little better by clicking through this demo.',
  config: {
    placement: 'bottom'
  }
};

const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: StoreType.demoWalkthrough })
export class DemoWalkthroughStore extends VuexModule<ThisType<DemoWalkthroughState>, RootState>
  implements DemoWalkthroughState {
  public currentIndex: number = initialState.currentIndex;
  public tooltips: DemoTooltip[] = initialState.tooltips;
  public tooltipsLoaded: boolean = initialState.tooltipsLoaded;
  public actionLookup: Record<DemoTooltipActionType, (action: DemoTooltipAction) => void> = {
    [DemoTooltipActionType.openBlockEditorPane]: this.openBlockEditorPane,
    [DemoTooltipActionType.closeBlockEditorPane]: this.closeBlockEditorPane,
    [DemoTooltipActionType.viewDeployment]: this.viewExampleProjectDeployment,
    [DemoTooltipActionType.openExecutionsPane]: this.openExecutionsPane,
    [DemoTooltipActionType.viewExecutionLogs]: this.viewExecutionLogs,
    [DemoTooltipActionType.openCodeRunner]: this.openCodeRunner,
    [DemoTooltipActionType.setCodeRunnerOutput]: this.setCodeRunnerOutput,
    [DemoTooltipActionType.closeEditPane]: this.closeEditPane,
    [DemoTooltipActionType.closeOpenPanes]: this.closeOpenPanes,
    [DemoTooltipActionType.promptUserSignup]: this.promptUserSignup,
    [DemoTooltipActionType.addDeploymentExecution]: this.addDeploymentExecution
  };
  public mockNetworkResponses: Record<string, object> = {};

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
    return this.tooltips.length > 0;
  }

  get currentTooltip(): DemoTooltip | undefined {
    return this.tooltips[this.currentIndex];
  }

  @Action
  public async setCurrentTooltips(tooltips: DemoTooltip[]) {
    await this.doSetCurrentTooltips(tooltips);

    const tooltip = this.currentTooltip;
    if (tooltip !== undefined) {
      await this.performTooltipAction(tooltip.setup);
    }
  }

  @Mutation
  private doSetCurrentTooltips(tooltips: DemoTooltip[]) {
    resetStoreState(this, baseState);

    if (tooltips.length == 0) {
      this.tooltips = [];
      return;
    }

    tooltips = [INITIAL_TOOLTIP, ...tooltips];

    this.currentIndex = 0;
    tooltips[this.currentIndex].visible = true;
    this.tooltipsLoaded = false;
    this.tooltips = tooltips;
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public loadCyTooltips(lookup: Record<string, cytoscape.Position>) {
    if (this.tooltipsLoaded) {
      return;
    }

    this.tooltips = this.tooltips.map(t => {
      // only do this for cytooltips
      if (t.type !== TooltipType.CyTooltip) {
        return t;
      }

      // lookup the position of the tooltip on the canvas
      const pos = lookup[t.target];
      if (!pos) {
        return t;
      }

      return {
        ...t,
        config: {
          ...t.config,
          ...pos
        }
      };
    });
    this.tooltipsLoaded = true;
  }

  @Action
  public async nextTooltip() {
    if (this.currentTooltip !== undefined) {
      await this.performTooltipAction(this.currentTooltip.teardown);
    }

    this.progressTooltip();

    if (this.currentTooltip !== undefined) {
      await this.performTooltipAction(this.currentTooltip.setup);
    }
  }

  @Mutation
  public progressTooltip() {
    if (this.tooltips.length == 0) {
      return;
    }

    const tooltips = [...this.tooltips];

    tooltips[this.currentIndex].visible = false;

    const nextCurrentTooltip = this.currentIndex + 1;
    if (nextCurrentTooltip < this.tooltips.length) {
      tooltips[nextCurrentTooltip].visible = true;

      this.currentIndex = nextCurrentTooltip;
      this.tooltips = tooltips;
    }
  }

  @Action
  private async performTooltipAction(tooltipAction: DemoTooltipAction | undefined) {
    if (tooltipAction) {
      if (!(tooltipAction.action in this.actionLookup)) {
        console.error('Unable to find action in lookup', tooltipAction.action);
        return;
      }

      this.actionLookup[tooltipAction.action].call(this, tooltipAction);
    }
  }

  @Action
  public async closeEditPane() {
    await this.context.dispatch(`project/editBlockPane/${EditBlockActions.cancelAndResetBlock}`, null, {
      root: true
    });
  }

  @Action
  public async openBlockEditorPane() {
    if (this.currentTooltip !== undefined) {
      await this.context.dispatch(`project/${ProjectViewActions.selectNode}`, this.currentTooltip.target, {
        root: true
      });
    }
  }

  @Action
  public async closeBlockEditorPane() {
    await this.context.dispatch(`project/${ProjectViewActions.clearSelection}`, null, {
      root: true
    });
  }

  @Action
  public async openExecutionsPane() {
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
  public async closeOpenPanes() {
    await this.context.dispatch(`project/editBlockPane/${EditBlockActions.cancelAndResetBlock}`, null, {
      root: true
    });

    await this.context.dispatch(`project/${ProjectViewActions.closePane}`, PANE_POSITION.left, {
      root: true
    });
  }

  @Action
  public async promptUserSignup() {
    await UnauthViewProjectStoreModule.promptDemoModeSignup(true);
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
  public mockGetLogsForExecutions(): BlockExecutionLogData {
    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    const blockId = openedProject.workflow_states[0].id;
    return {
      blockId: blockId,
      logs: {
        demo: {
          function_name: 'asdf',
          log_id: 'demo',
          s3_key: 'test',
          timestamp: 0,
          type: ExecutionStatusType.SUCCESS
        }
      },
      pages: [],
      totalExecutions: 0
    };
  }

  @Action
  public getBlockExecutionLogContentsByLogId(action: DemoTooltipAction): BlockExecutionLogContentsByLogId {
    const execLogsAction = action.options as ViewExecutionLogsOptions;

    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    return {
      demo: {
        ...execLogsAction,
        arn: 'asdf',
        log_id: 'demo',
        project_id: openedProject.project_id,
        timestamp: 0,
        type: ExecutionStatusType.SUCCESS
      }
    };
  }

  @Mutation
  public setBlockExecutionLogContentsByLogId(logs: BlockExecutionLogContentsByLogId) {
    this.mockNetworkResponses = {
      ...this.mockNetworkResponses,
      blockExecutionLogContentsByLogId: logs
    };
  }

  @Action
  public mockContentsForLogs(): BlockExecutionLogContentsByLogId {
    return this.mockNetworkResponses.blockExecutionLogContentsByLogId as BlockExecutionLogContentsByLogId;
  }

  @Action
  public async viewExecutionLogs(action: DemoTooltipAction) {
    const response = this.getBlockExecutionLogContentsByLogId(action);
    this.setBlockExecutionLogContentsByLogId(response);
  }

  @Action
  public getDeploymentExecution(action: DemoTooltipAction): ProductionExecutionResponse {
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
    return {
      executions: {
        demo: {
          errorCount: errorExecs,
          caughtErrorCount: caughtExecs,
          successCount: successfulExecs,
          oldestTimestamp: 0,
          executionId: 'demo',
          numberOfLogs: addExecAction.executions.length,
          blockExecutionGroupByBlockId: blockExecutionGroup
        }
      },
      oldestTimestamp: 0
    };
  }

  @Mutation
  public setDeploymentExecutionResponse(executions: ProductionExecutionResponse) {
    this.mockNetworkResponses = {
      ...this.mockNetworkResponses,
      getProjectExecutions: executions
    };
  }

  @Action
  public addDeploymentExecution(tooltipAction: DemoTooltipAction) {
    const response = this.getDeploymentExecution(tooltipAction);
    this.setDeploymentExecutionResponse(response);
  }

  @Action
  public mockAddDeploymentExecution(): ProductionExecutionResponse {
    return this.mockNetworkResponses.getProjectExecutions as ProductionExecutionResponse;
  }

  get mockGetLatestProjectDeployment(): GetLatestProjectDeploymentResponse {
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
    return {
      result: latestDeploymentResponse,
      success: true
    };
  }

  @Action
  public async viewExampleProjectDeployment() {
    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    router.push({
      name: 'deployment',
      params: {
        projectId: openedProject.project_id
      }
    });
  }
}
