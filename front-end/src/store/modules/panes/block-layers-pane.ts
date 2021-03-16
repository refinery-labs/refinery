import { VuexModule, Module, Mutation, Action } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { LambdaWorkflowState } from '@/types/graph';
import { ProductionLambdaWorkflowState } from '@/types/production-workflow-types';
import { EditBlockMutators } from '@/store/modules/panes/edit-block-pane';
import { ProjectViewMutators } from '@/constants/store-constants';
import { LoggingAction } from '@/lib/LoggingMutation';

const storeName = StoreType.blockLayers;

export interface BlockLayersState {
  isModalVisible: boolean;
  isReadOnlyModalVisible: boolean;

  selectedBlock: LambdaWorkflowState | null;
  layers: string[];
  container: string;
}

export const baseState: BlockLayersState = {
  isModalVisible: false,
  isReadOnlyModalVisible: false,

  selectedBlock: null,
  layers: [],
  container: ''
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, name: storeName })
export class BlockLayersStore extends VuexModule<ThisType<BlockLayersState>, RootState> implements BlockLayersState {
  public isModalVisible: boolean = initialState.isModalVisible;
  public isReadOnlyModalVisible: boolean = initialState.isReadOnlyModalVisible;

  public selectedBlock: LambdaWorkflowState | null = initialState.selectedBlock;
  public layers: string[] = initialState.layers;
  public container: string = initialState.container;

  get canAddMoreLayers() {
    return this.layers.length < 4;
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public setModalVisibility({ modalVisibility, readOnly }: { modalVisibility: boolean; readOnly: boolean }) {
    if (readOnly) {
      this.isReadOnlyModalVisible = modalVisibility;
      return;
    }
    this.isModalVisible = modalVisibility;
  }

  @Mutation
  public updateContainer(container: string) {
    this.container = container;
  }

  @Mutation
  public updateLayer({ index, value }: { index: number; value: string }) {
    this.layers[index] = value;

    // Make a copy of the array to force Vuex to refresh components
    this.layers = [...this.layers];
  }

  @Mutation
  public deleteLayer(index: number) {
    this.layers = this.layers.filter((row, i) => i !== index);
  }

  @Mutation
  public setSelectedBlock(selectedBlock: LambdaWorkflowState | null) {
    this.selectedBlock = selectedBlock;
  }

  @Mutation
  public setLayers(layers: string[]) {
    this.layers = deepJSONCopy(layers);
  }

  @Mutation
  public addNewLayer() {
    // Don't allow specifying more than 4 layers.
    if (this.layers.length >= 4) {
      return;
    }

    this.layers = [...this.layers, ''];
  }

  @LoggingAction
  public editBlockLayersModal(selectedBlock: LambdaWorkflowState) {
    this.setSelectedBlock(selectedBlock);
    this.setLayers(selectedBlock.layers || []);
    this.setModalVisibility({ modalVisibility: true, readOnly: false });
  }

  @LoggingAction
  public viewBlockLayersModal(selectedBlock: ProductionLambdaWorkflowState) {
    this.setSelectedBlock(selectedBlock);
    this.setLayers(selectedBlock.layers || []);
    this.setModalVisibility({ modalVisibility: true, readOnly: true });
  }

  @LoggingAction closeModal(readOnly: boolean) {
    this.setModalVisibility({ modalVisibility: false, readOnly });
  }

  @LoggingAction async closeEditor({ discard, readOnly }: { discard: boolean; readOnly: boolean }) {
    this.setModalVisibility({ modalVisibility: false, readOnly: readOnly });

    if (discard) {
      this.resetState();
      return;
    }

    const layers = deepJSONCopy(this.layers);
    const container = this.container;

    this.resetState();

    await this.context.commit(`project/editBlockPane/${EditBlockMutators.setLayers}`, layers, {
      root: true
    });

    await this.context.commit(`project/editBlockPane/${EditBlockMutators.setContainer}`, container, {
      root: true
    });

    await this.context.commit(`project/${ProjectViewMutators.markProjectDirtyStatus}`, true, { root: true });
  }
}
