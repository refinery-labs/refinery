import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import { ScheduleTriggerWorkflowState } from '@/types/graph';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import { BlockScheduleExpressionInput } from '@/components/ProjectEditor/block-components/EditBlockScheduleExpressionPane';
import { namespace } from 'vuex-class';
import { nopWrite } from '@/utils/block-utils';

import uuid from 'uuid/v4';
import { EditBlockPaneProps, EditorProps } from '@/types/component-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { BlockDocumentationButton } from '@/components/ProjectEditor/block-components/EditBlockDocumentationButton';
import { SavedBlockStatusCheckResult } from '@/types/api-types';
const editBlock = namespace('project/editBlockPane');
const viewBlock = namespace('viewBlock');

@Component
export class EditScheduleTriggerBlock extends Vue implements EditBlockPaneProps {
  @Prop({ required: true }) selectedNode!: ScheduleTriggerWorkflowState;
  @Prop({ required: true }) selectedNodeMetadata!: SavedBlockStatusCheckResult | null;
  @Prop({ required: true }) readOnly!: boolean;

  // Deployment
  @viewBlock.State('wideMode') wideModeDeployment!: boolean;
  @viewBlock.Mutation('setWidePanel') setWidePanelDeployment!: (wide: boolean) => void;
  @viewBlock.Action openAwsConsoleForBlock!: () => void;

  // Project Editor
  @editBlock.State wideMode!: boolean;

  @editBlock.Mutation setInputData!: (input_data: string) => void;
  @editBlock.Mutation setWidePanel!: (wide: boolean) => void;

  public renderCodeEditor() {
    const editorProps: EditorProps = {
      name: `schedule-trigger-editor`,
      lang: 'text',
      content: this.selectedNode.input_string,
      onChange: this.setInputData,
      readOnly: this.readOnly
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  public renderAwsLink() {
    if (!this.readOnly) {
      return null;
    }

    return (
      <b-form-group description="Click to open this resource in the AWS Console.">
        <label class="d-block">View in AWS Console:</label>
        <b-button variant="dark" class="col-12" on={{ click: this.openAwsConsoleForBlock }}>
          Open AWS Console
        </b-button>
      </b-form-group>
    );
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
          <b-button on={expandOnClick} class="show-block-container__expand-button">
            <span class="fa fa-angle-double-left" />
          </b-button>
        </div>
        <div class="input-group with-focus show-block-container__code-editor">{this.renderCodeEditor()}</div>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    const blockInputProps: EditBlockPaneProps = {
      selectedNode: this.selectedNode,
      selectedNodeMetadata: this.selectedNodeMetadata,
      readOnly: this.readOnly
    };

    return (
      <div>
        <BlockDocumentationButton props={{ docLink: 'https://docs.refinery.io/blocks/#timer-block' }} />
        <BlockNameInput props={blockInputProps} />
        <BlockScheduleExpressionInput props={blockInputProps} />
        {this.renderCodeEditorContainer()}
        {this.renderAwsLink()}
      </div>
    );
  }
}
