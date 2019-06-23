import Component from 'vue-class-component';
import Vue, { CreateElement, VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { SqsQueueWorkflowState } from '@/types/graph';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import { namespace } from 'vuex-class';
import { nopWrite } from '@/utils/block-utils';
import { BlockDocumentationButton } from '@/components/ProjectEditor/block-components/EditBlockDocumentationButton';

const editBlock = namespace('project/editBlockPane');
const viewBlock = namespace('viewBlock');

@Component
export class EditQueueBlock extends Vue {
  @Prop({ required: true }) selectedNode!: SqsQueueWorkflowState;
  @Prop({ required: true }) readOnly!: boolean;
  @viewBlock.Action openAwsConsoleForBlock!: () => void;

  @editBlock.Mutation setBatchSize!: (batch_size: number) => void;

  public renderBatchSize() {
    const setBatchSize = this.readOnly ? nopWrite : this.setBatchSize;
    return (
      <b-form-group id={`block-batch-size-group-${this.selectedNode.id}`}>
        <label class="d-block" htmlFor={`block-batch-size-${this.selectedNode.id}`}>
          Batch Size:
        </label>
        <div class="input-group with-focus">
          <b-form-input
            type="number"
            required
            readonly={this.readOnly}
            value={this.selectedNode.batch_size}
            on={{ input: setBatchSize }}
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

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockDocumentationButton props={{ docLink: 'https://docs.refinery.io/blocks/#queue-block' }} />
        <BlockNameInput props={{ selectedNode: this.selectedNode, readOnly: this.readOnly }} />
        {this.renderBatchSize()}
        {this.renderAwsLink()}
      </div>
    );
  }
}
