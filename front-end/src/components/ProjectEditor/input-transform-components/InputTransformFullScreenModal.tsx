import Component from 'vue-class-component';
import Vue from 'vue';
import Split from '@/components/Common/Split.vue';
import SplitArea from '@/components/Common/SplitArea.vue';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps } from '@/types/component-types';
import { InputTransformEditorStoreModule } from '@/store';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import moment from 'moment';
import { BlockCachedInputIOTypes, BlockCachedInputOriginTypes, BlockCachedInputResult } from '@/types/api-types';
import { getNodeDataById } from '@/utils/project-helpers';
import RunLambdaModule from '@/store/modules/run-lambda';
import { namespace } from 'vuex-class';
import { LambdaWorkflowState, WorkflowState } from '@/types/graph';
import { getExampleMapObjectKeysToTargetKeysQuery } from '@/utils/transform-utils';

const runLambda = namespace('runLambda');
const editBlock = namespace('project/editBlockPane');

@Component
export default class InputTransformFullScreenModal extends Vue {
  @runLambda.Getter getDevLambdaInputData!: (id: string) => string;
  @editBlock.State selectedNode!: WorkflowState | null;

  public renderObjectKeysToTargetKeysButton() {
    const exampleQueryString = getExampleMapObjectKeysToTargetKeysQuery(
      InputTransformEditorStoreModule.inputData,
      InputTransformEditorStoreModule.targetInputData
    );

    // If we got a null, this button is not enabled.
    if (exampleQueryString === null) {
      return null;
    }

    const onClickHandler = () => {
      InputTransformEditorStoreModule.setJqQuery(exampleQueryString);
      InputTransformEditorStoreModule.updateSuggestions();
    };

    return (
      <div>
        <b-button pill variant="info" on={{ click: onClickHandler }}>
          <i class="fas fa-magic" /> Map Input Object Keys to Target Object Keys
        </b-button>
      </div>
    );
  }

  public renderJQSuggestions() {
    const enabledTransformButtons = [this.renderObjectKeysToTargetKeysButton()];

    // If there are no valid buttons to show, we just hide the suggestions
    const displaySuggestedTransforms = enabledTransformButtons.every(buttonElement => {
      return buttonElement !== null;
    });
    if (!displaySuggestedTransforms) {
      return [];
    }

    return (
      <div class="mt-4">
        <h2>Suggested Transforms</h2>
        <div class="mt-3">{enabledTransformButtons}</div>
      </div>
    );
  }

  public renderAvailableMethods() {
    const suggestionElements = InputTransformEditorStoreModule.suggestedMethods.map(suggestedMethod => {
      const clickCallback = () => {
        InputTransformEditorStoreModule.setJqQueryAction(suggestedMethod.suggestedQuery);
        // @ts-ignore
        document.getElementById('jq-input-form').focus();
      };
      return (
        <b-list-group-item
          on={{ click: preventDefaultWrapper(clickCallback) }}
          class="jq-suggested-methods text-align--left pl-3 pb-0 d-flex w-100 justify-content-between"
        >
          <p>{suggestedMethod.suggestedQuery}</p>
          <p style="color: #b1b4c3;">
            <i class="fas fa-arrow-right" /> <i>{suggestedMethod.queryResult}</i>
          </p>
        </b-list-group-item>
      );
    });

    return (
      <div class="mt-2">
        <b-list-group class="text-align--left">{suggestionElements}</b-list-group>
      </div>
    );
  }

  getBlockDescriptorFromValue(cachedBlockInput: BlockCachedInputResult) {
    const originText = cachedBlockInput.origin === 'DEPLOYMENT' ? 'deployment logs' : 'editor';

    // If it's input data it must be the current block
    if (cachedBlockInput.io_type === BlockCachedInputIOTypes.Input) {
      return `Input data for the current block from the ${originText}`;
    }

    if (cachedBlockInput.name) {
      return `Data returned from upstream block '${cachedBlockInput.name}' from the ${originText}`;
    }

    return `Data returned from an upstream block from the ${originText}`;
  }

