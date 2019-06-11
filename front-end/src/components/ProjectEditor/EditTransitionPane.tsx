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

const project = namespace('project');
const editTransition = namespace('project/editTransitionPanel');

@Component
export default class EditTransitionPane extends Vue {
  @project.State
  newTransitionTypeSpecifiedInAddFlow!: WorkflowRelationshipType | null;

  @project.State selectedResource!: string;

  @project.Getter
  getValidMenuDisplayTransitionTypes!: WorkflowRelationshipType[];

  @project.Action selectTransitionTypeToAdd!: (key: WorkflowRelationshipType) => {};
  @project.Action cancelAddingTransition!: () => {};

  @editTransition.Action deleteTransition!: () => void;

  private checkIfTransitionEnabled(key: WorkflowRelationshipType) {
    console.log( "Valid transitions: " );
    console.log( findTransitionsBetweenNodes() );

    return this.getValidMenuDisplayTransitionTypes.some(t => t === key);
  }

  public renderTransitionSelect(key: WorkflowRelationshipType, transition: AddGraphElementConfig | null) {
    if (!transition) {
      return null;
    }

    const isTransitionEnabled = this.checkIfTransitionEnabled(key);
    const choosingTransition = !this.newTransitionTypeSpecifiedInAddFlow;

    const groupItemClasses = {
      'display--flex': true,
      'add-block--disabled': !isTransitionEnabled
    };

    const icon = <span class={!isTransitionEnabled ? 'icon-ban' : 'icon-check'}/>;

    const collapsedContent = (
      <div>
        {transition.name + ' '}
        {icon}
      </div>
    );

    const expandedContent = (
      <div class="flex-column align-items-start add-block__content">
        <div class="d-flex w-100 justify-content-between">
          <h4 class="mb-1">
            {transition.name + ' '}
            {icon}
          </h4>
        </div>

        <p class="mb-1">{transition.description}</p>
      </div>
    );

    return (
      <b-list-group-item
        on={{click: () => this.selectTransitionTypeToAdd(key)}}
        disabled={!isTransitionEnabled}
        active={this.newTransitionTypeSpecifiedInAddFlow === key}
        class={groupItemClasses}
        button
      >
        {choosingTransition ? expandedContent : collapsedContent}
      </b-list-group-item>
    );
  }

  renderHelpText() {
    return (
      <b-list-group class="add-transition-container" style={{margin: '0 0 2px 0'}}>
        <div>
          <b-list-group horizontal>
            {availableTransitions.map(key => this.renderTransitionSelect(key, transitionTypeToConfigLookup[key]))}
          </b-list-group>
        </div>
        <b-list-group-item class="text-align--center">
          <h4>Click on a glowing Block to select the second element for the transition.</h4>
        </b-list-group-item>
        <b-list-group-item>
          <b-button variant="danger" class="col-md-12" on={{click: this.cancelAddingTransition}}>
            Cancel Adding Transition
          </b-button>
        </b-list-group-item>
      </b-list-group>
    );
  }

  deleteSelectedTransition() {
    this.deleteTransition();
  }

  public render(h: CreateElement): VNode {
    if (this.newTransitionTypeSpecifiedInAddFlow) {
      return this.renderHelpText();
    }

    return (
      <div>
        <b-list-group class="add-transition-container" style={{margin: '0 0 2px 0'}}>
          {availableTransitions.map(key => this.renderTransitionSelect(key, transitionTypeToConfigLookup[key]))}
        </b-list-group>
        <div>
          <b-button on={{click: () => this.deleteSelectedTransition()}} block variant="danger">Delete Transition
          </b-button>
        </div>
      </div>
    );
  }
}
