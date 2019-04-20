import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import '@/styles/app.scss';

// The @Component decorator indicates the class is a Vue component
@Component
export default class AllProjects extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="all-projects-page">
        <h2>All Projects</h2>
        <router-view/>
      </div>
    );
  }
}