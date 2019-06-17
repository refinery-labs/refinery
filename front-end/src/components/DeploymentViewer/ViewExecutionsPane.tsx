import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';

const deployment = namespace('deployment');

@Component
export default class ViewExecutionsPane extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="view-executions-pane-container">
        View Executions
      </div>
    );
  }
}
