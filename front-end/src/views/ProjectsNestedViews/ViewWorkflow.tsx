import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import '@/styles/app.scss';

// The @Component decorator indicates the class is a Vue component
@Component
export default class ViewWorkflow extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div className="view-workflow">
        <h2>View Workflow</h2>
        Id: {this.$route.params.workflowId}
        <router-view/>
      </div>
    );
  }
}