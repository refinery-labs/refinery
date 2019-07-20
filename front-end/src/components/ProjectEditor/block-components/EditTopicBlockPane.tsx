import Vue, { CreateElement, VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { SnsTopicWorkflowState } from '@/types/graph';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { BlockDocumentationButton } from '@/components/ProjectEditor/block-components/EditBlockDocumentationButton';
import { EditBlockPaneProps } from '@/types/component-types';
import { SavedBlockStatusCheckResult } from '@/types/api-types';

const viewBlock = namespace('viewBlock');

@Component
export class EditTopicBlock extends Vue implements EditBlockPaneProps {
  @Prop({ required: true }) selectedNode!: SnsTopicWorkflowState;
  @Prop({ required: true }) selectedNodeMetadata!: SavedBlockStatusCheckResult | null;
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
    const editBlockProps: EditBlockPaneProps = {
      selectedNode: this.selectedNode,
      selectedNodeMetadata: this.selectedNodeMetadata,
      readOnly: this.readOnly
    };

    return (
      <div>
        <BlockDocumentationButton props={{ docLink: 'https://docs.refinery.io/blocks/#topic-block' }} />
        <BlockNameInput props={editBlockProps} />
        {this.renderAwsLink()}
      </div>
    );
  }
}
