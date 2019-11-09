import Vue from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import {
  LambdaWorkflowState,
  RefineryProject,
  SupportedLanguage,
  WorkflowState,
  WorkflowStateType
} from '@/types/graph';
import { PANE_POSITION } from '@/types/project-editor-types';
import RunLambda, { RunLambdaDisplayLocation, RunLambdaDisplayMode, RunLambdaProps } from '@/components/RunLambda';
import { RunLambdaResult } from '@/types/api-types';
import { RunCodeBlockLambdaConfig } from '@/types/run-lambda-types';
import { Prop } from 'vue-property-decorator';
import { deepJSONCopy } from '@/lib/general-utils';
import { checkBuildStatus, LibraryBuildArguments } from '@/store/fetchers/api-helpers';
import { getSelectedLambdaWorkflowState } from '@/utils/project-helpers';

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
  @runLambda.State loadingText!: string;

  // Getters
  @runLambda.Getter getRunLambdaConfig!: RunCodeBlockLambdaConfig | null;
  @runLambda.Getter getDevLambdaInputData!: (id: string) => string;
  @runLambda.Getter getDevLambdaBackpackData!: (id: string) => string;

  // Mutations
  @editBlock.Mutation setCodeModalVisibility!: (visible: boolean) => void;
  @editBlock.Mutation setSavedInputData!: (inputData: string) => void;
  @runLambda.Mutation setLoadingText!: (loadingText: string) => void;

  @Prop({ required: true }) displayMode!: RunLambdaDisplayMode;

  // Actions
  @project.Action closePane!: (p: PANE_POSITION) => void;

  @runLambda.Action runLambdaCode!: (config: RunCodeBlockLambdaConfig) => void;
  @runLambda.Action changeDevLambdaInputData!: (input: [string, string]) => void;
  @runLambda.Action changeDevLambdaBackpackData!: (input: [string, string]) => void;

  public render() {
    if (!this.selectedNode || this.selectedNode.type !== WorkflowStateType.LAMBDA) {
      return (
        <div class="text-align--center width--100percent">
          <span class="m-2 padding--normal d-block">Select a Code Block to execute code.</span>
        </div>
      );
    }

    const selectedNode = this.selectedNode as LambdaWorkflowState;

    const config = this.getRunLambdaConfig;

    if (!config) {
      return <span>Invalid run code block config</span>;
    }

    const inputData = this.getDevLambdaInputData(selectedNode.id);
    const backpackData = this.getDevLambdaBackpackData(selectedNode.id);

    const hasExistingTransform = selectedNode.transform !== null;

    const runLambdaProps: RunLambdaProps = {
      onRunLambda: () => this.runLambdaCode(config),
      onUpdateInputData: (s: string) => this.changeDevLambdaInputData([selectedNode.id, s]),
      onUpdateBackpackData: (s: string) => this.changeDevLambdaBackpackData([selectedNode.id, s]),
      onSaveInputData: () => this.setSavedInputData(inputData),
      fullScreenClicked: () => this.setCodeModalVisibility(true),
      lambdaIdOrArn: this.selectedNode.id,
      runResultOutput: this.devLambdaResult,
      runResultOutputId: this.devLambdaResultId,
      inputData: inputData,
      backpackData: backpackData,
      isCurrentlyRunning: this.isRunningLambda,
      displayLocation: RunLambdaDisplayLocation.editor,
      displayMode: this.displayMode,
      loadingText: this.loadingText,
      hasExistingTransform: hasExistingTransform
    };

    return <RunLambda props={runLambdaProps} />;
  }
}
