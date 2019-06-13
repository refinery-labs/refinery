import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {namespace} from 'vuex-class';
import {WorkflowRelationshipType} from '@/types/graph';
import EditTransitionSelector from "@/components/ProjectEditor/transition-components/EditTransitionSelector";

const project = namespace('project');

@Component
export default class AddTransitionPane extends Vue {
  @project.Getter
  getValidMenuDisplayTransitionTypes!: WorkflowRelationshipType[];

  @project.Action selectTransitionTypeToAdd!: (transitionType: WorkflowRelationshipType) => void;
  @project.Action cancelAddingTransition!: () => {};

  @project.State
  newTransitionTypeSpecifiedInAddFlow!: WorkflowRelationshipType | null;

  public render(h: CreateElement): VNode {
    const editTransitionSelectorProps = {
      "checkIfValidTransitionGetter": this.getValidMenuDisplayTransitionTypes,
      "selectTransitionAction": this.selectTransitionTypeToAdd,
      "newTransitionTypeSpecifiedInFlowState": this.newTransitionTypeSpecifiedInAddFlow,
      "helperText": "Click on a glowing Block to select the second element for the transition.",
      "cancelModifyingTransition": this.cancelAddingTransition,
      "hasSaveModificationButton": false,
    }

    return (
      <EditTransitionSelector props={editTransitionSelectorProps}/>
    );
  }
}
