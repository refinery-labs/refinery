import Component from 'vue-class-component';
import Vue, {CreateElement, VNode} from 'vue';
import {Prop} from 'vue-property-decorator';
import {SqsQueueWorkflowState} from '@/types/graph';
import {BlockNameInput} from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import {namespace} from 'vuex-class';
const editBlock = namespace('project/editBlockPane');

@Component
export class EditQueueBlock extends Vue {
  @Prop() selectedNode!: SqsQueueWorkflowState;

  @editBlock.Mutation setBatchSize!: (batch_size: number) => void;

  public renderBatchSize() {
    return (
      <b-form-group id={`block-batch-size-group-${this.selectedNode.id}`}>
        <label class="d-block" htmlFor={`block-batch-size-${this.selectedNode.id}`}>
          Batch Size:
        </label>
        <div class="input-group with-focus">
          <b-form-input
            type="number"
            required
            value={this.selectedNode.batch_size}
            on={{input: this.setBatchSize}}
            placeholder="1"
            min="1"
            max="10"
          />
        </div>
        <small class="form-text text-muted">
          The number of messages to be passed to the connected Code Blocks at once (e.g. 2 at a time).
        </small>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockNameInput/>
        {this.renderBatchSize()}
      </div>
    );
  }
}