import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import {namespace} from 'vuex-class';
import {RunLambdaDisplayMode} from '@/components/RunLambda';
import RunDeployedCodeBlockContainer from '@/components/DeploymentViewer/RunDeployedCodeBlockContainer';

const runLambda = namespace('runLambda');

@Component
export default class RunDeployedCodeBlockPane extends Vue {
  // TODO: Clean up this layer so that we don't need this variable here just to display the loading animation...
  @runLambda.State isRunningLambda!: boolean;

  public render(h: CreateElement): VNode {

    const formClasses = {
      'text-align--left run-lambda-pane-container': true,
      'whirl standard': this.isRunningLambda
    };

    return (
      <div class={formClasses}>
        <div class="run-lambda-pane-container__content overflow--scroll-y-auto mb-3 mt-3">
          <RunDeployedCodeBlockContainer props={{displayMode: RunLambdaDisplayMode.sidepane}} />
        </div>
      </div>
    );
  }
}
