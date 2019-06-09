import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';

const deployment = namespace('deployment');

@Component
export default class ViewDeployedTransitionPane extends Vue {

  public render(h: CreateElement): VNode {
    return (
      <b-list-group class="view-deployed-transition-pane-container">
        View Deployed Transition
      </b-list-group>
    );
  }
}