  public renderCachedBlockInputSelect() {
    const cachedBlockInputDropDownOptions = InputTransformEditorStoreModule.cachedInputTransformRunResults.map(
      cachedBlockInputRunResult => {
        const cachedBlockInputStatusIcon = cachedBlockInputRunResult.succeeded ? '✅' : '⚠️';
        const dropDownText =
          `${cachedBlockInputStatusIcon} | ${cachedBlockInputRunResult.cachedBlockInput.body.substring(
            0,
            25
          )}... | ${this.getBlockDescriptorFromValue(cachedBlockInputRunResult.cachedBlockInput)}, observed at ` +
          moment(cachedBlockInputRunResult.cachedBlockInput.timestamp * 1000).format('MMMM Do YYYY, h:mm:ss a') +
          '.';
        return {
          value: cachedBlockInputRunResult.cachedBlockInput.id,
          text: dropDownText
        };
      }
    );

    const cachedBlockInputsExist = InputTransformEditorStoreModule.cachedBlockInputs.length > 0;

    const cachedBlockInputSelectCallback = async (cachedBlockInputId: string) => {
      await InputTransformEditorStoreModule.setCachedBlockInput(cachedBlockInputId);
      await InputTransformEditorStoreModule.updateSuggestions();
    };

    const cachedBlockInputSelectorProps = {
      options: cachedBlockInputDropDownOptions,
      value: cachedBlockInputsExist ? InputTransformEditorStoreModule.cachedBlockInputs[0].id : ''
    };

    if (!cachedBlockInputsExist) {
      return (
        <div class="text-align--center m-2">
          No example block inputs are stored, deploy and execute this block or an upstream block to generate some.
        </div>
      );
    }

    return (
      <div class="m-2">
        <b-form-select
          on={{ change: cachedBlockInputSelectCallback }}
          props={cachedBlockInputSelectorProps}
          class="width--auto"
        />
      </div>
    );
  }

  public renderTransformWarning() {
    // Get number of cached block inputs that failed the current jq transform
    const jqFailureNumber = InputTransformEditorStoreModule.cachedInputTransformRunResults.filter(
      cachedInputTransformRunResult => !cachedInputTransformRunResult.succeeded
    ).length;

    if (jqFailureNumber === 0) {
      return <div />;
    }

    return (
      <div class="ml-2 mr-2 pt-2 pb-0 text-align--center warning-text-color">
        <i class="fas fa-exclamation-triangle" /> This transform fails when run against {jqFailureNumber}{' '}
        previously-observed Code Block input{jqFailureNumber ? 's' : ''}. Click the drop-down below for the problematic
        input{jqFailureNumber ? 's' : ''}.
      </div>
    );
  }

  public render() {
    const renderEditorWrapper = (text: string | null, editor: any) => (
      <div class="display--flex flex-direction--column flex-grow--1">
        {text && (
          <div class="text-align--left run-lambda-container__text-label">
            <label class="text-light padding--none mt-0 mb-0 ml-2">{text}</label>
          </div>
        )}
        <div class="flex-grow--1 display--flex">{editor}</div>
      </div>
    );

    const sharedEditorProps = {
      collapsible: true,
      wrapText: true
    };

    const inputDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `input-data-editor`,
      // This is very nice for rendering non-programming text
      lang: 'json',
      content: InputTransformEditorStoreModule.inputData,
      readOnly: false,
      // Update suggestions when user edits input data
      onChange: async (newEditorText: string) => {
        await InputTransformEditorStoreModule.updateInputData(newEditorText);
        await InputTransformEditorStoreModule.updateSuggestions();
      }
    };

