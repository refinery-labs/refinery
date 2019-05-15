import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';

@Component
export default class ViewWorkflow extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="view-workflow">
        <h2>View Workflow</h2>
        Id: {this.$route.params.workflowId}
        <router-view/>
      </div>
    );
  }
}