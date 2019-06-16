import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowRelationship, WorkflowRelationshipType } from '@/types/graph';
import EditTransitionSelector from '@/components/ProjectEditor/transition-components/EditTransitionSelector';
import { nopWrite } from '@/utils/block-utils';
import { EditTransitionSelectorProps } from '@/types/component-types';

const viewTransition = namespace('viewTransition');

@Component
export default class ViewDeployedTransitionPane extends Vue {
  @viewTransition.State selectedEdge!: WorkflowRelationship | null;

  public render(h: CreateElement): VNode {
    if (!this.selectedEdge) {
      return <div>Please select a transition first.</div>;
    }

    const ifExpression = this.selectedEdge.type === WorkflowRelationshipType.IF ? this.selectedEdge.expression : null;

    const editTransitionSelectorProps: EditTransitionSelectorProps = {
      // Allow all "transitions" to be visible
      checkIfValidTransitionGetter: [
        WorkflowRelationshipType.THEN,
        WorkflowRelationshipType.IF,
        WorkflowRelationshipType.FAN_OUT,
        WorkflowRelationshipType.FAN_IN,
        WorkflowRelationshipType.EXCEPTION,
        WorkflowRelationshipType.ELSE
      ],
      selectTransitionAction: nopWrite,
      newTransitionTypeSpecifiedInFlowState: this.selectedEdge.type,
      helperText: null,
      cancelModifyingTransition: nopWrite,
      hasSaveModificationButton: false,
      saveModificationButtonAction: nopWrite,
      currentlySelectedTransitionType: this.selectedEdge.type,

      readOnly: true,

      ifSelectDropdownValue: null,
      ifExpression: ifExpression,
      ifDropdownSelection: nopWrite,
      setIfExpression: nopWrite
    };

    return (
      <div class="view-deployed-transition-pane-container">
        <EditTransitionSelector props={editTransitionSelectorProps} />
      </div>
    );
  }
}
