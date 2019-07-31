import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import {
  AddGraphElementConfig,
  availableTransitions,
  transitionTypeToConfigLookup
} from '@/constants/project-editor-constants';
import { SupportedLanguage, WorkflowRelationshipType } from '@/types/graph';
import { IfDropDownSelectionType } from '@/store/store-types';
import { Prop } from 'vue-property-decorator';
import { nopWrite } from '@/utils/block-utils';
import { EditorProps, EditTransitionSelectorProps } from '@/types/component-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';

@Component
export default class EditTransitionSelector extends Vue implements EditTransitionSelectorProps {
  @Prop({ required: true }) readOnly!: boolean;

  @Prop({ required: true }) checkIfValidTransitionGetter!: WorkflowRelationshipType[] | null;
  @Prop({ required: true }) newTransitionTypeSpecifiedInFlowState!: WorkflowRelationshipType | null;
  @Prop() selectTransitionAction!: (key: WorkflowRelationshipType) => void;
  @Prop() cancelModifyingTransition?: () => {};
  @Prop() currentlySelectedTransitionType!: WorkflowRelationshipType | null;

  @Prop({ required: true }) ifSelectDropdownValue!: IfDropDownSelectionType;
  @Prop({ required: true }) ifExpression!: string;

  @Prop({ required: true }) ifDropdownSelection!: (dropdownSelection: string) => void;
  @Prop({ required: true }) setIfExpression!: (ifExpression: string) => void;

  private checkIfTransitionEnabled(key: WorkflowRelationshipType) {
    return this.checkIfValidTransitionGetter && this.checkIfValidTransitionGetter.some(t => t === key);
  }

  public renderTransitionSelect(key: WorkflowRelationshipType, transition: AddGraphElementConfig | null) {
    if (!transition) {
      return null;
    }

    const isTransitionEnabled = this.checkIfTransitionEnabled(key);
    const choosingTransition = !this.newTransitionTypeSpecifiedInFlowState;

    const selectTransitionAction = this.readOnly ? nopWrite : this.selectTransitionAction;

    const groupItemClasses = {
      'display--flex': true,
      'add-block--disabled': !isTransitionEnabled
    };

    const icon = <span class={!isTransitionEnabled ? 'icon-ban' : 'icon-check'} />;

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
        on={{ click: () => selectTransitionAction(key) }}
        disabled={!isTransitionEnabled}
        active={(this.newTransitionTypeSpecifiedInFlowState || this.currentlySelectedTransitionType) === key}
        class={groupItemClasses}
        button
      >
        {choosingTransition ? expandedContent : collapsedContent}
      </b-list-group-item>
    );
  }

  renderHelpText() {
    return (
      <b-list-group class="add-transition-container" style={{ margin: '0 0 2px 0' }}>
        <div>
          <b-list-group horizontal>
            {availableTransitions.map(key => this.renderTransitionSelect(key, transitionTypeToConfigLookup[key]))}
          </b-list-group>
        </div>
      </b-list-group>
    );
  }

  public renderCodeEditor() {
    const setIfExpression = this.readOnly ? nopWrite : this.setIfExpression;

    const editorProps: EditorProps = {
      name: `editor-export-project-if-conditional-dropdown`,
      lang: SupportedLanguage.PYTHON_2,
      content: this.ifExpression || '',
      readOnly: this.readOnly,
      wrapText: true,
      onChange: setIfExpression
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  private renderIfConditionalSettings() {
    const ifDropdownSelection = this.readOnly ? nopWrite : this.ifDropdownSelection;

    // This only renders in edit mode.
    const selector = (
      <b-form-select on={{ input: ifDropdownSelection }} value={this.ifSelectDropdownValue} class="mt-2 mb-2">
        <option value={IfDropDownSelectionType.DEFAULT}>
          -- Select an option to get an example conditional expression --
        </option>
        <option value={IfDropDownSelectionType.EQUALS_VALUE}>Returned value equals a specific value.</option>
        <option value={IfDropDownSelectionType.NOT_EQUALS_VALUE}>
          Returned value does NOT equal a specific value.
        </option>
        <option value={IfDropDownSelectionType.EQUALS_TRUE}>Returned value is true.</option>
        <option value={IfDropDownSelectionType.EQUALS_FALSE}>Returned value is false.</option>
        <option value={IfDropDownSelectionType.CUSTOM_CONDITIONAL}>
          [Advanced] Write a custom Python conditional.
        </option>
      </b-form-select>
    );

    return (
      <div class="m-2">
        {!this.readOnly && selector}
        <div class="d-block text-align--left display--flex">
          <div class="width--100percent flex-grow--1" style="height: 200px;">
            {this.renderCodeEditor()}
            <small class="mt-1 d-block text-muted">
              For more information, see the{' '}
              <a href="https://docs.refinerylabs.io/transitions/#if" target="_blank">
                Refinery documentation on the <code>if</code> transition.
              </a>
            </small>
          </div>
        </div>
      </div>
    );
  }

  private renderCancelButton() {
    if (!this.cancelModifyingTransition) {
      return null;
    }

    return (
      <div class="ml-2 mr-2 mb-2">
        <b-button variant="danger" class="col-md-12" on={{ click: this.cancelModifyingTransition }}>
          Cancel
        </b-button>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    if (
      this.newTransitionTypeSpecifiedInFlowState &&
      this.newTransitionTypeSpecifiedInFlowState === WorkflowRelationshipType.IF
    ) {
      return (
        <div>
          {this.renderHelpText()}
          {this.renderIfConditionalSettings()}
          <b-list-group class="add-transition-container" style={{ margin: '0 0 0 0' }}>
            {this.renderCancelButton()}
          </b-list-group>
        </div>
      );
    }
    if (this.newTransitionTypeSpecifiedInFlowState) {
      return (
        <b-list-group class="add-transition-container" style={{ margin: '0 0 0 0' }}>
          {this.renderHelpText()}
          {this.renderCancelButton()}
        </b-list-group>
      );
    }

    return (
      <b-list-group class="add-transition-container" style={{ margin: '0 0 0 0' }}>
        {availableTransitions.map(key => this.renderTransitionSelect(key, transitionTypeToConfigLookup[key]))}
      </b-list-group>
    );
  }
}
