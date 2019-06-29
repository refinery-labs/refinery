import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowRelationship, WorkflowRelationshipType } from '@/types/graph';
import EditTransitionSelector from '@/components/ProjectEditor/transition-components/EditTransitionSelector';
import { IfDropDownSelectionType } from '@/store/store-types';
import { EditTransitionSelectorProps } from '@/types/component-types';

const project = namespace('project');
const editTransition = namespace('project/editTransitionPanel');

@Component
export default class EditTransitionPane extends Vue {
  @editTransition.State selectedEdge!: WorkflowRelationship | null;

  @project.Getter getValidEditMenuDisplayTransitionTypes!: WorkflowRelationshipType[];

  @editTransition.Action deleteTransition!: () => void;
  @editTransition.Action changeTransitionType!: (RelationshipType: WorkflowRelationshipType | null) => void;

  @project.Action selectTransitionTypeToEdit!: (transitionType: WorkflowRelationshipType) => void;
  @project.Action cancelEditingTransition!: () => {};

  @project.State newTransitionTypeSpecifiedInEditFlow!: WorkflowRelationshipType | null;

  @project.State ifSelectDropdownValue!: IfDropDownSelectionType;
  @project.State ifExpression!: string;

  @project.Action ifDropdownSelection!: (dropdownSelection: string) => {};
  @project.Action setIfExpression!: (ifExpression: string) => {};

  deleteSelectedTransition() {
    this.deleteTransition();
  }

  public render(h: CreateElement): VNode {
    const editTransitionSelectorProps: EditTransitionSelectorProps = {
      checkIfValidTransitionGetter: this.getValidEditMenuDisplayTransitionTypes,
      selectTransitionAction: this.selectTransitionTypeToEdit,
      newTransitionTypeSpecifiedInFlowState: this.newTransitionTypeSpecifiedInEditFlow,
      helperText: 'Click the Save Transition button to save your changes.',
      cancelModifyingTransition: this.cancelEditingTransition,
      hasSaveModificationButton: true,
      saveModificationButtonAction: this.changeTransitionType,
      currentlySelectedTransitionType: this.selectedEdge && this.selectedEdge.type,

      readOnly: false,

      ifSelectDropdownValue: this.ifSelectDropdownValue,
      ifExpression: this.ifExpression,
      ifDropdownSelection: this.ifDropdownSelection,
      setIfExpression: this.setIfExpression
    };

    return (
      <div>
        <b-list-group-item>
          <b-button on={{ click: () => this.deleteSelectedTransition() }} class="col-md-12" variant="danger">
            <span class="fas fa-trash" /> Delete Transition
          </b-button>
        </b-list-group-item>
        <EditTransitionSelector props={editTransitionSelectorProps} />
      </div>
    );
  }
}
