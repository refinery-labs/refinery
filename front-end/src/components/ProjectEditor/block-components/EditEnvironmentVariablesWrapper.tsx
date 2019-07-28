import Vue, { CreateElement, VNode } from 'vue';
import { Prop } from 'vue-property-decorator';
import { LambdaWorkflowState, ProjectConfig } from '@/types/graph';
import Component from 'vue-class-component';
import {
  EnvironmentVariablesEditor,
  EnvironmentVariablesEditorProps
} from '@/components/ProjectEditor/EnvironmentVariablesEditor';
import { EnvironmentVariablesEditorModule } from '@/store/modules/panes/environment-variables-editor';
import { namespace } from 'vuex-class';
import { ProductionLambdaWorkflowState } from '@/types/production-workflow-types';
import { EditBlockPaneProps } from '@/types/component-types';
import { SavedBlockStatusCheckResult } from '@/types/api-types';

const project = namespace('project');

export interface EditEnvironmentVariablesWrapperProps {
  selectedNode: LambdaWorkflowState;
  readOnly: boolean;
}

@Component
export class EditEnvironmentVariablesWrapper extends Vue
  implements EditEnvironmentVariablesWrapperProps, EditBlockPaneProps {
  @Prop({ required: true }) selectedNode!: LambdaWorkflowState;
  @Prop({ required: true }) selectedNodeMetadata!: SavedBlockStatusCheckResult | null;
  @Prop({ required: true }) readOnly!: boolean;

  @project.State openedProjectConfig!: ProjectConfig | null;

  public onOpenModal() {
    if (!this.selectedNode) {
      return;
    }

    if (this.readOnly) {
      EnvironmentVariablesEditorModule.viewProductionBlockInModal(this.selectedNode as ProductionLambdaWorkflowState);
      return;
    }

    const openedProjectConfig = this.openedProjectConfig as ProjectConfig;

    EnvironmentVariablesEditorModule.editBlockInModal({ block: this.selectedNode, config: openedProjectConfig });
  }

  public render(h: CreateElement): VNode {
    if (!this.selectedNode || !this.openedProjectConfig) {
      return <div>Invalid selected block or project.</div>;
    }

    const environmentVariablesEditorProps: EnvironmentVariablesEditorProps = {
      modalMode: true,
      readOnly: this.readOnly,
      activeBlockId: EnvironmentVariablesEditorModule.activeBlockId,
      activeBlockName: EnvironmentVariablesEditorModule.activeBlockName,
      envVariableList: EnvironmentVariablesEditorModule.envVariableList,
      isModalVisible: this.readOnly
        ? EnvironmentVariablesEditorModule.isReadOnlyModalVisible
        : EnvironmentVariablesEditorModule.isModalVisible,
      onModalHidden: () => EnvironmentVariablesEditorModule.closeModal(this.readOnly),
      addNewVariable: () => EnvironmentVariablesEditorModule.addNewVariable(),
      deleteVariable: id => EnvironmentVariablesEditorModule.deleteVariable(id),
      closeEditor: (discard: boolean) =>
        EnvironmentVariablesEditorModule.closeEditor({ discard, readOnly: this.readOnly }),
      setVariableDescription: (id, description) =>
        EnvironmentVariablesEditorModule.setVariableDescription({ id, description }),
      setVariableName: (id, name) => EnvironmentVariablesEditorModule.setVariableName({ id, name }),
      setVariableRequired: (id, required) => EnvironmentVariablesEditorModule.setVariableRequired({ id, required }),
      setVariableValue: (id, value) => EnvironmentVariablesEditorModule.setVariableValue({ id, value })
    };

    return (
      <div>
        <b-button class="col-12" variant="dark" on={{ click: this.onOpenModal }}>
          {this.readOnly ? 'View' : 'Edit'} Environment Variables
        </b-button>
        <EnvironmentVariablesEditor props={environmentVariablesEditorProps} />
      </div>
    );
  }
}
