import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';

@Component
export default class HelpPage extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="help-page">
        <h1>Help</h1>
        <br />
        <h4>For documentation about Refinery, please visit our documentation website <a href="https://docs.refinerylabs.io/" rel="">here.</a></h4>
        <br />

        <h4>Please <a href="mailto:support@refinerylabs.io">email</a> us with any questions you have!</h4>
      </div>
    );
  }
}
