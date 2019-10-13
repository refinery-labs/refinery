import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import debounce from 'debounce';
import { WorkflowState, WorkflowStateType } from '@/types/graph';
import { blockTypeToEditorComponentLookup } from '@/constants/project-editor-constants';
import { EditBlockPaneProps } from '@/types/component-types';
import { SavedBlockStatusCheckResult } from '@/types/api-types';
import CreateSavedBlockViewContainer, {
  CreateSavedBlockViewContainerProps
} from '@/components/ProjectEditor/saved-blocks-components/CreateSavedBlockViewContainer';
import Resizer from '@/lib/Resizer';
import { SettingsAppStoreModule } from '@/store';

const editBlock = namespace('project/editBlockPane');

// TODO: Add support for Layers
// const layersText = <span>
//   The ARN(s) of the
//   <a href="https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html" target="_blank">layers</a> you
//   wish to use with this Lambda. There is a hard AWS limit of five layers per Lambda.
// </span>;

@Component
export default class EditBlockPane extends Vue {
  debouncedSetWidth!: (width: number) => void;

  @editBlock.State selectedNode!: WorkflowState | null;
  @editBlock.State selectedNodeMetadata!: SavedBlockStatusCheckResult | null;
  @editBlock.State confirmDiscardModalVisibility!: boolean;

  @editBlock.Getter isStateDirty!: boolean;
  @editBlock.Getter isEditedBlockValid!: boolean;

  @editBlock.Mutation setConfirmDiscardModalVisibility!: (visibility: boolean) => void;

  @editBlock.Action cancelAndResetBlock!: () => void;
  @editBlock.Action tryToCloseBlock!: () => void;
  @editBlock.Action deleteBlock!: () => void;
  @editBlock.Action duplicateBlock!: () => void;
  @editBlock.Action saveBlock!: (close: boolean) => void;

  mounted() {
    const container = this.$refs.container as HTMLElement;

    if (!container) {
      return;
    }

    this.debouncedSetWidth = debounce((width: number) => SettingsAppStoreModule.setEditBlockPaneWidth(width), 200);
  }

  public deleteBlockClicked(e: Event) {
    e.preventDefault();
    this.deleteBlock();
  }

  onSizeChanged(deltaX: number, deltaY: number) {
    const container = this.$refs.container as HTMLElement;

    if (!container) {
      return;
    }

    const newWidth = container.getBoundingClientRect().width - deltaX;
    container.style.width = newWidth + 'px';
    this.debouncedSetWidth(newWidth);
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

    const ActiveEditorComponent = blockTypeToEditorComponentLookup[this.selectedNode.type]();

    const props: EditBlockPaneProps = {
      selectedNode: this.selectedNode,
      readOnly: false,
      selectedNodeMetadata: this.selectedNodeMetadata
    };

    // I have no idea how to manage this with Typescript support, blast!
    // @ts-ignore
    const componentInstance = <ActiveEditorComponent props={props} />;

    return (
      <div class="mb-2 mt-2 text-align--left show-block-container__form">
        <div class="scrollable-pane-container padding-left--normal padding-right--normal">{componentInstance}</div>
        <div class="display--flex show-block-container__bottom-buttons ml-0 mr-3 mt-2">
          <b-button
            variant="success"
            class="mr-1 width--100percent flex-grow--1"
            on={{ click: () => this.saveBlock(true) }}
          >
            Save
          </b-button>
          <b-button variant="info" class="mr-1 ml-1 width--100percent flex-grow--1" on={{ click: this.duplicateBlock }}>
            Duplicate
          </b-button>
          <b-button
            variant="danger"
            class="ml-1 width--100percent flex-grow--1"
            on={{ click: this.deleteBlockClicked }}
          >
            Delete
          </b-button>
        </div>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const createSavedBlockViewContainerProps: CreateSavedBlockViewContainerProps = {
      modalMode: true
    };

    const showResizer = this.selectedNode && this.selectedNode.type === WorkflowStateType.LAMBDA;

    const formClasses = {
      'show-block-container mr-2': true,
      'show-block-container--small ml-2': !showResizer,
      'ml-3': showResizer
    };

    const containerStyle = {
      width: showResizer && SettingsAppStoreModule.getEditBlockPaneWidth
    };

    const resizer = <Resizer props={{ onSizeChanged: this.onSizeChanged }} />;

    return (
      <div class={formClasses} style={containerStyle} ref="container">
        {showResizer && resizer}
        {this.renderContentWrapper()}
        {this.renderConfirmDiscardModal()}
        <CreateSavedBlockViewContainer props={createSavedBlockViewContainerProps} />
      </div>
    );
  }
}