    const transformedInputDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `input-data-editor`,
      // This is very nice for rendering non-programming text
      lang: 'json',
      content: InputTransformEditorStoreModule.transformedInputData,
      readOnly: true
    };

    const targetInputDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `target-input-data-editor`,
      // This is very nice for rendering non-programming text
      lang: 'json',
      content: InputTransformEditorStoreModule.targetInputData,
      readOnly: false,
      // Update suggestions when user edits input data
      onChange: async (newEditorText: string) => {
        await InputTransformEditorStoreModule.setTargetInputData(newEditorText);
        await InputTransformEditorStoreModule.updateSuggestions();
      }
    };

    const modalOnHandlers = {
      hidden: () => InputTransformEditorStoreModule.setModalVisibilityAction(false)
    };

    const saveTransformOnClick = async () => {
      await InputTransformEditorStoreModule.setModalVisibilityAction(false);
      await InputTransformEditorStoreModule.saveCodeBlockInputTransform();
    };
    const discardTransformOnClick = async () => {
      await InputTransformEditorStoreModule.setModalVisibilityAction(false);
    };

    return (
      <b-modal
        ref={`input-transform-modal`}
        on={modalOnHandlers}
        hide-footer={true}
        no-close-on-esc={true}
        size="xl no-max-width no-modal-body-padding dark-modal"
        title="Input Data Transform Editor"
        visible={InputTransformEditorStoreModule.isFullScreenEditorModalVisible}
      >
        <div class="display--flex code-modal-editor-container overflow--hidden-x">
          <Split
            props={{
              direction: 'horizontal' as Object,
              extraClasses: 'height--100percent flex-grow--1 display--flex' as Object
            }}
          >
            <SplitArea props={{ size: 50 as Object, positionRelative: true as Object }}>
              <Split props={{ direction: 'vertical' as Object }}>
                <SplitArea props={{ size: 50 as Object }}>
                  {renderEditorWrapper(
                    'Input Data (Pre-Transform, When Returned From Upstream Block)',
                    <RefineryCodeEditor props={inputDataEditorProps} />
                  )}
                </SplitArea>
                {this.renderTransformWarning()}
                {this.renderCachedBlockInputSelect()}
                <SplitArea props={{ size: 50 as Object }}>
                  {renderEditorWrapper(
                    'Transformed Input Data (Post-Transform)',
                    <RefineryCodeEditor props={transformedInputDataEditorProps} />
                  )}
                </SplitArea>
              </Split>
            </SplitArea>
            <SplitArea props={{ size: 50 as Object }}>
              <Split props={{ direction: 'vertical' as Object }}>
                <SplitArea props={{ size: 50 as Object }}>
                  <div class="text-align--center mt-2 mb-2 ml-3 mr-3">
                    <h1>JQ Transform Query</h1>
                    <p>
                      This is a transform applied to the Code Block input data{' '}
                      <u>only when the input data is from the return data of another block</u>.
                      <br />
                    </p>
                    <b-input-group size="lg">
                      <b-form-input
                        id="jq-input-form"
                        class="jq-input"
                        placeholder=".object_key.sub_key[0] | .output_key"
                        value={InputTransformEditorStoreModule.jqQuery}
                        on={{ input: InputTransformEditorStoreModule.setJqQueryAction }}
                        state={InputTransformEditorStoreModule.isValidQuery}
                        spellcheck="false"
                        autofocus
                      />
                      <b-form-invalid-feedback state={InputTransformEditorStoreModule.isValidQuery}>
                        This <code>jq</code> transform query failed against the specified input data. See the error in
                        the bottom-left of the transform editor for more information.
                      </b-form-invalid-feedback>
                    </b-input-group>
                    {this.renderAvailableMethods()}
                    {this.renderJQSuggestions()}
                  </div>
                </SplitArea>
                <div class="text-align--center inline p-2">
                  <div class="btn-group w-100">
                    <b-tooltip target="saveTransformButton" triggers="hover">
                      Save this input transform to the Code Block.
                    </b-tooltip>
                    <b-tooltip target="discardTransformButton" triggers="hover">
                      Discard changes to this input transform.
                    </b-tooltip>
                    <b-button
                      on={{ click: saveTransformOnClick }}
                      disabled={!InputTransformEditorStoreModule.isValidQuery}
                      id="saveTransformButton"
                      variant="success"
                      class="w-50"
                    >
                      Save Transform
                    </b-button>
                    <b-button
                      on={{ click: discardTransformOnClick }}
                      id="discardTransformButton"
                      class="w-50"
                      variant="danger"
                    >
                      Discard Transform
                    </b-button>
                  </div>
                </div>
                <SplitArea props={{ size: 50 as Object }}>
                  {renderEditorWrapper(
                    'Target Input Format (Saved Input for Code Block)',
                    <RefineryCodeEditor props={targetInputDataEditorProps} />
                  )}
                </SplitArea>
              </Split>
            </SplitArea>
          </Split>
        </div>
      </b-modal>
    );
  }
}
