import Component from 'vue-class-component';
import Vue from 'vue';
import {WorkflowState} from '@/types/graph';
import {namespace} from 'vuex-class';
import {blockNameText} from '@/constants/project-editor-constants';

const editBlock = namespace('project/editBlockPane');

@Component
export class BlockNameInput extends Vue {
  @editBlock.State selectedNode!: WorkflowState | null;
  @editBlock.Mutation setBlockName!: (name: string) => void;

  public render() {
    if (!this.selectedNode) {
      return null;
    }

    const selectedNode = this.selectedNode;

    return (
      <b-form-group id={`block-name-group-${selectedNode.id}`} description={blockNameText}>
        <label class="d-block" htmlFor={`block-name-${selectedNode.id}`}>
          Block Name:
        </label>
        <div class="input-group with-focus">
          <b-form-input
            id={`block-name-${selectedNode.id}`}
            type="text"
            required
            value={selectedNode.name}
            on={{input: this.setBlockName}}
            placeholder="My Amazing Block"
          />
        </div>
      </b-form-group>
    );
  }
}