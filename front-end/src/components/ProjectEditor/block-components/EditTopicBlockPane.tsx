import Vue, { CreateElement, VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { SnsTopicWorkflowState } from '@/types/graph';
import { BlockNameInput } from '@/components/ProjectEditor/block-components/EditBlockNamePane';
import Component from 'vue-class-component';

@Component
export class EditTopicBlock extends Vue {
  @Prop({ required: true }) selectedNode!: SnsTopicWorkflowState;
  @Prop({ required: true }) readOnly!: boolean;

  public render(h: CreateElement): VNode {
    return (
      <div>
        <BlockNameInput props={{ selectedNode: this.selectedNode, readOnly: this.readOnly }} />
      </div>
    );
  }
}
