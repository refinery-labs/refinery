import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {GetSavedProjectRequest} from '@/types/api-types';
import {namespace} from 'vuex-class';
import {ActiveLeftSidebarPaneToContainerMapping, LeftSidebarPaneState, LEFT_SIDEBAR_PANE} from '@/types/project-editor-types';
import AddBlockPane from '@/components/ProjectEditor/AddBlockPane';
import {paneTypeToWindowNameLookup} from '@/menu';
import AddTransitionPane from '@/components/ProjectEditor/AddTransitionPane';

const project = namespace('project');

const mappedContainers: ActiveLeftSidebarPaneToContainerMapping = {
  [LEFT_SIDEBAR_PANE.addBlock]: AddBlockPane,
  [LEFT_SIDEBAR_PANE.addTransition]: AddTransitionPane,
  [LEFT_SIDEBAR_PANE.allBlocks]: AddBlockPane,
  [LEFT_SIDEBAR_PANE.allVersions]: AddBlockPane,
  [LEFT_SIDEBAR_PANE.deployProject]: AddBlockPane,
  [LEFT_SIDEBAR_PANE.saveProject]: AddBlockPane
};

@Component
export default class ProjectEditorLeftPaneContainer extends Vue {
  @project.State activeLeftSidebarPane!: LEFT_SIDEBAR_PANE | null;
  @project.State leftSidebarPaneState!: LeftSidebarPaneState;
  @project.Action closeLeftSidebarPane!: () => {};
  
  public render(h: CreateElement): VNode {
  
    if (this.activeLeftSidebarPane === null) {
      return <div />;
    }
    
    const ActiveLeftPane = mappedContainers[this.activeLeftSidebarPane];
    const activeLeftSidebarPaneState = this.leftSidebarPaneState[this.activeLeftSidebarPane];
    
    const headerClasses = {
      'editor-left-pane-instance__modal-header': true,
      'modal-header': true,
      'bg-dark': true,
      'text-light': true
    };
    
    const containerClasses = {
      'project-left-pane-container': true,
      'display--flex': true
    };
    
    return (
      <div class={containerClasses}>
        <div class="modal-dialog editor-left-pane-instance__modal-dialog" role="document">
          <div class="modal-content">
            <div class={headerClasses}>
              <h4 class="modal-title">
                {paneTypeToWindowNameLookup[this.activeLeftSidebarPane]}
              </h4>
              <button type="button" class="close text-white editor-left-pane-instance__close-button" data-dismiss="modal"
                      aria-label="Close" on={{click: this.closeLeftSidebarPane}}>
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
            <ActiveLeftPane props={{paneState: activeLeftSidebarPaneState}} />
          </div>
        </div>
      </div>
    );
  }
}
