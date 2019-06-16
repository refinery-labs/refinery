import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {namespace} from 'vuex-class';
import {
  AddGraphElementConfig,
  transitionTypeToConfigLookup,
  availableTransitions
} from '@/constants/project-editor-constants';
import {WorkflowRelationship, WorkflowRelationshipType} from '@/types/graph';
import {getTransitionDataById} from "@/utils/project-helpers";
import EditTransitionSelector from "@/components/ProjectEditor/transition-components/EditTransitionSelector";

const project = namespace('project');
const editTransition = namespace('project/editTransitionPanel');

@Component
export default class EditTransitionPane extends Vue {
  @editTransition.State selectedEdge!: WorkflowRelationship | null;

  @project.Getter
  getValidEditMenuDisplayTransitionTypes!: WorkflowRelationshipType[];

  @editTransition.Action deleteTransition!: () => void;
  @editTransition.Action changeTransitionType!: (RelationshipType: WorkflowRelationshipType) => void;

  @project.Action selectTransitionTypeToEdit!: (transitionType: WorkflowRelationshipType) => void;
  @project.Action cancelEditingTransition!: () => {};

  @project.State
  newTransitionTypeSpecifiedInEditFlow!: WorkflowRelationshipType | null;

  deleteSelectedTransition() {
    this.deleteTransition();
  }

  public render(h: CreateElement): VNode {
    const editTransitionSelectorProps = {
      checkIfValidTransitionGetter: this.getValidEditMenuDisplayTransitionTypes,
      selectTransitionAction: this.selectTransitionTypeToEdit,
      newTransitionTypeSpecifiedInFlowState: this.newTransitionTypeSpecifiedInEditFlow,
      helperText: 'Click the Save Transition button to save your changes.',
      cancelModifyingTransition: this.cancelEditingTransition,
      hasSaveModificationButton: true,
      saveModificationButtonAction: this.changeTransitionType,
      currentlySelectedTransitionType: this.selectedEdge && this.selectedEdge.type
    };

    return (
      <div>
        <EditTransitionSelector props={editTransitionSelectorProps}/>
        <b-list-group-item>
          <b-button on={{click: () => this.deleteSelectedTransition()}} class="col-md-12" variant="danger">
            Delete Transition
          </b-button>
        </b-list-group-item>
      </div>
    );
  }
}
