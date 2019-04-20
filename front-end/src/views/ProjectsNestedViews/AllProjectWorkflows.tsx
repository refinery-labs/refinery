import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import '@/styles/app.scss';

// The @Component decorator indicates the class is a Vue component
@Component
export default class AllProjectWorkflows extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="all-project-workflows">
        <h2>All Workflows</h2>
        Id: {this.$route.params.projectId}
      </div>
    );
  }
}