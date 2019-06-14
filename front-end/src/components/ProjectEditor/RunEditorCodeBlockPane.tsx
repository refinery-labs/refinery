import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import RunEditorCodeBlockContainer from '@/components/ProjectEditor/RunEditorCodeBlockContainer';
import {namespace} from 'vuex-class';

const runLambda = namespace('runLambda');

@Component
export default class RunEditorCodeBlockPane extends Vue {
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
          <RunEditorCodeBlockContainer props={{showFullscreenButton: true}} />
        </div>
      </div>
    );
  }
}
