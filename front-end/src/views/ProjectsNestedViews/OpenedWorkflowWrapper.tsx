import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';

@Component
export default class OpenedWorkflowWrapper extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="opened-workflow-wrapper">
        <h2>Opened Workflow Wrapper</h2>
        Id: {this.$route.params.workflowId}
        <router-view/>
      </div>
    );
  }
}