import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';

@Component
export default class OpenedDeploymentWrapper extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="opened-deployment-wrapper">
        <h2>Opened Deployment Wrapper</h2>
        Id: {this.$route.params.deploymentId}
        <router-view/>
      </div>
    );
  }
}