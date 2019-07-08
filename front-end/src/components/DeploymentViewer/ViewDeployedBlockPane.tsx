import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowState } from '@/types/graph';
import { blockTypeToEditorComponentLookup } from '@/constants/project-editor-constants';
import {EditBlockPaneProps} from '@/types/component-types';

const viewBlock = namespace('viewBlock');

@Component
export default class ViewDeployedBlockPane extends Vue {
  @viewBlock.State selectedNode!: WorkflowState | null;
  @viewBlock.State confirmDiscardModalVisibility!: boolean;
  @viewBlock.State wideMode!: boolean;

  @viewBlock.Mutation setConfirmDiscardModalVisibility!: (visibility: boolean) => void;

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

    const formClasses = {
      'mb-3 mt-3 text-align--left': true,
      'show-block-container__form--normal': !this.wideMode,
      'show-block-container__form--wide': this.wideMode
    };

    // I have no idea how to manage this with Typescript support, blast!
    // @ts-ignore
    const componentInstance = <ActiveEditorComponent props={props} />;

    return (
      <b-form class={formClasses} on={{ submit: (e: Event) => e.preventDefault() }}>
        <div class="scrollable-pane-container padding-left--normal padding-right--normal">
          {componentInstance}
        </div>
      </b-form>
    );
  }

  public render(h: CreateElement): VNode {
    return <div class="show-block-container container">{this.renderContentWrapper()}</div>;
  }
}
