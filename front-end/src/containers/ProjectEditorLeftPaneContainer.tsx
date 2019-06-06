import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {namespace} from 'vuex-class';
import {LeftSidebarPaneState, PANE_POSITION, SIDEBAR_PANE} from '@/types/project-editor-types';
import {paneTypeToWindowNameLookup} from '@/menu';
import {paneToContainerMapping} from '@/constants/project-editor-constants';

const project = namespace('project');

@Component
export default class ProjectEditorLeftPaneContainer extends Vue {
  @project.State activeLeftSidebarPane!: SIDEBAR_PANE | null;
  @project.State leftSidebarPaneState!: LeftSidebarPaneState;
  @project.Action closePane!: (p: PANE_POSITION) => void;
  
  public render(h: CreateElement): VNode {
  
    if (this.activeLeftSidebarPane === null) {
      return <div />;
    }
    
    const ActiveLeftPane = paneToContainerMapping[this.activeLeftSidebarPane];
    const activeLeftSidebarPaneState = this.leftSidebarPaneState[this.activeLeftSidebarPane];
    
    const headerClasses = {
      'editor-pane-instance__modal-header': true,
      'modal-header': true,
      'bg-dark': true,
      'text-light': true
    };
    
    const containerClasses = {
      'project-pane-container display--flex': true
    };
    
    return (
      <div class={containerClasses}>
        <div class="modal-dialog editor-pane-instance__modal-dialog" role="document">
          <div class="modal-content">
            <div class={headerClasses}>
              <h4 class="modal-title">
                {paneTypeToWindowNameLookup[this.activeLeftSidebarPane]}
              </h4>
              <button type="button" class="close text-white editor-pane-instance__close-button" data-dismiss="modal"
                      aria-label="Close" on={{click: () => this.closePane(PANE_POSITION.left)}}>
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
