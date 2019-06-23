import Vue, { CreateElement, VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { SnsTopicWorkflowState } from '@/types/graph';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { BlockDocumentationButton } from '@/components/ProjectEditor/block-components/EditBlockDocumentationButton';

const viewBlock = namespace('viewBlock');

@Component
export class EditTopicBlock extends Vue {
  @Prop({ required: true }) selectedNode!: SnsTopicWorkflowState;
  @Prop({ required: true }) readOnly!: boolean;

  @viewBlock.Action openAwsConsoleForBlock!: () => void;

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
        <BlockDocumentationButton props={{ docLink: 'https://docs.refinery.io/blocks/#topic-block' }} />
        <BlockNameInput props={{ selectedNode: this.selectedNode, readOnly: this.readOnly }} />
        {this.renderAwsLink()}
      </div>
    );
  }
}
