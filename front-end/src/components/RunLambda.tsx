import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { SupportedLanguage } from '@/types/graph';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { EditorProps } from '@/types/component-types';
import { RunLambdaResult } from '@/types/api-types';
import Loading from '@/components/Common/Loading.vue';
import { namespace } from 'vuex-class';

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

  public getRunLambdaOutput() {
    // Need to check this because Ace will shit the bed if given a *gasp* null value!
    if (!this.runResultOutput) {
      return '';
    }

    return this.runResultOutput.logs;
  }

  /**
   * This is only helpful for inspecting the elements on the page. Not needed for any other purpose.
   */
  getNameSuffix() {
    return `${this.displayLocation}-${this.displayMode}`;
  }

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
        {/*<b-button on={expandOnClick} class="edit-block-container__expand-button">*/}
        {/*  <span class="fa fa-angle-double-left"/>*/}
        {/*</b-button>*/}
      </b-button>
    );
  }

  public renderOutputData() {
    const noDataText = ['No output data to display.', <br />, 'Click "Execute with Data" to generate output.'];

    const isInSidepane = this.displayMode === RunLambdaDisplayMode.sidepane;
    const hasValidOutput = this.checkIfValidRunLambdaOutput();

    if (!hasValidOutput && isInSidepane) {
      return <label class="mt-3 mb-3">{noDataText}</label>;
    }

    const resultDataEditorProps: EditorProps = {
      name: `result-data-${this.getNameSuffix()}`,
      // This is very nice for rendering non-programming text
      lang: 'text',
      content: (this.runResultOutput && this.runResultOutput.returned_data) || '',
      wrapText: true,
      readOnly: true
    };

    const resultOutputEditorProps: EditorProps = {
      name: `result-output-${this.getNameSuffix()}`,
      // This is very nice for rendering non-programming text
      lang: 'text',
      content: this.getRunLambdaOutput(),
      wrapText: true,
      readOnly: true
    };

    const resultDataTab = (
      <b-tab title="first" active>
        <template slot="title">
          <span>
            Returned Data <em class="fas fa-code" />
          </span>
        </template>
        <RefineryCodeEditor props={resultDataEditorProps} />
      </b-tab>
    );

    const outputDataTab = (
      <b-tab title="second">
        <template slot="title">
          <span>
            Execution Output <em class="fas fa-terminal" />
          </span>
        </template>
        <RefineryCodeEditor props={resultOutputEditorProps} />
      </b-tab>
    );

    const colClasses = {
      'run-lambda-container__col text-align--left': true,
      'run-lambda-container__modal': !isInSidepane
    };

    return (
      <div class={colClasses}>
        <b-tabs nav-class="nav-justified">
          {hasValidOutput && resultDataTab}
          {hasValidOutput && outputDataTab}
          <div slot="empty">
            <h4 class="mt-3 mb-3">{noDataText}</h4>
          </div>
        </b-tabs>
      </div>
    );
  }

  public renderEditors() {
    const inputDataEditorProps: EditorProps = {
      name: `input-${this.getNameSuffix()}`,
      // Using NodeJS for JSON support
      lang: SupportedLanguage.NODEJS_8,
      content: this.inputData,
      onChange: this.onUpdateInputData
    };

    const inputDataLabelClasses = {
      'flex-grow--1 run-lambda-container__input-data': true,
      'run-lambda-container__input-data--top-padding': this.displayMode === RunLambdaDisplayMode.fullscreen
    };

    const inputDataEditor = (
      <div class="run-lambda-container__col">
        <div class="display--flex text-align--left">
          <label class={inputDataLabelClasses}> Input Data</label>
          {this.renderFullscreenButton()}
        </div>
        <RefineryCodeEditor props={inputDataEditorProps} />
      </div>
    );

    const outputDataEditor = this.renderOutputData();

    // Column layout
    if (this.displayMode === RunLambdaDisplayMode.sidepane) {
      return [inputDataEditor, outputDataEditor];
    }

    // Row layout
    return (
      <div class="display--flex flex-direction--row flex-grow--1">
        {inputDataEditor}
        {outputDataEditor}
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const loadingProps = {
      show: this.isCurrentlyRunning,
      label: this.loadingText
    };

    return (
      <div>
        {/*
              // @ts-ignore */}
        <Loading props={loadingProps}>
          <div class="run-lambda-container display--flex flex-direction--column">
            {this.renderEditors()}
            <div class="run-lambda-container__buttons">
              <b-button-group class="width--100percent">
                {/*<b-button variant="info" disabled on={{click: () => this.onRunLambda()}}>*/}
                {/*  View Last Execution*/}
                {/*</b-button>*/}
                <b-button variant="primary" on={{ click: () => this.onRunLambda() }}>
                  Execute With Data
                </b-button>
              </b-button-group>
            </div>
          </div>
        </Loading>
      </div>
    );
  }
}
