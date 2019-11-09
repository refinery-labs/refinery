import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { SupportedLanguage } from '@/types/graph';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps, LoadingContainerProps } from '@/types/component-types';
import { RunLambdaResult } from '@/types/api-types';
import Loading from '@/components/Common/Loading.vue';
import Split from '@/components/Common/Split.vue';
import SplitArea from '@/components/Common/SplitArea.vue';
import InputTransformFullScreenModal from '@/components/ProjectEditor/input-transform-components/InputTransformFullScreenModal';
import { InputTransformEditorStoreModule } from '@/store';

export enum RunLambdaDisplayLocation {
  editor = 'editor',
  deployment = 'deployment'
}

export enum RunLambdaDisplayMode {
  sidepane = 'sidepane',
  fullscreen = 'fullscreen'
}

export interface RunLambdaProps {
  onRunLambda: () => void;
  onUpdateInputData: (s: string) => void;
  onUpdateBackpackData: (s: string) => void;
  onSaveInputData?: () => void;
  fullScreenClicked?: () => void;
  lambdaIdOrArn: string;

  runResultOutput: RunLambdaResult | null;
  runResultOutputId: string | null;
  inputData: string;
  backpackData: string;
  isCurrentlyRunning: boolean;
  hasExistingTransform: boolean;

  displayLocation: RunLambdaDisplayLocation;
  displayMode: RunLambdaDisplayMode;

  loadingText: string;
}

@Component({
  components: {
    Loading
  }
})
export default class RunLambda extends Vue implements RunLambdaProps {
  @Prop({ required: true }) onRunLambda!: () => void;
  @Prop({ required: true }) onUpdateInputData!: (s: string) => void;
  @Prop({ required: true }) onUpdateBackpackData!: (s: string) => void;
  @Prop() onSaveInputData?: () => void;
  @Prop() fullScreenClicked?: () => void;

  /**
   * Allows us to associated the selected block with prior results.
   */
  @Prop({ required: true }) lambdaIdOrArn!: string;

  @Prop() runResultOutputId!: string | null;
  @Prop({ required: true }) runResultOutput!: RunLambdaResult | null;
  @Prop({ required: true }) inputData!: string;
  @Prop({ required: true }) backpackData!: string;
  @Prop({ required: true }) isCurrentlyRunning!: boolean;
  @Prop({ required: true }) hasExistingTransform!: boolean;

  @Prop({ required: true }) displayLocation!: RunLambdaDisplayLocation;
  @Prop({ required: true }) displayMode!: RunLambdaDisplayMode;

  @Prop({ required: true }) loadingText!: string;

  public checkIfValidRunLambdaOutput() {
    if (!this.runResultOutput) {
      return false;
    }

    // If we have a valid Lambda ARN and the output matches it, we have valid output.
    if (this.lambdaIdOrArn && this.runResultOutput.arn === this.lambdaIdOrArn) {
      return true;
    }

    // If we have valid output for a Lambda based on it's ID.
    if (this.lambdaIdOrArn) {
      return true;
    }

    // Otherwise, false. This is not valid output.
    return false;
  }

  public getRunLambdaReturnFieldValue(runResultOutput: RunLambdaResult | null) {
    // Check if the Lambda is running, we'll show a different return value if it is
    // to indicate to the user that the Code Block is currently still executing.
    if (this.isCurrentlyRunning) {
      return 'The Code Block has not finished executing yet, please wait...';
    }

    if (runResultOutput && runResultOutput.returned_data && typeof runResultOutput.returned_data === 'string') {
      return runResultOutput.returned_data;
    }

    return 'Click Execute button for run output.';
  }

  public getRunLambdaOutput(hasValidOutput: boolean) {
    // Check if the Lambda is running, we'll show a different return value if it is
    // to indicate to the user that the Code Block is currently still executing.
    if (this.isCurrentlyRunning && !this.runResultOutput) {
      return 'No output from Code Block received yet, please wait...';
    }

    // Need to check this because Ace will shit the bed if given a *gasp* null value!
    if (!hasValidOutput || !this.runResultOutput) {
      return 'No return data to display.';
    }

    return this.runResultOutput.logs;
  }

  /**
   * This is only helpful for inspecting the elements on the page. Not needed for any other purpose.
   */
  getNameSuffix() {
    return `${this.displayLocation}-${this.displayMode}`;
  }

  /**
   * TODO: Determine if we still want this feature on the Code Runner pane
   */
  public renderFullscreenButton() {
    if (
      !this.fullScreenClicked ||
      this.displayMode === RunLambdaDisplayMode.fullscreen ||
      this.displayLocation === RunLambdaDisplayLocation.deployment
    ) {
      return null;
    }

    const fullScreenClicked = this.fullScreenClicked;

    // TODO: Potentially add this feature here too
    const fullscreenOnClick = {
      click: () => fullScreenClicked()
    };

    return (
      <b-button on={fullscreenOnClick} class="run-lambda-container__expand-button">
        <span class="fa fa-expand" />
        {/*<b-button on={expandOnClick} class="show-block-container__expand-button">*/}
        {/*  <span class="fa fa-angle-double-left"/>*/}
        {/*</b-button>*/}
      </b-button>
    );
  }

