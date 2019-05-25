import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import OpenedProjectGraphContainer from '@/containers/OpenedProjectGraphContainer';

@Component
export default class ViewProject extends Vue {
  public render(h: CreateElement): VNode {
    const basePath = `/p/${this.$route.params.projectId}`;
    
    return (
      <div class="view-project-page">
        
        <b-nav tabs justified>
          <b-nav-item exact to={basePath}>Overview</b-nav-item>
          <b-nav-item to={`${basePath}/edit`}>Edit</b-nav-item>
          <b-nav-item to={`${basePath}/deployments`}>Deployments</b-nav-item>
          <b-nav-item to={`${basePath}/usage`}>Usage</b-nav-item>
          <b-nav-item to={`${basePath}/settings`}>Settings</b-nav-item>
        </b-nav>
        
        <router-view />
      </div>
    );
  }
}
