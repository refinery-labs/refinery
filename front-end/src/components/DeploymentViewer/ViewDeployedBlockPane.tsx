import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';

const deployment = namespace('deployment');

@Component
export default class ViewDeployedBlockPane extends Vue {

  public render(h: CreateElement): VNode {
    return (
      <b-list-group class="view-deployed-block-pane-container">
        View Deployed Block
      </b-list-group>
    );
  }
}
