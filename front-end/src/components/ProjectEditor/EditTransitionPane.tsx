import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowRelationship, WorkflowRelationshipType } from '@/types/graph';
import EditTransitionSelector from '@/components/ProjectEditor/transition-components/EditTransitionSelector';
import { IfDropDownSelectionType } from '@/store/store-types';
import { EditTransitionSelectorProps } from '@/types/component-types';

const project = namespace('project');
const editTransition = namespace('project/editTransitionPane');

@Component
export default class EditTransitionPane extends Vue {
  @editTransition.State selectedEdge!: WorkflowRelationship | null;
  @editTransition.State confirmDiscardModalVisibility!: boolean;

  @project.Getter getValidEditMenuDisplayTransitionTypes!: WorkflowRelationshipType[];

  @editTransition.Action deleteTransition!: () => void;
  @editTransition.Action changeTransitionType!: (RelationshipType: WorkflowRelationshipType | null) => void;

  @project.Action selectTransitionTypeToEdit!: (transitionType: WorkflowRelationshipType) => void;
  @project.Action cancelEditingTransition!: () => {};

  @project.State newTransitionTypeSpecifiedInEditFlow!: WorkflowRelationshipType | null;

  @project.State ifSelectDropdownValue!: IfDropDownSelectionType;
  @project.State ifExpression!: string;

  @editTransition.Mutation setConfirmDiscardModalVisibility!: (visibility: boolean) => void;

  @project.Action ifDropdownSelection!: (dropdownSelection: string) => {};
  @project.Action setIfExpression!: (ifExpression: string) => {};
  @editTransition.Action cancelAndResetBlock!: () => void;

  deleteSelectedTransition() {
    this.deleteTransition();
  }

  public renderConfirmDiscardModal() {
    if (!this.selectedEdge) {
      return;
    }

    const nameString = `Are you sure you want to discard changes to '${this.selectedEdge.name}'?`;

    const modalOnHandlers = {
      hidden: () => this.setConfirmDiscardModalVisibility(false),
      ok: () => this.cancelAndResetBlock()
    };

    return (
      <b-modal
        ref={`confirm-discard-${this.selectedEdge.id}`}
        on={modalOnHandlers}
        ok-variant="danger"
        footer-class="p-2"
        title={nameString}
        visible={this.confirmDiscardModalVisibility}
      >
        You will lose any changes made to the transition!
      </b-modal>
    );
  }

  public render(h: CreateElement): VNode {
    const editTransitionSelectorProps: EditTransitionSelectorProps = {
      checkIfValidTransitionGetter: this.getValidEditMenuDisplayTransitionTypes,
      selectTransitionAction: this.selectTransitionTypeToEdit,
      newTransitionTypeSpecifiedInFlowState: this.newTransitionTypeSpecifiedInEditFlow,
      currentlySelectedTransitionType: this.selectedEdge && this.selectedEdge.type,

      readOnly: false,

      ifSelectDropdownValue: this.ifSelectDropdownValue,
      ifExpression: this.ifExpression,
      ifDropdownSelection: this.ifDropdownSelection,
      setIfExpression: this.setIfExpression
    };

    return (
      <div>
        <div class="m-2">
          <b-button on={{ click: () => this.deleteSelectedTransition() }} class="col-md-12" variant="danger">
            <span class="fas fa-trash" /> Delete Transition
          </b-button>
        </div>
        <EditTransitionSelector props={editTransitionSelectorProps} />
        {this.renderConfirmDiscardModal()}
      </div>
    );
  }
}
