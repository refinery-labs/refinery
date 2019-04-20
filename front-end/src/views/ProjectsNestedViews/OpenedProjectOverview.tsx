import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import '@/styles/app.scss';

// The @Component decorator indicates the class is a Vue component
@Component
export default class OpenedProjectOverview extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="opened-project-overview">
        <h2>Opened Project</h2>
        Id: {this.$route.params.projectId}
      </div>
    );
  }
}