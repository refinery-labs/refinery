import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';

@Component
export default class EditWorkflow extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="edit-workflow">
        <h2>Edit Workflow</h2>
        Id: {this.$route.params.workflowId}
        <router-view />
      </div>
    );
  }
}