  /*
  Disables the Execute With Data button if the Lambda is running
  */
  getExecuteWithDataButton() {
    if (this.isCurrentlyRunning) {
      return (
        <b-button variant="primary" disabled={true}>
          <b-spinner small /> Code Block is executing, please wait...
        </b-button>
      );
    }

    return (
      <b-button variant="primary" on={{ click: () => this.onRunLambda() }}>
        Execute With Data
      </b-button>
    );
  }

  showInputFullScreenModal() {
    InputTransformEditorStoreModule.setModalVisibilityAction(true);
  }

  public renderEditors() {
    const hasValidOutput = this.checkIfValidRunLambdaOutput();

    const sharedEditorProps = {
      collapsible: true
    };

    const inputDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `input-data-${this.getNameSuffix()}`,
      lang: 'json',
      content: this.inputData,
      onChange: this.onUpdateInputData
    };

    const inputDataEditor = <RefineryCodeEditor props={inputDataEditorProps} />;

    const backpackDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `backpack-data-${this.getNameSuffix()}`,
      lang: 'json',
      content: this.backpackData,
      onChange: this.onUpdateBackpackData
    };

    const backpackDataEditor = <RefineryCodeEditor props={backpackDataEditorProps} />;

    const hasResultData = hasValidOutput && this.runResultOutput && this.runResultOutput.returned_data;

    const resultDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `result-data-${this.getNameSuffix()}`,
      // This is very nice for rendering non-programming text
      lang: hasResultData ? 'json' : 'text',
      content: this.getRunLambdaReturnFieldValue(this.runResultOutput),
      wrapText: true,
      readOnly: true
    };

    const resultOutputEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `result-output-${this.getNameSuffix()}`,
      // This is very nice for rendering non-programming text
      lang: 'text',
      content: this.getRunLambdaOutput(hasValidOutput),
      wrapText: true,
      readOnly: true,
      tailOutput: true
    };

    const saveInputDataButton = (
      <b-button variant="outline-info" on={{ click: () => this.onSaveInputData && this.onSaveInputData() }}>
        Save Input Data
      </b-button>
    );

    const buttons = (
      <div class="m-2">
        <b-button-group class="width--100percent">
          {this.displayLocation === RunLambdaDisplayLocation.editor && this.onSaveInputData && saveInputDataButton}
          {this.getExecuteWithDataButton()}
        </b-button-group>
      </div>
    );

    const renderEditorWrapper = (text: string | null, editor: any) => (
      <div class="display--flex flex-direction--column flex-grow--1">
        {text && (
          <div class="text-align--left run-lambda-container__text-label">
            <label class="text-light padding--none mt-0 mb-0 ml-2">{text}:</label>
          </div>
        )}
        <div class="flex-grow--1 display--flex">{editor}</div>
      </div>
    );

    return (
      <div class="display--flex flex-direction--column flex-grow--1">
        <InputTransformFullScreenModal />
        <div class="display--flex flex-grow--1 height--100percent">
          <Split props={{ direction: 'vertical' as Object }}>
            <SplitArea props={{ size: 38 as Object }}>
              <b-tabs nav-class="nav-justified" content-class="padding--none position--relative flex-grow--1">
                <b-tab title="Input Data" active={true} no-body={true} title-link-class="dark-nav-tab">
                  <div class="display--flex flex-grow--1 ace-hack margin-left--negative-micro margin-right--negative-micro">
                    {renderEditorWrapper(null, inputDataEditor)}
                  </div>
                </b-tab>
                <b-tab title="Backpack Data" no-body={true} title-link-class="dark-nav-tab">
                  <div class="display--flex flex-grow--1 ace-hack margin-left--negative-micro margin-right--negative-micro">
                    {renderEditorWrapper(null, backpackDataEditor)}
                  </div>
                </b-tab>
              </b-tabs>
            </SplitArea>
            <div>{this.renderInputTransformButton()}</div>
            <SplitArea props={{ size: 30 as Object }}>
              {renderEditorWrapper('Return Data', <RefineryCodeEditor props={resultDataEditorProps} />)}
            </SplitArea>
            <SplitArea props={{ size: 30 as Object }}>
              {renderEditorWrapper('Execution Output', <RefineryCodeEditor props={resultOutputEditorProps} />)}
            </SplitArea>
          </Split>
        </div>
        {buttons}
      </div>
    );
  }

  public renderInputTransformButton() {
    if (this.displayLocation === RunLambdaDisplayLocation.editor) {
      return (
        <button class="btn btn-block btn-primary" on={{ click: this.showInputFullScreenModal }}>
          <i class="fas fa-random" /> {this.hasExistingTransform ? 'Edit' : 'Add'} Block Input Transform
        </button>
      );
    }

    return <div />;
  }

  public render(h: CreateElement): VNode {
    console.log('has existing transforms:');
    console.log(this.hasExistingTransform);
    const classes = {
      'run-lambda-container display--flex flex-direction--column width--100percent': true,
      [`run-lambda-container__${this.displayMode}`]: true
    };

    return <div class={classes}>{this.renderEditors()}</div>;
  }
}
