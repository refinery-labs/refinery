import Vue from 'vue';
import Component from 'vue-class-component';
import {namespace} from 'vuex-class';
import {WorkflowState, WorkflowStateType} from '@/types/graph';
import {PANE_POSITION} from '@/types/project-editor-types';
import RunLambda, {RunLambdaDisplayLocation, RunLambdaDisplayMode} from '@/components/RunLambda';
import {RunLambdaResult} from '@/types/api-types';
import {RunCodeBlockLambdaConfig} from '@/types/run-lambda-types';
import {Prop} from 'vue-property-decorator';

const project = namespace('project');
const editBlock = namespace('project/editBlockPane');
const runLambda = namespace('runLambda');

@Component
export default class RunEditorCodeBlockContainer extends Vue {
  // State
  @editBlock.State selectedNode!: WorkflowState | null;

  @runLambda.State isRunningLambda!: boolean;
  @runLambda.State devLambdaResult!: RunLambdaResult | null;
  @runLambda.State devLambdaResultId!: string | null;
  @runLambda.State devLambdaInputData!: string;

  // Getters
  @runLambda.Getter getRunLambdaConfig!: RunCodeBlockLambdaConfig | null;

  // Mutations
  @editBlock.Mutation setCodeModalVisibility!: (visible: boolean) => void;
  @runLambda.Mutation setDevLambdaInputData!: (inputData: string) => void;

  @Prop({required: true}) displayMode!: RunLambdaDisplayMode;

  // Actions
  @project.Action closePane!: (p: PANE_POSITION) => void;
  @runLambda.Action runSpecifiedEditorCodeBlock!: (config: RunCodeBlockLambdaConfig) => void;

  public render() {
    if (!this.selectedNode || this.selectedNode.type !== WorkflowStateType.LAMBDA) {
      return <span>Select a Code Block to execute code.</span>;
    }

    const config = this.getRunLambdaConfig;

    if (!config) {
      return <span>Invalid run code block config</span>;
    }

    const runLambdaProps = {
      onRunLambda: () => this.runSpecifiedEditorCodeBlock(config),
      onUpdateInputData: this.setDevLambdaInputData,
      fullScreenClicked: () => this.setCodeModalVisibility(true),
      lambdaIdOrArn: this.selectedNode.id,
      runResultOutput: this.devLambdaResult,
      runResultOutputId: this.devLambdaResultId,
      inputData: this.devLambdaInputData,
      isCurrentlyRunning: this.isRunningLambda,
      displayLocation: RunLambdaDisplayLocation.editor,
      displayMode: this.displayMode
    };

    return (
      <RunLambda props={runLambdaProps}/>
    );
  }
}
