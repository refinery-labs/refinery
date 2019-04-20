import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import '@/styles/app.scss';

@Component
export default class EditProjectDeployment extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="edit-project-deployment">
        <h2>Edit Project Deployment</h2>
        Id: {this.$route.params.deploymentId}
        <router-view/>
      </div>
    );
  }
}