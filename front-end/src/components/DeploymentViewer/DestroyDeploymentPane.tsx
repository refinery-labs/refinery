import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';

const deployment = namespace('deployment');

@Component
export default class DestroyDeploymentPane extends Vue {
  @deployment.Action destroyDeployment!: () => void;

  public render(h: CreateElement): VNode {
    return (
      <b-list-group class="destroy-deployment-pane-container mb-2 mt-2 mr-2 ml-2">
        <h4>
          Are you sure you want to destroy this deployment?
          <br />
          <br />
          This change is permanent!
        </h4>
        <b-button variant="danger" class="mt-2" on={{ click: this.destroyDeployment }}>
          Destroy Deployment
        </b-button>
      </b-list-group>
    );
  }
}
