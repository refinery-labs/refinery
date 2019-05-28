import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';

@Component
export default class ProjectNotFound extends Vue {
  mounted() {
    // Redirect to the projectId base (if a project id exists in the path)
    if (this.$route.params.projectId) {
      this.$router.push({
        name: 'project',
        params: {
          projectId: this.$route.params.projectId
        }
      });
      return;
    }
    
    // Redirect to view all projects
    this.$router.push({ name: 'allProjects' });
  }
  
  public render(h: CreateElement): VNode {
    return (
      <div class="page-not-found-page">
        <h2>Project Not Found, sorry about that!</h2>
        <router-view />
      </div>
    );
  }
}
