import { VuexModule, Module, Mutation, Action, getModule } from 'vuex-module-decorators';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState } from '@/store/store-types';
import { LambdaWorkflowState } from '@/types/graph';
import { EnvVariableRow, OpenEnvironmentVariablesParams } from '@/store/modules/panes/environment-variables-editor';
import { ProductionLambdaWorkflowState } from '@/types/production-workflow-types';
import { EditBlockMutators } from '@/store/modules/panes/edit-block-pane';
import { ProjectViewMutators } from '@/constants/store-constants';

const storeName = 'blockLayers';

export interface BlockLayersState {
  isModalVisible: boolean;
  isReadOnlyModalVisible: boolean;

  selectedBlock: LambdaWorkflowState | null;
  layers: string[];
}

export const baseState: BlockLayersState = {
  isModalVisible: false,
  isReadOnlyModalVisible: false,

  selectedBlock: null,
  layers: []
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class BlockLayersStore extends VuexModule<ThisType<BlockLayersState>, RootState> implements BlockLayersState {
  public isModalVisible: boolean = initialState.isModalVisible;
  public isReadOnlyModalVisible: boolean = initialState.isReadOnlyModalVisible;

  public selectedBlock: LambdaWorkflowState | null = initialState.selectedBlock;
  public layers: string[] = initialState.layers;

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

  @Action
  public editBlockLayersModal(selectedBlock: LambdaWorkflowState) {
    this.setSelectedBlock(selectedBlock);
    this.setLayers(selectedBlock.layers || []);
    this.setModalVisibility({ modalVisibility: true, readOnly: false });
  }

  @Action
  public viewBlockLayersModal(selectedBlock: ProductionLambdaWorkflowState) {
    this.setSelectedBlock(selectedBlock);
    this.setLayers(selectedBlock.layers || []);
    this.setModalVisibility({ modalVisibility: true, readOnly: true });
  }

  @Action closeModal(readOnly: boolean) {
    this.setModalVisibility({ modalVisibility: false, readOnly });
  }

  @Action closeEditor({ discard, readOnly }: { discard: boolean; readOnly: boolean }) {
    this.setModalVisibility({ modalVisibility: false, readOnly: readOnly });

    if (discard) {
      this.resetState();
      return;
    }

    const layers = deepJSONCopy(this.layers);

    this.resetState();

    this.context.commit(`project/editBlockPane/${EditBlockMutators.setLayers}`, layers, {
      root: true
    });

    this.context.commit(`project/${ProjectViewMutators.markProjectDirtyStatus}`, true, { root: true });
  }
}

export const BlockLayersStoreModule = getModule(BlockLayersStore);
