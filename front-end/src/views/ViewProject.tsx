import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import RefineryGraph from '@/components/RefineryGraph';

// The @Component decorator indicates the class is a Vue component
@Component
export default class ViewProject extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="view-project-page">
        <h2>View Project</h2>
        Id: {this.$route.params.projectId}
        <router-view />
        {/*<router-view name="graphComponent" />*/}
        <RefineryGraph />
      </div>
    );
  }
}
