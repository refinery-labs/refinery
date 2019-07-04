import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowRelationshipType } from '@/types/graph';
import EditTransitionSelector from '@/components/ProjectEditor/transition-components/EditTransitionSelector';
import { EditTransitionSelectorProps } from '@/types/component-types';
import { IfDropDownSelectionType } from '@/store/store-types';

const project = namespace('project');

@Component
export default class AddTransitionPane extends Vue {
  @project.Getter getValidMenuDisplayTransitionTypes!: WorkflowRelationshipType[];

  @project.Action selectTransitionTypeToAdd!: (transitionType: WorkflowRelationshipType) => void;
  @project.Action cancelAddingTransition!: () => {};

  @project.State newTransitionTypeSpecifiedInAddFlow!: WorkflowRelationshipType | null;

  @project.State ifSelectDropdownValue!: IfDropDownSelectionType;
  @project.State ifExpression!: string;

  @project.Action ifDropdownSelection!: (dropdownSelection: string) => {};
  @project.Action setIfExpression!: (ifExpression: string) => {};

  public render(h: CreateElement): VNode {
    const editTransitionSelectorProps: EditTransitionSelectorProps = {
      checkIfValidTransitionGetter: this.getValidMenuDisplayTransitionTypes,
      selectTransitionAction: this.selectTransitionTypeToAdd,
      newTransitionTypeSpecifiedInFlowState: this.newTransitionTypeSpecifiedInAddFlow,
      cancelModifyingTransition: this.cancelAddingTransition,
      readOnly: false,
      currentlySelectedTransitionType: null,
      ifDropdownSelection: this.ifDropdownSelection,
      ifExpression: this.ifExpression,
      ifSelectDropdownValue: this.ifSelectDropdownValue,
      setIfExpression: this.setIfExpression
    };

    return <EditTransitionSelector props={editTransitionSelectorProps} />;
  }
}
