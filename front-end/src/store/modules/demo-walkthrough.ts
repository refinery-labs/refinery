import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import {
  AddDeploymentExecutionOptions,
  CyTooltip,
  DemoMockNetworkResponseLookup,
  DemoTooltip,
  DemoTooltipAction,
  DemoTooltipActionType,
  ExecutionLogsOptions,
  HTMLTooltip,
  SetCodeRunnerInputOptions,
  SetCodeRunnerOutputOptions,
  TooltipType
} from '@/types/demo-walkthrough-types';
import { DeploymentViewActions, ProjectViewActions } from '@/constants/store-constants';
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
import { RunLambdaActions, RunLambdaMutators } from '@/store/modules/run-lambda';
import { EditBlockActions } from '@/store/modules/panes/edit-block-pane';
import cytoscape from 'cytoscape';
import { UnauthViewProjectStoreModule } from '@/store';
import { languages } from 'monaco-editor';

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

const INITIAL_TOOLTIP: HTMLTooltip = {
  type: TooltipType.HTMLTooltip,
  visible: false,
  header: 'Start the walkthrough',
  body: 'Get to know this project and Refinery a little better by clicking through this demo.',
  config: {
    htmlSelector: 'li[data-tooltip-id="editor-nav-item"]',
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
    [DemoTooltipActionType.setCodeRunnerInput]: this.setCodeRunnerInput,
    [DemoTooltipActionType.setCodeRunnerOutput]: this.setCodeRunnerOutput,
    [DemoTooltipActionType.closeEditPane]: this.closeEditPane,
    [DemoTooltipActionType.closeOpenPanes]: this.closeOpenPanes,
    [DemoTooltipActionType.promptUserSignup]: this.promptUserSignup,
    [DemoTooltipActionType.addDeploymentExecution]: this.addDeploymentExecution
  };
  public mockNetworkResponses: DemoMockNetworkResponseLookup = {};

  get cyTooltips(): CyTooltip[] {
    return this.tooltips.filter(t => t.type == TooltipType.CyTooltip).map(t => t as CyTooltip);
  }

  get currentHTMLTooltip(): HTMLTooltip | undefined {
    const htmlTooltips = this.tooltips
      .filter(t => t.visible && t.type == TooltipType.HTMLTooltip)
      .map(t => t as HTMLTooltip);

    if (htmlTooltips.length > 0) {
      return htmlTooltips[0];
    }
    return undefined;
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
  public skipWalkthrough() {
    this.doSetCurrentTooltips([]);
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
  public loadCyTooltips(lookup: Record<string, cytoscape.Position>) {
    if (this.tooltipsLoaded) {
      return;
    }

    this.tooltips = this.tooltips.reduce((tooltips: DemoTooltip[], t: DemoTooltip) => {
      if (t.type == TooltipType.CyTooltip) {
        const cyTooltip = t as CyTooltip;

        // lookup the position of the tooltip on the canvas
        const pos = lookup[cyTooltip.config.blockId];
        if (!pos) {
          // block does not exist on the canvas, so we remove it from the list
          return tooltips;
        }

        const newCyTooltip = {
          ...cyTooltip,
          config: {
            ...cyTooltip.config,
            ...pos
          }
        };

        tooltips.push(newCyTooltip);
      } else {
        tooltips.push(t);
      }
      return tooltips;
    }, []);
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
    } else {
      resetStoreState(this, baseState);
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
    if (this.currentTooltip !== undefined && this.currentTooltip.type === TooltipType.CyTooltip) {
      const currentTooltip = this.currentTooltip as CyTooltip;
      const blockId = currentTooltip.config.blockId;
      await this.context.dispatch(`project/${ProjectViewActions.selectNode}`, blockId, {
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
  public async setCodeRunnerInput(action: DemoTooltipAction) {
    const currentTooltip = this.currentTooltip as CyTooltip;
    const blockId = currentTooltip.config.blockId;

    const codeRunnerInputAction = action.options as SetCodeRunnerInputOptions;
    await this.context.dispatch(
      `runLambda/${RunLambdaActions.changeDevLambdaInputData}`,
      [blockId, JSON.stringify(codeRunnerInputAction.input)],
      {
        root: true
      }
    );
    await this.context.dispatch(
      `runLambda/${RunLambdaActions.changeDevLambdaBackpackData}`,
      [blockId, JSON.stringify(codeRunnerInputAction.backpack)],
      {
        root: true
      }
    );
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
  public getLogDataForExecutions(action: DemoTooltipAction): BlockExecutionLogData {
    const execLogDataOptions = action.options as ExecutionLogsOptions;
    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    const blockId = openedProject.workflow_states[execLogDataOptions.block_index].id;
    return {
      blockId: blockId,
      logs: {
        [execLogDataOptions.log_id]: {
          ...execLogDataOptions.data,
          log_id: execLogDataOptions.log_id
        }
      },
      pages: [],
      totalExecutions: 0
    };
  }

  @Mutation
  public setLogsForExecutions(logData: BlockExecutionLogData) {
    this.mockNetworkResponses.blockExecutionLogData = logData;
  }

  @Action
  public mockExecutionLogData(): BlockExecutionLogData | null {
    return this.mockNetworkResponses.blockExecutionLogData || null;
  }

  @Action
  public async viewExecutionLogData(action: DemoTooltipAction) {
    const logData = this.getLogDataForExecutions(action);
    this.setLogsForExecutions(logData);
  }

  @Action
  public getBlockExecutionLogContentsByLogId(action: DemoTooltipAction): BlockExecutionLogContentsByLogId {
    const execLogsAction = action.options as ExecutionLogsOptions;

    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    return {
      [execLogsAction.log_id]: {
        ...execLogsAction.contents,
        arn: '',
        log_id: execLogsAction.log_id,
        project_id: openedProject.project_id,
        timestamp: 0,
        type: ExecutionStatusType.SUCCESS
      }
    };
  }

  @Mutation
  public setBlockExecutionLogContentsByLogId(logs: BlockExecutionLogContentsByLogId) {
    this.mockNetworkResponses.blockExecutionLogContentsByLogId = logs;
  }

  @Action
  public mockContentsForLogs(): BlockExecutionLogContentsByLogId | null {
    return this.mockNetworkResponses.blockExecutionLogContentsByLogId || null;
  }

  @Action
  public async viewExecutionLogs(action: DemoTooltipAction) {
    const response = this.getBlockExecutionLogContentsByLogId(action);
    this.setBlockExecutionLogContentsByLogId(response);

    this.viewExecutionLogData(action);
  }

  @Action
  public getDeploymentExecution(action: DemoTooltipAction): ProductionExecutionResponse {
    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    const addExecAction = action.options as AddDeploymentExecutionOptions;

    const blockExecutionGroup = addExecAction.executions.reduce((group, execution) => {
      const block = openedProject.workflow_states[execution.block_index];
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
    this.mockNetworkResponses.getProjectExecutions = executions;
  }

  @Action
  public addDeploymentExecution(tooltipAction: DemoTooltipAction) {
    const response = this.getDeploymentExecution(tooltipAction);
    this.setDeploymentExecutionResponse(response);
  }

  @Action
  public mockAddDeploymentExecution(): ProductionExecutionResponse | null {
    return this.mockNetworkResponses.getProjectExecutions || null;
  }

  @Action
  public mockGetLatestProjectDeployment(): GetLatestProjectDeploymentResponse {
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
