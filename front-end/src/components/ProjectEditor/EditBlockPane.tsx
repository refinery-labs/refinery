import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowState } from '@/types/graph';
import { blockTypeToEditorComponentLookup } from '@/constants/project-editor-constants';

const editBlock = namespace('project/editBlockPane');

// TODO: Add support for Layers
// const layersText = <span>
//   The ARN(s) of the
//   <a href="https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html" target="_blank">layers</a> you
//   wish to use with this Lambda. There is a hard AWS limit of five layers per Lambda.
// </span>;

@Component
export default class EditBlockPane extends Vue {
  @editBlock.State selectedNode!: WorkflowState | null;
  @editBlock.State confirmDiscardModalVisibility!: boolean;
  @editBlock.State wideMode!: boolean;

  @editBlock.Getter isStateDirty!: boolean;

  @editBlock.Mutation setConfirmDiscardModalVisibility!: (visibility: boolean) => void;

  @editBlock.Action cancelAndResetBlock!: () => void;
  @editBlock.Action tryToCloseBlock!: () => void;
  @editBlock.Action saveBlock!: () => void;
  @editBlock.Action deleteBlock!: () => void;

  public saveBlockClicked(e: Event) {
    e.preventDefault();
    this.saveBlock();
  }

  public deleteBlockClicked(e: Event) {
    e.preventDefault();
    this.deleteBlock();
  }

  public renderConfirmDiscardModal() {
    if (!this.selectedNode) {
      return;
    }

    const nameString = `Are you sure you want to discard changes to '${this.selectedNode.name}'?`;

    const modalOnHandlers = {
      hidden: () => this.setConfirmDiscardModalVisibility(false),
      ok: () => this.cancelAndResetBlock()
    };

    return (
      <b-modal
        ref={`confirm-discard-${this.selectedNode.id}`}
        on={modalOnHandlers}
        ok-variant="danger"
        footer-class="p-2"
        title={nameString}
        visible={this.confirmDiscardModalVisibility}
      >
        You will lose any changes made to the block!
      </b-modal>
    );
  }

  public renderContentWrapper() {
    if (!this.selectedNode) {
      return <div />;
    }

    const ActiveEditorComponent = blockTypeToEditorComponentLookup[this.selectedNode.type];

    const props = {
      selectedNode: this.selectedNode as Object,
      readOnly: false as Object
    };

    const formClasses = {
      'mb-3 mt-3 text-align--left': true,
      'edit-block-container__form--normal': !this.wideMode,
      'edit-block-container__form--wide': this.wideMode
    };

    return (
      <b-form class={formClasses} on={{ submit: this.saveBlockClicked }}>
        <div class="edit-block-container__scrollable overflow--scroll-y-auto">
          <ActiveEditorComponent props={props} />
        </div>
        <div class="row edit-block-container__bottom-buttons">
          <b-button-group class="col-12">
            <b-button variant="primary" class="col-8" type="submit" disabled={!this.isStateDirty}>
              Save Block
            </b-button>
            <b-button variant="danger" class="col-4" on={{ click: this.deleteBlockClicked }}>
              Delete
            </b-button>
          </b-button-group>
        </div>
      </b-form>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <b-container class="edit-block-container">
        {this.renderContentWrapper()}
        {this.renderConfirmDiscardModal()}
      </b-container>
    );
  }
}
