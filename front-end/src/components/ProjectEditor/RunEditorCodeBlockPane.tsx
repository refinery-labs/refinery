import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import {
  LambdaWorkflowState,
  ProjectConfig,
  RefineryProject,
  SupportedLanguage,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import AceEditor from '@/components/Common/AceEditor.vue';
import {languageToAceLangMap, PANE_POSITION} from '@/types/project-editor-types';
import RunLambda from '@/components/RunLambda';
import {RunCodeBlockLambdaConfig} from '@/store/modules/run-lambda';
import {RunLambdaResult} from '@/types/api-types';

const project = namespace('project');
const editBlock = namespace('project/editBlockPane');
const runLambda = namespace('runLambda');

@Component
export default class RunEditorCodeBlockPane extends Vue {
  // State
  @project.State openedProjectConfig!: ProjectConfig | null;
  @editBlock.State selectedNode!: WorkflowState | null;

  @runLambda.State isRunningLambda!: boolean;
  @runLambda.State devLambdaResult!: RunLambdaResult | null;
  @runLambda.State devLambdaInputData!: string;

  // Mutations
  @runLambda.Mutation setDevLambdaInputData!: (inputData: string) => void;

  // Actions
  @project.Action closePane!: (p: PANE_POSITION) => void;
  @runLambda.Action runSpecifiedEditorCodeBlock!: (config: RunCodeBlockLambdaConfig) => void;

  public getRunLambdaConfig(): RunCodeBlockLambdaConfig | null {
    if (!this.selectedNode || this.selectedNode.type !== WorkflowStateType.LAMBDA || !this.openedProjectConfig) {
      return null;
    }

    return {
      codeBlock: this.selectedNode as LambdaWorkflowState,
      projectConfig: this.openedProjectConfig
    };
  }

  public renderCodeEditor() {
    if (!this.openedProjectConfig) {
      return (
        <span>Please open project!</span>
      );
    }

    if (!this.selectedNode || this.selectedNode.type !== WorkflowStateType.LAMBDA) {
      return (
        <span>Select a Code Block to execute code.</span>
      );
    }

    const config = this.getRunLambdaConfig();

    if (!config) {
      return (
        <span>Invalid run code block config</span>
      );
    }

    const runLambdaProps = {
      onRunLambda: () => this.runSpecifiedEditorCodeBlock(config),
      onUpdateInputData: this.setDevLambdaInputData,
      lambdaId: this.selectedNode.id,
      runResultOutput: this.devLambdaResult,
      inputData: this.devLambdaInputData,
      isCurrentlyRunning: this.isRunningLambda
    };

    return (
      // @ts-ignore
      <RunLambda props={runLambdaProps}
      />
    );
  }

  public render(h: CreateElement): VNode {

    const formClasses = {
      'mb-3 mt-3 text-align--left run-lambda-pane-container': true
    };

    return (
      <div class={formClasses}>
        <div class="run-lambda-pane-container__content overflow--scroll-y-auto">
          {this.renderCodeEditor()}
        </div>
      </div>
    );
  }
}
