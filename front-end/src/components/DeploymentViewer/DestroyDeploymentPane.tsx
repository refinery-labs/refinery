import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';

const deployment = namespace('deployment');

@Component
export default class DestroyDeploymentPane extends Vue {

  public render(h: CreateElement): VNode {
    return (
      <b-list-group class="destroy-deployment-pane-container">
        Destroy Deployment Pane
      </b-list-group>
    );
  }
}
