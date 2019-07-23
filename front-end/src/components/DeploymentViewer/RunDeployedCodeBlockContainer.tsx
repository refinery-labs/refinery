import Vue from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowState, WorkflowStateType } from '@/types/graph';
import { PANE_POSITION } from '@/types/project-editor-types';
import RunLambda, { RunLambdaDisplayLocation, RunLambdaDisplayMode, RunLambdaProps } from '@/components/RunLambda';
import { RunLambdaResult } from '@/types/api-types';
import { RunCodeBlockLambdaConfig } from '@/types/run-lambda-types';
import { Prop } from 'vue-property-decorator';
import { ProductionLambdaWorkflowState } from '@/types/production-workflow-types';

const deployment = namespace('deployment');
const runLambda = namespace('runLambda');

@Component
export default class RunDeployedCodeBlockContainer extends Vue {
  @Prop({ required: true }) displayMode!: RunLambdaDisplayMode;

  // State
  @runLambda.State isRunningLambda!: boolean;
  @runLambda.State deployedLambdaResult!: RunLambdaResult | null;

  // Getters
  @deployment.Getter getSelectedBlock!: WorkflowState | null;
  @runLambda.Getter getDeployedLambdaInputData!: (id: string) => string;

  // Actions
  @deployment.Action closePane!: (p: PANE_POSITION) => void;
  @runLambda.Action runSelectedDeployedCodeBlock!: (block: ProductionLambdaWorkflowState) => void;
  @runLambda.Action changeDeployedLambdaInputData!: (input: [string, string]) => void;

  public render() {
    const selectedBlock = this.getSelectedBlock as ProductionLambdaWorkflowState;

    if (!selectedBlock || selectedBlock.type !== WorkflowStateType.LAMBDA || !selectedBlock.arn) {
      return (
        <div class="text-align--center width--100percent">
          <h4 class="m-2 padding--normal d-block">Select a Code Block to execute code.</h4>
        </div>
      );
    }

    // The if check above doesn't make the function below happy...
    const selectedBlockArn = selectedBlock.arn as string;
    const inputData = this.getDeployedLambdaInputData(selectedBlock.id);

    const runLambdaProps: RunLambdaProps = {
      onRunLambda: () => this.runSelectedDeployedCodeBlock(selectedBlock),
      onUpdateInputData: (s: string) => this.changeDeployedLambdaInputData([selectedBlock.id, s]),
      lambdaIdOrArn: selectedBlockArn,
      runResultOutput: this.deployedLambdaResult,
      runResultOutputId: null,
      inputData: inputData,
      isCurrentlyRunning: this.isRunningLambda,
      displayLocation: RunLambdaDisplayLocation.deployment,
      displayMode: this.displayMode,
      loadingText: 'Running deployed Code Block...'
    };

    return <RunLambda props={runLambdaProps} />;
  }
}
