import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {namespace} from 'vuex-class';
import {
  AddGraphElementConfig,
  availableTransitions,
  transitionTypeToConfigLookup
} from '@/constants/project-editor-constants';
import {SupportedLanguage, WorkflowRelationshipType} from '@/types/graph';
import {languageToAceLangMap} from "@/types/project-editor-types";
import AceEditor from "@/components/Common/AceEditor.vue";
import {IfDropDownSelectionType} from "@/store/store-types";
import {PropsDefinition} from "vue/types/options";
import {Prop} from "vue-property-decorator";

const project = namespace('project');

@Component
export default class EditTransitionSelector extends Vue {
  @Prop({required: true}) checkIfValidTransitionGetter!: WorkflowRelationshipType[];
  @Prop({required: true}) selectTransitionAction!: (key: WorkflowRelationshipType) => {};
  @Prop({required: true}) newTransitionTypeSpecifiedInFlowState!: WorkflowRelationshipType | null;
  @Prop({required: true}) helperText!: string;
  @Prop({required: true}) cancelModifyingTransition!: () => {};
  @Prop({required: false}) saveModificationButtonAction!: (key: WorkflowRelationshipType | null) => {};

  // This isn't as symmetric as I'd like, but the method for adding and
  // editing transitions is fundamentally different \o/
  @Prop({required: true}) hasSaveModificationButton!: boolean;

  @project.State
  ifSelectDropdownValue!: IfDropDownSelectionType;
  @project.State
  ifExpression!: string;

  @project.Action ifDropdownSelection!: (dropdownSelection: string) => {};
  @project.Action setIfExpression!: (ifExpression: string) => {};

  private checkIfTransitionEnabled(key: WorkflowRelationshipType) {
    return this.checkIfValidTransitionGetter.some(t => t === key);
  }

  public renderTransitionSelect(key: WorkflowRelationshipType, transition: AddGraphElementConfig | null) {
    if (!transition) {
      return null;
    }

    const isTransitionEnabled = this.checkIfTransitionEnabled(key);
    const choosingTransition = !this.newTransitionTypeSpecifiedInFlowState;

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
        on={{click: () => this.selectTransitionAction(key)}}
        disabled={!isTransitionEnabled}
        active={this.newTransitionTypeSpecifiedInFlowState === key}
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
      </b-list-group>
    );
  }

  public renderCodeEditor() {
    const editorProps = {
      'editor-id': `editor-export-project-if-conditional-dropdown`,
      // Set Nodejs because it supports JSON
      lang: languageToAceLangMap[SupportedLanguage.PYTHON_2],
      theme: 'monokai',
      content: this.ifExpression,
      on: {'change-content': this.setIfExpression}
    };

    return (
      // @ts-ignore
      <AceEditor
        wrapText={true}
        editor-id={editorProps['editor-id']}
        lang={editorProps.lang}
        theme={editorProps.theme}
        content={editorProps.content}
        on={editorProps.on}
      />
    );
  }

  private renderIfConditionalSettings() {
    return (
      <div>
        <b-form-select
          on={{input: this.ifDropdownSelection}}
          value={this.ifSelectDropdownValue}
          class="mb-3"
        >
          <option value={IfDropDownSelectionType.DEFAULT}>-- Select an option to get an example conditional expression
            --
          </option>
          <option value={IfDropDownSelectionType.EQUALS_VALUE}>Returned value equals a specific value.</option>
          <option value={IfDropDownSelectionType.NOT_EQUALS_VALUE}>Returned value does NOT equal a specific value.
          </option>
          <option value={IfDropDownSelectionType.EQUALS_TRUE}>Returned value is true.</option>
          <option value={IfDropDownSelectionType.EQUALS_FALSE}>Returned value is false.</option>
          <option value={IfDropDownSelectionType.CUSTOM_CONDITIONAL}>[Advanced] Write a custom Python conditional.
          </option>
        </b-form-select>
        <div class="d-block text-center display--flex">
          <div class="width--100percent flex-grow--1" style="height: 200px;">{this.renderCodeEditor()}</div>
        </div>
        <small class="text-align--center mb-3 d-block">
          For more information, see the <a href="https://docs.refinerylabs.io/transitions/#if" target="_blank">Refinery
          documentation on the <code>if</code> transition.</a>
        </small>
      </div>
    );
  }

  private saveModificationButtonActionEvent() {
    this.saveModificationButtonAction(this.newTransitionTypeSpecifiedInFlowState);
  }

  private renderSaveModificationButton() {
    if (this.hasSaveModificationButton) {
      return (
        <b-list-group-item>
          <b-button variant="primary" class="col-md-12"
                    on={{click: this.saveModificationButtonActionEvent}}>
            Save Transition
          </b-button>
        </b-list-group-item>
      )
    }

    return (
      <div></div>
    )
  }

  private renderBlockSelectionHelpText() {
    return (
      <div>
        <b-list-group-item class="text-align--center">
          <h4>{this.helperText}</h4>
        </b-list-group-item>
        {this.renderSaveModificationButton()}
        <b-list-group-item>
          <b-button variant="danger" class="col-md-12" on={{click: this.cancelModifyingTransition}}>
            Cancel
          </b-button>
        </b-list-group-item>
      </div>
    )
  }

  public render(h: CreateElement): VNode {
    if (this.newTransitionTypeSpecifiedInFlowState && this.newTransitionTypeSpecifiedInFlowState === WorkflowRelationshipType.IF) {
      return (
        <div>
          {this.renderHelpText()}
          {this.renderIfConditionalSettings()}
          <b-list-group class="add-transition-container" style={{margin: '0 0 0 0'}}>
            {this.renderBlockSelectionHelpText()}
          </b-list-group>
        </div>
      )
    }
    if (this.newTransitionTypeSpecifiedInFlowState) {
      return (
        <b-list-group class="add-transition-container" style={{margin: '0 0  0'}}>
          {this.renderHelpText()}
          {this.renderBlockSelectionHelpText()}
        </b-list-group>
      )
    }

    return (
      <b-list-group class="add-transition-container" style={{margin: '0 0 0 0'}}>
        {availableTransitions.map(key => this.renderTransitionSelect(key, transitionTypeToConfigLookup[key]))}
      </b-list-group>
    );
  }
}
