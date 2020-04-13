import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';

@Component
export default class EditorPaneWrapper extends Vue {
  @Prop() paneTitle!: string;
  @Prop() closePane!: () => void;
  @Prop() tryToCloseBlock!: () => void;

  public renderHeader() {
    const headerClasses = {
      'editor-pane-instance__modal-header': true,
      'modal-header': true,
      'bg-dark': true,
      'text-light': true
    };

    const closeFunction = this.tryToCloseBlock || this.closePane;

    return (
      <div class={headerClasses}>
        <h4 class="modal-title">{this.paneTitle}</h4>
        <button
          type="button"
          class="close text-white editor-pane-instance__close-button"
          data-dismiss="modal"
          aria-label="Close"
          on={{ click: closeFunction }}
        >
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const containerClasses = {
      'project-pane-container display--flex': true
    };

    const tooltipId = `editorpane-${this.paneTitle.replace(' ', '-').toLowerCase()}`;

    return (
      <div class={containerClasses} data-tooltip-id={tooltipId}>
        <div class="editor-pane-instance__modal-dialog" role="document">
          <div class="display--flex flex-direction--column editor-pane-instance__modal-content">
            {this.renderHeader()}
            {this.$slots.pane}
          </div>
        </div>
      </div>
    );
  }
}
