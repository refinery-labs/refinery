import { VuexModule, Module, Mutation, Action, getModule } from 'vuex-module-decorators';
import uuid from 'uuid/v4';
import store from '@/store/index';
import {
  BlockEnvironmentVariableList,
  LambdaWorkflowState,
  ProjectConfig,
  ProjectEnvironmentVariableList
} from '@/types/graph';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { ProductionLambdaWorkflowState } from '@/types/production-workflow-types';
import { EditBlockMutators } from '@/store/modules/panes/edit-block-pane';
import { ProjectViewMutators } from '@/constants/store-constants';
import { RootState } from '@/store/store-types';

export interface EnvironmentVariablesEditorPaneState {
  isModalVisible: boolean;
  isReadOnlyModalVisible: boolean;

  activeBlockId: string | null;
  activeBlockName: string | null;
  envVariableList: EnvVariableRow[];
}

export interface EnvVariableRow {
  id: string;
  value: string | null;
  name: string;
  description: string;
  required: boolean;
}

export interface OpenEnvironmentVariablesParams {
  block: LambdaWorkflowState;
  config: ProjectConfig;
}

export const baseState: EnvironmentVariablesEditorPaneState = {
  // TODO: Make it so that modals are instantiated by ID or something so that we can have more than two...
  isModalVisible: false,
  isReadOnlyModalVisible: false,
  activeBlockId: null,
  activeBlockName: null,
  envVariableList: []
};

// Must copy so that we can not thrash the pointers...
const initialState = deepJSONCopy(baseState);

@Module({ namespaced: true, dynamic: true, store, name: 'environmentVariablesEditor' })
class EnvironmentVariablesEditorStore extends VuexModule<ThisType<EnvironmentVariablesEditorPaneState>, RootState>
  implements EnvironmentVariablesEditorPaneState {
  public isModalVisible: boolean = initialState.isModalVisible;
  public isReadOnlyModalVisible: boolean = initialState.isModalVisible;

  public activeBlockId: string | null = initialState.activeBlockId;
  public activeBlockName: string | null = initialState.activeBlockName;
  public envVariableList: EnvVariableRow[] = initialState.envVariableList;

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
  public updateVariable({ id, updateFn }: { id: string; updateFn: (envVariable: EnvVariableRow) => void }) {
    const envVariable = this.envVariableList.find(t => t.id === id);

    if (!envVariable) {
      return;
    }

    updateFn(envVariable);

    this.envVariableList = [...this.envVariableList];
  }

  @Mutation
  public addNewVariable() {
    if (!this.activeBlockId) {
      return;
    }

    this.envVariableList.push({
      id: uuid(),
      description: '',
      name: '',
      required: false,
      value: ''
    });
  }

  @Mutation
  public deleteVariable(id: string) {
    if (!this.activeBlockId) {
      return;
    }

    this.envVariableList = this.envVariableList.filter(row => row.id !== id);
  }

  @Mutation
  private editNewBlock(params: OpenEnvironmentVariablesParams) {
    const { block, config } = params;

    const projectEnvironmentVariables = config.environment_variables || {};

    const envVariablesInBlock = Object.keys(block.environment_variables || {});

    this.envVariableList = envVariablesInBlock.map(key => {
      const currentVariable = block.environment_variables[key];

      // Make sure that the key exists on the object
      const value = projectEnvironmentVariables[key] && projectEnvironmentVariables[key].value;

      return {
        id: key,
        value: value !== undefined && value !== null ? value : '',
        name: currentVariable.name,
        description: currentVariable.description,
        required: currentVariable.required
      };
    });

    this.activeBlockId = block.id;
    this.activeBlockName = block.name;
  }

  @Mutation
  private viewNewBlock(block: ProductionLambdaWorkflowState) {
    this.envVariableList = Object.keys(block.environment_variables).map(key => {
      const envVariable = block.environment_variables[key];
      return {
        id: key,
        value: envVariable.value,
        description: envVariable.description,
        required: envVariable.required,
        name: envVariable.name
      };
    });

    this.activeBlockId = block.id;
    this.activeBlockName = block.name;
  }

  @Action
  public setVariableName({ id, name }: { id: string; name: string }) {
    this.updateVariable({ id, updateFn: t => (t.name = name) });
  }

  @Action
  public setVariableValue({ id, value }: { id: string; value: string }) {
    this.updateVariable({ id, updateFn: t => (t.value = value) });
  }

  @Action
  public setVariableDescription({ id, description }: { id: string; description: string }) {
    this.updateVariable({ id, updateFn: t => (t.description = description) });
  }

  @Action
  public setVariableRequired({ id, required }: { id: string; required: boolean }) {
    this.updateVariable({ id, updateFn: t => (t.required = required) });
  }

  @Action
  public editBlockInModal(params: OpenEnvironmentVariablesParams) {
    if (!params || !params.block || !params.config) {
      throw new Error('Cannot open environment variables with missing block or config');
    }

    this.editNewBlock(params);
    this.setModalVisibility({ modalVisibility: true, readOnly: false });
  }

  @Action
  public viewProductionBlockInModal(block: ProductionLambdaWorkflowState) {
    if (!block) {
      throw new Error('Cannot open environment variables with missing production block');
    }

    this.viewNewBlock(block);
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

    if (!this.context.rootState.project.openedProjectConfig) {
      console.error('Missing project config when writing environment variables');
      return;
    }

    const openedProjectConfig = this.context.rootState.project.openedProjectConfig;

    const environmentVariables: BlockEnvironmentVariableList = this.envVariableList.reduce(
      (out: BlockEnvironmentVariableList, t) => {
        out[t.id] = {
          name: t.name,
          required: t.required,
          description: t.description
        };

        return out;
      },
      {}
    );

    const currentBlockEnvironmentVars = this.envVariableList.reduce(
      (outVars: ProjectEnvironmentVariableList, envVariable) => {
        outVars[envVariable.id] = {
          value: envVariable.value !== null ? envVariable.value : '',
          timestamp: Date.now()
        };
        return outVars;
      },
      {}
    );

    const newProjectEnvironmentVars = Object.assign(
      deepJSONCopy(openedProjectConfig.environment_variables),
      deepJSONCopy(currentBlockEnvironmentVars)
    );

    const projectConfig: ProjectConfig = {
      ...openedProjectConfig,
      environment_variables: newProjectEnvironmentVars
    };

    this.resetState();

    this.context.commit(`project/editBlockPane/${EditBlockMutators.setEnvironmentVariables}`, environmentVariables, {
      root: true
    });
    this.context.commit(`project/${ProjectViewMutators.setOpenedProjectConfig}`, projectConfig, { root: true });
    this.context.commit(`project/${ProjectViewMutators.markProjectDirtyStatus}`, true, { root: true });
  }
}

export const EnvironmentVariablesEditorModule = getModule(EnvironmentVariablesEditorStore);
