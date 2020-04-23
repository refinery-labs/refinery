import Component from 'vue-class-component';
import Vue from 'vue';
import { WorkflowState } from '@/types/graph';
import { namespace } from 'vuex-class';
import { blockNameText } from '@/constants/project-editor-constants';
import { Prop } from 'vue-property-decorator';
import { EditBlockPaneProps } from '@/types/component-types';
import { SavedBlockStatusCheckResult } from '@/types/api-types';

const editBlock = namespace('project/editBlockPane');

@Component
export class BlockNameInput extends Vue implements EditBlockPaneProps {
  @Prop({ required: true }) selectedNode!: WorkflowState;
  @Prop({ default: null }) selectedNodeMetadata!: SavedBlockStatusCheckResult | null;

  @Prop({ required: true }) readOnly!: boolean;

  @editBlock.Mutation setBlockName!: (name: string) => void;

  public getDescription(isEditor: boolean) {
    if (!isEditor) {
      return null;
    }

    return blockNameText;
  }

  public renderReadOnlyName(selectedNode: WorkflowState) {
    return <h4>{selectedNode.name}</h4>;
  }

  public renderEditableName(selectedNode: WorkflowState) {
    return (
      <div class="input-group with-focus">
        <b-form-input
          id={`block-name-${selectedNode.id}`}
          type="text"
          required
          value={selectedNode.name}
          on={{ input: this.setBlockName }}
          placeholder="My Amazing Block"
        />
      </div>
    );
  }

  public render() {
    if (!this.selectedNode) {
      return null;
    }

    const selectedNode = this.selectedNode;

    const isEditor = !this.readOnly;

    // @ts-ignore
    const arnBlock = this.readOnly && <label class="d-block">Lambda ARN: {selectedNode.arn}</label>;

    return (
      <b-form-group id={`block-name-group-${selectedNode.id}`} description={this.getDescription(isEditor)}>
        <label class="d-block" htmlFor={isEditor && `block-name-${selectedNode.id}`}>
          {this.readOnly ? 'Deployed ' : null}Block Name:
        </label>

        {this.readOnly ? this.renderReadOnlyName(selectedNode) : this.renderEditableName(selectedNode)}

        {this.readOnly ? arnBlock : null}
      </b-form-group>
    );
  }
}
