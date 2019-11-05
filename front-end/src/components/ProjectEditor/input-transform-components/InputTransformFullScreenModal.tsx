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

const runLambda = namespace('runLambda');
const editBlock = namespace('project/editBlockPane');

@Component
export default class InputTransformFullScreenModal extends Vue {
  @runLambda.Getter getDevLambdaInputData!: (id: string) => string;
  @editBlock.State selectedNode!: WorkflowState | null;

  public renderJQSuggestions() {
    return [];
    /*
    return (
      <b-list-group class="mt-2">
        <b-list-group-item class="text-align--left">
          <div class="d-flex w-100 justify-content-between">
            <h5 class="mb-1">
              <b>Map Object Keys to Different Key Names</b>
            </h5>
          </div>

          <p class="mb-1">
            Map the keys of this object/hash to different key names. This is useful when you want to map a return
            parameter from one Code Block input the input value of another.
          </p>

          <p class="mb-1">
            Example Input:{' '}
            <code>
              {'{'}"url": "https://www.example.com"{'}'}
            </code>
            <br />
            JQ Query:{' '}
            <code>
              {'{'}"input_url": .url{'}'}
            </code>
            <br />
            Result:{' '}
            <code>
              {'{'}"input_url": "https://www.example.com"{'}'}
            </code>
          </p>
        </b-list-group-item>
      </b-list-group>
    );
     */
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
    const cachedBlockInputDropDownOptions = InputTransformEditorStoreModule.cachedBlockInputs.map(cachedBlockInput => {
      const dropDownText =
        `${cachedBlockInput.body.substring(0, 25)}... | ${this.getBlockDescriptorFromValue(
          cachedBlockInput
        )}, observed at ` +
        moment(cachedBlockInput.timestamp * 1000).format('MMMM Do YYYY, h:mm:ss a') +
        '.';
      return {
        value: cachedBlockInput.id,
        text: dropDownText
      };
    });

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
          className="width--auto"
        />
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
      collapsible: true
    };

    const inputDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `input-data-editor`,
      // This is very nice for rendering non-programming text
      lang: 'json',
      content: InputTransformEditorStoreModule.inputData,
      wrapText: true,
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
      wrapText: true,
      readOnly: false
    };

    const selectedNode = this.selectedNode as LambdaWorkflowState;
    console.log(selectedNode);
    const targetInputDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `target-input-data-editor`,
      // This is very nice for rendering non-programming text
      lang: 'json',
      content: this.getDevLambdaInputData(selectedNode.id),
      wrapText: true,
      readOnly: false
    };

    const modalOnHandlers = {
      hidden: () => InputTransformEditorStoreModule.setModalVisibilityAction(false)
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
                    'Input Data (Before Transformation)',
                    <RefineryCodeEditor props={inputDataEditorProps} />
                  )}
                </SplitArea>
                {this.renderCachedBlockInputSelect()}
                <SplitArea props={{ size: 50 as Object }}>
                  {renderEditorWrapper(
                    'Transformed Input Data (After Transformation)',
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
                    <b-input-group size="lg">
                      <b-form-input
                        id="jq-input-form"
                        class="jq-input"
                        placeholder=".object_key.sub_key[0] | .output_key"
                        value={InputTransformEditorStoreModule.jqQuery}
                        on={{ input: InputTransformEditorStoreModule.setJqQueryAction }}
                        spellcheck="false"
                        autofocus
                      />
                    </b-input-group>
                    {this.renderAvailableMethods()}
                    {this.renderJQSuggestions()}
                  </div>
                </SplitArea>
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
