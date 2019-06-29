import Vue from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowState, WorkflowStateType } from '@/types/graph';
import { PANE_POSITION } from '@/types/project-editor-types';
import RunLambda, { RunLambdaDisplayLocation, RunLambdaDisplayMode } from '@/components/RunLambda';
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
  @runLambda.State deployedLambdaInputData!: string;

  // Getters
  @deployment.Getter getSelectedBlock!: WorkflowState | null;

  // Mutations
  @runLambda.Mutation setDeployedLambdaInputData!: (inputData: string) => void;

  // Actions
  @deployment.Action closePane!: (p: PANE_POSITION) => void;
  @runLambda.Action runSelectedDeployedCodeBlock!: (arn: string) => void;

  public render() {
    const selectedBlock = this.getSelectedBlock as ProductionLambdaWorkflowState;

    if (!selectedBlock || selectedBlock.type !== WorkflowStateType.LAMBDA || !selectedBlock.arn) {
      return (
        <div class="text-align--center width--100percent">
          <span class="m-2">Select a Code Block to execute code.</span>
        </div>
      );
    }

    // The if check above doesn't make the function below happy...
    const selectedBlockArn = selectedBlock.arn as string;

    const runLambdaProps = {
      onRunLambda: () => this.runSelectedDeployedCodeBlock(selectedBlockArn),
      onUpdateInputData: this.setDeployedLambdaInputData,
      lambdaIdOrArn: selectedBlockArn,
      runResultOutput: this.deployedLambdaResult,
      inputData: this.deployedLambdaInputData,
      isCurrentlyRunning: this.isRunningLambda,
      displayLocation: RunLambdaDisplayLocation.deployment,
      displayMode: this.displayMode,
      loadingText: 'Running deployed Code Block...'
    };

    return <RunLambda props={runLambdaProps} />;
  }
}
