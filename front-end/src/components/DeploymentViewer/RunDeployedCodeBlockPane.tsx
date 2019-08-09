import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { RunLambdaDisplayMode } from '@/components/RunLambda';
import RunDeployedCodeBlockContainer from '@/components/DeploymentViewer/RunDeployedCodeBlockContainer';

const runLambda = namespace('runLambda');

@Component
export default class RunDeployedCodeBlockPane extends Vue {
  // TODO: Clean up this layer so that we don't need this variable here just to display the loading animation...
  @runLambda.State isRunningLambda!: boolean;

  public render(h: CreateElement): VNode {
    const classes = {
      'run-lambda-pane-container__content row overflow--scroll-y-auto overflow--hidden-x padding-left--micro padding-right--micro padding-bottom--normal': true,
      'row overflow--scroll-y-auto': true,
      'padding-left--micro padding-right--micro padding-bottom--normal': true
    };

    return (
      <div class="text-align--left run-lambda-pane-container">
        <div class={classes}>
          <RunDeployedCodeBlockContainer props={{ displayMode: RunLambdaDisplayMode.sidepane }} />
        </div>
      </div>
    );
  }
}
