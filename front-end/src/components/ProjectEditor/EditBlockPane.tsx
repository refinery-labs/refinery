import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { ApiEndpointWorkflowState, WorkflowState } from '@/types/graph';
import { blockTypeToEditorComponentLookup } from '@/constants/project-editor-constants';
import { CreateSavedBlockViewStoreModule } from '@/store/modules/panes/create-saved-block-view';
import { Prop } from 'vue-property-decorator';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { CreateSavedBlockViewProps } from '@/types/component-types';
import CreateSavedBlockView from '@/components/ProjectEditor/CreateSavedBlockView';

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
  @editBlock.Getter isEditedBlockValid!: boolean;

  @editBlock.Mutation setConfirmDiscardModalVisibility!: (visibility: boolean) => void;

  @editBlock.Action cancelAndResetBlock!: () => void;
  @editBlock.Action tryToCloseBlock!: () => void;
  @editBlock.Action saveBlock!: () => Promise<void>;
  @editBlock.Action deleteBlock!: () => void;

  public async saveBlockClicked(e: Event) {
    e.preventDefault();
    await this.saveBlock();
    CreateSavedBlockViewStoreModule.openModal();
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
      'show-block-container__form--normal': !this.wideMode,
      'show-block-container__form--wide': this.wideMode
    };

    return (
      <div class={formClasses}>
        <div class="scrollable-pane-container padding-left--normal padding-right--normal">
          <ActiveEditorComponent props={props} />
        </div>
        <div class="row show-block-container__bottom-buttons">
          <b-button-group class="col-12">
            <b-button variant="primary" class="col-8" on={{ click: this.saveBlockClicked }}>
              Create Saved Block
            </b-button>
            <b-button variant="danger" class="col-4" on={{ click: this.deleteBlockClicked }}>
              Delete
            </b-button>
          </b-button-group>
        </div>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const createSavedBlockProps: CreateSavedBlockViewProps = {
      modalMode: true
    };

    return (
      <b-container class="show-block-container">
        {this.renderContentWrapper()}
        {this.renderConfirmDiscardModal()}
        <CreateSavedBlockView props={createSavedBlockProps} />
      </b-container>
    );
  }
}
