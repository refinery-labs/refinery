import Vue, { CreateElement, VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { LambdaWorkflowState } from '@/types/graph';
import Component from 'vue-class-component';
import { ProductionLambdaWorkflowState } from '@/types/production-workflow-types';
import { EditBlockPaneProps } from '@/types/component-types';
import { SavedBlockStatusCheckResult } from '@/types/api-types';
import { BlockLayersEditorProps, EditBlockLayersEditor } from '@/components/ProjectEditor/EditBlockLayersEditor';
import { BlockLayersStoreModule } from '@/store';

export interface EditBlockLayersWrapperProps {
  selectedNode: LambdaWorkflowState;
  selectedNodeMetadata: SavedBlockStatusCheckResult | null;
  readOnly: boolean;
}

@Component
export class EditBlockLayersWrapper extends Vue implements EditBlockLayersWrapperProps, EditBlockPaneProps {
  @Prop({ required: true }) selectedNode!: LambdaWorkflowState;
  @Prop({ required: true }) selectedNodeMetadata!: SavedBlockStatusCheckResult | null;
  @Prop({ required: true }) readOnly!: boolean;

  public onOpenModal() {
    if (!this.selectedNode) {
      return;
    }

    if (this.readOnly) {
      BlockLayersStoreModule.viewBlockLayersModal(this.selectedNode as ProductionLambdaWorkflowState);
      return;
    }

    BlockLayersStoreModule.editBlockLayersModal(this.selectedNode);
  }

  public render(h: CreateElement): VNode {
    if (!this.selectedNode) {
      return <div>Invalid selected block.</div>;
    }

    const selectedNode = this.selectedNode;

    const blockLayersEditorProps: BlockLayersEditorProps = {
      modalMode: true,
      readOnly: this.readOnly,
      activeBlockId: selectedNode.id,
      activeBlockName: selectedNode.name,
      layers: BlockLayersStoreModule.layers,
      canAddMoreLayers: BlockLayersStoreModule.canAddMoreLayers,
      isModalVisible: this.readOnly
        ? BlockLayersStoreModule.isReadOnlyModalVisible
        : BlockLayersStoreModule.isModalVisible,
      onModalHidden: () => BlockLayersStoreModule.closeModal(this.readOnly),
      addNewLayer: () => BlockLayersStoreModule.addNewLayer(),
      deleteLayer: index => BlockLayersStoreModule.deleteLayer(index),
      closeEditor: (discard: boolean) => BlockLayersStoreModule.closeEditor({ discard, readOnly: this.readOnly }),
      updateLayer: (index, value) => BlockLayersStoreModule.updateLayer({ index, value })
    };

    return (
      <div>
        <b-button class="col-12" variant="dark" on={{ click: this.onOpenModal }}>
          {this.readOnly ? 'View' : 'Edit'} Layers
        </b-button>
        <EditBlockLayersEditor props={blockLayersEditorProps} />
      </div>
    );
  }
}
