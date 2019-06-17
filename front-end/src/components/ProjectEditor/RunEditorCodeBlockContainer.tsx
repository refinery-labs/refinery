import Vue from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { LambdaWorkflowState, SupportedLanguage, WorkflowState, WorkflowStateType } from '@/types/graph';
import { PANE_POSITION } from '@/types/project-editor-types';
import RunLambda, { RunLambdaDisplayLocation, RunLambdaDisplayMode } from '@/components/RunLambda';
import { RunLambdaResult } from '@/types/api-types';
import { RunCodeBlockLambdaConfig } from '@/types/run-lambda-types';
import { Prop } from 'vue-property-decorator';
import { libraryBuildArguments } from '@/store/modules/project-view';
import { deepJSONCopy } from '@/lib/general-utils';

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
  @runLambda.State loadingText!: string;

  // Getters
  @runLambda.Getter getRunLambdaConfig!: RunCodeBlockLambdaConfig | null;

  // Mutations
  @editBlock.Mutation setCodeModalVisibility!: (visible: boolean) => void;
  @runLambda.Mutation setDevLambdaInputData!: (inputData: string) => void;
  @runLambda.Mutation setLoadingText!: (loadingText: string) => void;

  @Prop({ required: true }) displayMode!: RunLambdaDisplayMode;

  // Actions
  @project.Action closePane!: (p: PANE_POSITION) => void;
  @project.Action checkBuildStatus!: (libraryBuildArgs: libraryBuildArguments) => boolean;

  @runLambda.Action runSpecifiedEditorCodeBlock!: (config: RunCodeBlockLambdaConfig) => void;

  private getLoadingText(isBuildCached: boolean) {
    if (isBuildCached) {
      return 'Running Code Block...';
    }

    return 'Building libraries and then running Code Block...';
  }

  private async checkBuildRequired(config: RunCodeBlockLambdaConfig) {
    if (this.selectedNode === null || this.selectedNode.type !== WorkflowStateType.LAMBDA) {
      console.error("You don't have a node currently selected so I can't check the build status!");
      return;
    }
    const selectedLambda = deepJSONCopy(this.selectedNode) as LambdaWorkflowState;

    const params = {
      language: selectedLambda.language as SupportedLanguage,
      libraries: selectedLambda.libraries
    } as libraryBuildArguments;
    const isLibraryBuildCached = await this.checkBuildStatus(params);
    this.setLoadingText(this.getLoadingText(isLibraryBuildCached));
    this.runSpecifiedEditorCodeBlock(config);
  }

  public render() {
    if (!this.selectedNode || this.selectedNode.type !== WorkflowStateType.LAMBDA) {
      return <span>Select a Code Block to execute code.</span>;
    }

    const config = this.getRunLambdaConfig;

    if (!config) {
      return <span>Invalid run code block config</span>;
    }

    const runLambdaProps = {
      onRunLambda: () => this.checkBuildRequired(config),
      onUpdateInputData: this.setDevLambdaInputData,
      fullScreenClicked: () => this.setCodeModalVisibility(true),
      lambdaIdOrArn: this.selectedNode.id,
      runResultOutput: this.devLambdaResult,
      runResultOutputId: this.devLambdaResultId,
      inputData: this.devLambdaInputData,
      isCurrentlyRunning: this.isRunningLambda,
      displayLocation: RunLambdaDisplayLocation.editor,
      displayMode: this.displayMode,
      loadingText: this.loadingText
    };

    return <RunLambda props={runLambdaProps} />;
  }
}
