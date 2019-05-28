import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import Offsidebar from '@/components/Layout/Offsidebar.vue';
import OpenedProjectGraphContainer from '@/containers/OpenedProjectGraphContainer';
import {Watch} from 'vue-property-decorator';
import {Route} from 'vue-router';
import {GetSavedProjectRequest} from '@/types/api-types';
import {namespace} from 'vuex-class';
import SidebarNav from '@/components/SidebarNav';
import {SidebarMenuItems} from '@/menu';
import {RefineryProject} from '@/types/graph';

const project = namespace('project');

@Component
export default class OpenedProjectOverview extends Vue {
  @project.State isLoadingProject!: boolean;
  @project.Action openProject!: (projectId: GetSavedProjectRequest) => {};
  
  @Watch('$route', {immediate: true})
  private routeChanged(val: Route, oldVal: Route) {
    // Project is already opened
    if (val && oldVal && val.params.projectId && val.params.projectId === oldVal.params.projectId) {
      return;
    }
    
    this.openProject({id: val.params.projectId});
  }
  
  public render(h: CreateElement): VNode {
  
    // TODO: Add validation of the ID structure
    if (!this.$route.params.projectId) {
      return (
        <h2>Please open a project first</h2>
      );
    }
    
    const containerClasses = {
      'opened-project-overview': true,
      'display--flex': true,
      'flex-grow--1': true
    };
  
    // Show a nice loading animation
    if (this.isLoadingProject) {
      return (
        <div class={{
          ...containerClasses,
          'whirl': true,
          'standard': true
        }}>
        </div>
      );
    }
    
    return (
      <div class={containerClasses}>
        <SidebarNav props={{navItems: SidebarMenuItems}} />
  
        <OpenedProjectGraphContainer />
  
        <Offsidebar/>
      </div>
    );
  }
}