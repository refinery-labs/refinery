import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {Prop} from 'vue-property-decorator';
import {ScheduleTriggerWorkflowState} from '@/types/graph';
import AceEditor from '@/components/Common/AceEditor.vue';
import {BlockNameInput} from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import {BlockScheduleExpressionInput} from '@/components/ProjectEditor/block-components/EditBlockScheduleExpressionPane';
import {namespace} from 'vuex-class';

const editBlock = namespace('project/editBlockPane');

@Component
export class EditScheduleTriggerBlock extends Vue {
  @Prop() selectedNode!: ScheduleTriggerWorkflowState;

  @editBlock.State wideMode!: boolean;

  @editBlock.Mutation setInputData!: (input_data: string) => void;
  @editBlock.Mutation setWidePanel!: (wide: boolean) => void;

  public renderCodeEditor(id: string) {
    const editorProps = {
      'editor-id': `schedule-trigger-editor-${this.selectedNode.id}-${id}`,
      lang: 'text',
      theme: 'monokai',
      content: this.selectedNode.input_string,
      on: {'change-content': this.setInputData}
    };

    return (
      // @ts-ignore
      <AceEditor
        editor-id={editorProps['editor-id']}
        lang={editorProps.lang}
        theme="monokai"
        content={editorProps.content}
        on={editorProps.on}
      />
    );
  }

  public renderCodeEditorContainer() {
    const selectedNode = this.selectedNode;
    const expandOnClick = {click: () => this.setWidePanel(!this.wideMode)};

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
            <span class="fa fa-angle-double-left"/>
          </b-button>
        </div>
        <div class="input-group with-focus edit-block-container__code-editor">{this.renderCodeEditor('pane')}</div>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockNameInput/>
        <BlockScheduleExpressionInput/>
        {this.renderCodeEditorContainer()}
      </div>
    );
  }
}