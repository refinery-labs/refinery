import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import debounce from 'debounce';
import { WorkflowState, WorkflowStateType } from '@/types/graph';
import { blockTypeToEditorComponentLookup } from '@/constants/project-editor-constants';
import { EditBlockPaneProps } from '@/types/component-types';
import Resizer from '@/lib/Resizer';
import { SettingsAppStoreModule } from '@/store';

const viewBlock = namespace('viewBlock');

@Component
export default class ViewDeployedBlockPane extends Vue {
  debouncedSetWidth!: (width: number) => void;

  @viewBlock.State selectedNode!: WorkflowState | null;
  @viewBlock.State confirmDiscardModalVisibility!: boolean;

  @viewBlock.Mutation setConfirmDiscardModalVisibility!: (visibility: boolean) => void;

  mounted() {
    const container = this.$refs.container as HTMLElement;

    if (!container) {
      return;
    }

    this.debouncedSetWidth = debounce((width: number) => SettingsAppStoreModule.setEditBlockPaneWidth(width), 200);
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

  public renderContentWrapper() {
    if (!this.selectedNode) {
      return <div />;
    }

    const ActiveEditorComponent = blockTypeToEditorComponentLookup[this.selectedNode.type]();

    // The Typescript support here is a huge pain... Just cast to Object and it will work. *shakes head*
    const props: EditBlockPaneProps = {
      selectedNode: this.selectedNode,
      selectedNodeMetadata: null,
      readOnly: true
    };

    // I have no idea how to manage this with Typescript support, blast!
    // @ts-ignore
    const componentInstance = <ActiveEditorComponent props={props} />;

    return (
      <b-form
        class="mb-2 mt-2 text-align--left show-block-container__form"
        on={{ submit: (e: Event) => e.preventDefault() }}
      >
        <div class="scrollable-pane-container padding-left--normal padding-right--normal">{componentInstance}</div>
      </b-form>
    );
  }

  public render(h: CreateElement): VNode {
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
      </div>
    );
  }
}
