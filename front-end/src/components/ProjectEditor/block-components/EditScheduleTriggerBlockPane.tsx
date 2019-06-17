import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import { ScheduleTriggerWorkflowState } from '@/types/graph';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import { BlockScheduleExpressionInput } from '@/components/ProjectEditor/block-components/EditBlockScheduleExpressionPane';
import { namespace } from 'vuex-class';
import { nopWrite } from '@/utils/block-utils';

import uuid from 'uuid/v4';
import { EditorProps } from '@/types/component-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
const editBlock = namespace('project/editBlockPane');
const viewBlock = namespace('viewBlock');

@Component
export class EditScheduleTriggerBlock extends Vue {
  @Prop({ required: true }) selectedNode!: ScheduleTriggerWorkflowState;
  @Prop({ required: true }) readOnly!: boolean;

  // Deployment
  @viewBlock.State('wideMode') wideModeDeployment!: boolean;
  @viewBlock.Mutation('setWidePanel') setWidePanelDeployment!: (wide: boolean) => void;

  // Project Editor
  @editBlock.State wideMode!: boolean;

  @editBlock.Mutation setInputData!: (input_data: string) => void;
  @editBlock.Mutation setWidePanel!: (wide: boolean) => void;

  public renderCodeEditor(id: string) {
    const editorProps: EditorProps = {
      name: `schedule-trigger-editor`,
      lang: 'text',
      content: this.selectedNode.input_string,
      onChange: this.setInputData,
      readOnly: this.readOnly
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  public renderCodeEditorContainer() {
    const selectedNode = this.selectedNode;

    const setWidePanel = this.readOnly ? this.setWidePanelDeployment : this.setWidePanel;
    const wideMode = this.readOnly ? this.wideModeDeployment : this.wideMode;

    const expandOnClick = { click: () => setWidePanel(!wideMode) };

    return (
      <b-form-group
        id={`code-editor-group-${selectedNode.id}`}
        description="Some data to be passed to the connected Code Blocks as input."
      >
        <div class="display--flex">
          <label class="d-block flex-grow--1" htmlFor={`code-editor-${selectedNode.id}`}>
            Edit Return Data:
          </label>
          <b-button on={expandOnClick} class="edit-block-container__expand-button">
            <span class="fa fa-angle-double-left" />
          </b-button>
        </div>
        <div class="input-group with-focus edit-block-container__code-editor">{this.renderCodeEditor('pane')}</div>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockNameInput props={{ selectedNode: this.selectedNode, readOnly: this.readOnly }} />
        <BlockScheduleExpressionInput props={{ selectedNode: this.selectedNode, readOnly: this.readOnly }} />
        {this.renderCodeEditorContainer()}
      </div>
    );
  }
}
