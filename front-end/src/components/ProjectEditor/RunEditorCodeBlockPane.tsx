import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import RunEditorCodeBlockContainer from '@/components/ProjectEditor/RunEditorCodeBlockContainer';
import { namespace } from 'vuex-class';
import { RunLambdaDisplayMode } from '@/components/RunLambda';

const runLambda = namespace('runLambda');

@Component
export default class RunEditorCodeBlockPane extends Vue {
  // TODO: Clean up this layer so that we don't need this variable here just to display the loading animation...
  @runLambda.State isRunningLambda!: boolean;

  public render(h: CreateElement): VNode {
    return (
      <div class="text-align--left run-lambda-pane-container">
        <div class="run-lambda-pane-container__content row overflow--scroll-y-auto mb-3 mt-3">
          <RunEditorCodeBlockContainer props={{ displayMode: RunLambdaDisplayMode.sidepane }} />
        </div>
      </div>
    );
  }
}
