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
import ProjectEditorLeftPaneContainer from '@/containers/ProjectEditorLeftPaneContainer';
import {LEFT_SIDEBAR_PANE} from '@/types/project-editor-types';

const project = namespace('project');

@Component
export default class OpenedProjectOverview extends Vue {
  @project.State isLoadingProject!: boolean;
  @project.State activeLeftSidebarPane!: LEFT_SIDEBAR_PANE | null;
  
  @project.Getter canSaveProject!: boolean;
  @project.Getter transitionAddButtonEnabled!: boolean;
  
  @project.Action openProject!: (projectId: GetSavedProjectRequest) => {};
  @project.Action openLeftSidebarPane!: (paneType: LEFT_SIDEBAR_PANE) => {};
  
  @Watch('$route', {immediate: true})
  private routeChanged(val: Route, oldVal: Route) {
    // Project is already opened
    if (val && oldVal && val.params.projectId && val.params.projectId === oldVal.params.projectId) {
      return;
    }
    
    this.openProject({id: val.params.projectId});
  }
  
  renderLeftPaneOverlay() {
    return (
      <div class="project-left-pane-overlay-container">
        <ProjectEditorLeftPaneContainer />
      </div>
    );
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
    
    const sidebarNavProps = {
      navItems: SidebarMenuItems,
      activeLeftSidebarPane: this.activeLeftSidebarPane,
      onNavItemClicked: this.openLeftSidebarPane,
      leftSidebarPaneTypeToEnabledCheckFunction: {
        [LEFT_SIDEBAR_PANE.addTransition]: () => this.transitionAddButtonEnabled,
        [LEFT_SIDEBAR_PANE.saveProject]: () => this.canSaveProject
      }
    };
    
    return (
      <div class={containerClasses}>
        <div class="project-sidebar-container">
          <SidebarNav props={sidebarNavProps} />
        </div>
  
        {this.renderLeftPaneOverlay()}
        
        <OpenedProjectGraphContainer />
  
        <Offsidebar/>
      </div>
    );
  }
}