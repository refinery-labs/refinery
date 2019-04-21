import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';

@Component
export default class ProjectDeployments extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="project-deployments">
        <h2>Project Deployments</h2>
        Id: {this.$route.params.workflowId}
        <router-view/>
      </div>
    );
  }
}