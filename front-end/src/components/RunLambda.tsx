import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { SupportedLanguage } from '@/types/graph';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps, LoadingContainerProps } from '@/types/component-types';
import { RunLambdaResult } from '@/types/api-types';
import Loading from '@/components/Common/Loading.vue';
import Split from '@/components/Common/Split.vue';
import SplitArea from '@/components/Common/SplitArea.vue';

export enum RunLambdaDisplayLocation {
  editor = 'editor',
  deployment = 'deployment'
}

export enum RunLambdaDisplayMode {
  sidepane = 'sidepane',
  fullscreen = 'fullscreen'
}

@Component({
  components: {
    Loading
  }
})
export default class RunLambda extends Vue {
  @Prop({ required: true }) private onRunLambda!: () => void;
  @Prop({ required: true }) private onUpdateInputData!: (s: string) => void;
  @Prop() private fullScreenClicked!: () => void;

  /**
   * Allows us to associated the selected block with prior results.
   */
  @Prop({ required: true }) private lambdaIdOrArn!: string;

  @Prop({ required: true }) private runResultOutput!: RunLambdaResult | null;
  @Prop() private runResultOutputId!: string | null;
  @Prop({ required: true }) private inputData!: string;
  @Prop({ required: true }) private isCurrentlyRunning!: boolean;

  @Prop({ required: true }) private displayLocation!: RunLambdaDisplayLocation;
  @Prop({ required: true }) private displayMode!: RunLambdaDisplayMode;

  @Prop({ required: true }) private loadingText!: string;

  public checkIfValidRunLambdaOutput() {
    if (!this.runResultOutput) {
      return false;
    }

    // If we have a valid Lambda ARN and the output matches it, we have valid output.
    if (this.lambdaIdOrArn && this.runResultOutput.arn === this.lambdaIdOrArn) {
      return true;
    }

    // If we have valid output for a Lambda based on it's ID.
    if (this.lambdaIdOrArn && this.runResultOutputId === this.lambdaIdOrArn) {
      return true;
    }

    // Otherwise, false. This is not valid output.
    return false;
  }

  public getRunLambdaOutput(hasValidOutput: boolean) {
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
      this.displayMode === RunLambdaDisplayMode.fullscreen ||
      this.displayLocation === RunLambdaDisplayLocation.deployment
    ) {
      return null;
    }

    // TODO: Potentially add this feature here too
    // const expandOnClick = {click: () => this.setWidePanel(!this.wideMode)};
    const fullscreenOnClick = {
      click: () => this.fullScreenClicked()
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

  public renderEditors() {
    const hasValidOutput = this.checkIfValidRunLambdaOutput();

    const sharedEditorProps = {
      collapsible: true,
      extraClasses: 'ace-hack'
    };

    const inputDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `input-${this.getNameSuffix()}`,
      // Using NodeJS for JSON support
      lang: SupportedLanguage.NODEJS_8,
      content: this.inputData,
      onChange: this.onUpdateInputData,
    };

    const inputDataEditor = (
      <div>
        <RefineryCodeEditor props={inputDataEditorProps} />
      </div>
    );

    const resultDataEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `result-data-${this.getNameSuffix()}`,
      // This is very nice for rendering non-programming text
      lang: 'json',
      content: (hasValidOutput && this.runResultOutput && this.runResultOutput.returned_data) || 'Click Execute button for run output.',
      wrapText: true,
      readOnly: true,
    };

    const resultOutputEditorProps: EditorProps = {
      ...sharedEditorProps,
      name: `result-output-${this.getNameSuffix()}`,
      // This is very nice for rendering non-programming text
      lang: 'text',
      content: this.getRunLambdaOutput(hasValidOutput),
      wrapText: true,
      readOnly: true,
    };

    const buttons = (
      <div class="m-2">
        <b-button-group class="width--100percent">
          {/*<b-button variant="info" disabled on={{click: () => this.onRunLambda()}}>*/}
          {/*  View Last Execution*/}
          {/*</b-button>*/}
          <b-button variant="primary" on={{ click: () => this.onRunLambda() }}>
            Execute With Data
          </b-button>
        </b-button-group>
      </div>
    );

    const renderEditorWrapper = (text: string, editor: any) => (
      <div class="display--flex flex-direction--column height--100percent">

        <div class="text-align--left run-lambda-container__text-label">
          <label class="text-light padding--none mt-0 mb-0 ml-2">
            {text}:
          </label>
        </div>
        <div class="flex-grow--1">
          <div class="height--100percent position--relative">

            {editor}
          </div>
        </div>
      </div>
    );

    const editors = (
      <div class="display--flex flex-direction--column height--100percent">
        <div class="display--flex flex-grow--1">
          <Split props={{direction: 'vertical' as Object, extraClasses: 'flex-grow--1' as Object}}>
            <SplitArea props={{size: 34 as Object}}>
              {renderEditorWrapper('Block Input Data', inputDataEditor)}
            </SplitArea>
            <SplitArea props={{size: 33 as Object}}>
              {renderEditorWrapper('Return Data', <RefineryCodeEditor props={resultDataEditorProps} />)}
            </SplitArea>
            <SplitArea props={{size: 33 as Object}}>
              {renderEditorWrapper('Execution Output', <RefineryCodeEditor props={resultOutputEditorProps} />)}
            </SplitArea>
          </Split>
        </div>
        {buttons}
      </div>
    );

    // Column layout
    if (this.displayMode === RunLambdaDisplayMode.sidepane) {
      return (
        <div class="display--flex flex-direction--column flex-grow--1 width--100percent"
             style={{'height': '500px', 'min-width': '354px'}}>
          {editors}
        </div>
      );
    }

    // Row layout
    return editors;
  }

  public render(h: CreateElement): VNode {
    const loadingProps: LoadingContainerProps = {
      show: this.isCurrentlyRunning,
      label: this.loadingText,
      classes: 'height--100percent width--100percent'
    };

    return (
      <Loading props={loadingProps}>
        <div class="run-lambda-container display--flex flex-direction--column height--100percent">
          {this.renderEditors()}
        </div>
      </Loading>
    );
  }
}
