import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { DemoTooltip, DemoTooltipAction, DemoTooltipActionType, TooltipType } from '@/types/demo-walkthrough-types';
import {
  DeploymentViewActions,
  DeploymentViewMutators,
  ProjectViewActions,
  ProjectViewMutators
} from '@/constants/store-constants';
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
import { SIDEBAR_PANE } from '@/types/project-editor-types';
import { RunLambdaMutators } from '@/store/modules/run-lambda';

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

const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: StoreType.demoWalkthrough })
export class DemoWalkthroughStore extends VuexModule<ThisType<DemoWalkthroughState>, RootState>
  implements DemoWalkthroughState {
  public currentTooltip: number = initialState.currentTooltip;
  public tooltips: DemoTooltip[] = initialState.tooltips;
  public tooltipsLoaded: boolean = initialState.tooltipsLoaded;
  public actionLookup: Record<DemoTooltipActionType, () => void> = {
    [DemoTooltipActionType.openBlockEditorPane]: this.openBlockEditorPane,
    [DemoTooltipActionType.closeBlockEditorPane]: this.closeBlockEditorPane,
    [DemoTooltipActionType.viewDeployment]: this.viewExampleProjectDeployment,
    [DemoTooltipActionType.openExecutionsPane]: this.openExecutionsPane,
    [DemoTooltipActionType.addDeploymentExecution]: this.addDeploymentExecution,
    [DemoTooltipActionType.viewExecutionLogs]: this.viewExecutionLogs,
    [DemoTooltipActionType.openCodeRunner]: this.openCodeRunner,
    [DemoTooltipActionType.setCodeRunnerOutput]: this.setCodeRunnerOutput
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
    if (tooltips.length == 0) {
      this.tooltips = [];
      return;
    }

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
      if (pos) {
        tooltips[i].config = {
          ...tooltips[i].config,
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
  public async doTooltipSetupAction() {
    const setup = this.tooltips[this.currentTooltip].setup;
    if (setup) {
      await this.actionLookup[setup.action].call(this);
    }
  }

  @Action
  public async doTooltipTeardownAction() {
    const teardown = this.tooltips[this.currentTooltip].teardown;
    if (teardown) {
      await this.actionLookup[teardown.action].call(this);
    }
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
  public async setCodeRunnerOutput() {
    const result: RunLambdaResult = {
      is_error: false,
      version: '1',
      logs: 'test',
      truncated: false,
      status_code: 200,
      arn: 'test',
      returned_data: 'asdf'
    };
    await this.context.commit(`runLambda/${RunLambdaMutators.setDevLambdaRunResult}`, result, {
      root: true
    });
  }

  @Action
  public async viewExecutionLogs() {
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
        arn: 'asdf',
        backpack: {},
        input_data: 'asdf',
        log_id: 'test',
        name: 'asdf',
        program_output: 'asdf',
        project_id: openedProject.project_id,
        return_data: 'asdf',
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
    await this.context.dispatch(`deploymentExecutions/${DeploymentExecutionsActions.selectLogByLogId}`, 'demo', {
      root: true
    });

    await this.context.dispatch(`deploymentExecutions/${DeploymentExecutionsActions.doOpenExecutionGroup}`, 'demo', {
      root: true
    });
  }

  @Action
  public async addDeploymentExecution() {
    const openedProject = this.context.rootState.project.openedProject as RefineryProject;
    const blockId = openedProject.workflow_states[0].id;
    const blockName = openedProject.workflow_states[0].name;
    const projectExecutions: ProjectExecutionsByExecutionId = {
      demo: {
        errorCount: 0,
        caughtErrorCount: 0,
        successCount: 1,
        oldestTimestamp: 0,
        executionId: 'demo',
        numberOfLogs: 1,
        blockExecutionGroupByBlockId: {
          [blockId]: {
            executionStatus: ExecutionStatusType.SUCCESS,
            executionResult: {
              arn: '',
              SUCCESS: 0,
              EXCEPTION: 0,
              CAUGHT_EXCEPTION: 0
            },
            timestamp: 0,
            totalExecutionCount: 1,
            executionId: 'demo',
            blockId: blockId,
            blockName: blockName,
            blockArn: ''
          }
        }
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
