import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {Prop} from 'vue-property-decorator';

@Component
export default class EditorPaneWrapper extends Vue {
  @Prop() paneTitle!: string;
  @Prop() closePane!: () => void;
  
  public renderHeader() {
  
    const headerClasses = {
      'editor-pane-instance__modal-header': true,
      'modal-header': true,
      'bg-dark': true,
      'text-light': true
    };
    
    return (
      <div class={headerClasses}>
        <h4 class="modal-title">
          {this.paneTitle}
        </h4>
        <button type="button" class="close text-white editor-pane-instance__close-button" data-dismiss="modal"
                aria-label="Close" on={{click: this.closePane}}>
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
    );
  }
  
  public render(h: CreateElement): VNode {
    
    const containerClasses = {
      'project-pane-container display--flex': true
    };
    
    return (
      <div class={containerClasses}>
        <div class="modal-dialog editor-pane-instance__modal-dialog" role="document">
          <div class="modal-content">
            {this.renderHeader()}
            {this.$slots.pane}
          </div>
        </div>
      </div>
    );
  }
}
