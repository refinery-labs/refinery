import {CreateElement, VNode} from 'vue';
import {Component, Prop, Vue} from 'vue-property-decorator';
import {SupportedLanguage} from '@/types/graph';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import {EditorProps} from '@/types/component-types';
import {RunLambdaResult} from '@/types/api-types';

@Component
export default class RunLambda extends Vue {
  @Prop({ required: true }) private onRunLambda!: () => void;
  @Prop({ required: true }) private onUpdateInputData!: (s: string) => void;
  @Prop({ required: true }) private fullScreenClicked!: () => void;

  @Prop({ required: true }) private lambdaId!: string;
  @Prop({ required: true }) private runResultOutput!: RunLambdaResult | null;
  @Prop({ required: true }) private inputData!: string;
  @Prop({ required: true }) private isCurrentlyRunning!: boolean;
  // Useful because it allows us to use the same component on the side pane and the modal... Leaky but not terrible.
  @Prop({ required: true }) private showFullscreenButton!: boolean;

  public getRunLambdaOutput() {
    // Need to check this because Ace will shit the bed if given a *gasp* null value!
    if (!this.runResultOutput) {
      return '';
    }

    return this.runResultOutput.logs;
  }

  public getModeForIdString() {
    return this.showFullscreenButton ? 'pane' : 'modal';
  }

  public renderFullscreenButton() {
    if (!this.showFullscreenButton) {
      return null;
    }

    // TODO: Potentially add this feature here too
    // const expandOnClick = {click: () => this.setWidePanel(!this.wideMode)};
    const fullscreenOnClick = {
      click: () => this.fullScreenClicked()
    };

    return (
      <b-button on={fullscreenOnClick} class="run-lambda-container__expand-button">
        <span class="fa fa-expand"/>
        {/*<b-button on={expandOnClick} class="edit-block-container__expand-button">*/}
        {/*  <span class="fa fa-angle-double-left"/>*/}
        {/*</b-button>*/}
      </b-button>
    );
  }

  public renderOutputData() {
    const isInSidepane = this.showFullscreenButton;

    if (!this.runResultOutput && isInSidepane) {
      return null;
    }

    const resultDataEditorProps: EditorProps = {
      id: `result-data-${this.lambdaId}-${this.getModeForIdString()}`,
      // This is very nice for rendering non-programming text
      lang: 'text',
      content: this.runResultOutput && this.runResultOutput.returned_data || '',
      wrapText: true,
      readOnly: true
    };

    const resultOutputEditorProps: EditorProps = {
      id: `result-output-${this.lambdaId}-${this.getModeForIdString()}`,
      // This is very nice for rendering non-programming text
      lang: 'text',
      content: this.getRunLambdaOutput(),
      wrapText: true,
      readOnly: true
    };

    const resultDataTab = (
      <b-tab title="first" active>
        <template slot="title">
          <span>Returned Data <em class="fas fa-code" /></span>
        </template>
        <RefineryCodeEditor props={{editorProps: resultDataEditorProps}} />
      </b-tab>
    );

    const outputDataTab = (
      <b-tab title="second">
        <template slot="title">
          <span>Execution Output <em class="fas fa-terminal" /></span>
        </template>
        <RefineryCodeEditor props={{editorProps: resultOutputEditorProps}} />
      </b-tab>
    );

    const colClasses = {
      'run-lambda-container__col text-align--left': true,
      'run-lambda-container__modal': !this.showFullscreenButton
    };

    return (
      <div class={colClasses}>
        <b-tabs nav-class="nav-justified">
          {this.runResultOutput && resultDataTab}
          {this.runResultOutput && outputDataTab}
          <div slot="empty">
            <h4 class="mt-3 mb-3">No output data to display. Click "Execute with Data" to generate output.</h4>
          </div>
        </b-tabs>
      </div>
    );
  }

  public renderEditors() {

    const inputDataEditorProps: EditorProps = {
      id: `input-${this.lambdaId}-${this.getModeForIdString()}`,
      // Using NodeJS for JSON support
      lang: SupportedLanguage.NODEJS_8,
      content: this.inputData,
      onChange: this.onUpdateInputData
    };

    const inputDataLabelClasses = {
      'flex-grow--1 run-lambda-container__input-data': true,
      'run-lambda-container__input-data--top-padding': !this.showFullscreenButton
    };

    const inputDataEditor = (
      <div class="run-lambda-container__col">
        <div class="display--flex text-align--left">
          <label class={inputDataLabelClasses}> Input Data</label>
          {this.renderFullscreenButton()}
        </div>
        <RefineryCodeEditor props={{editorProps: inputDataEditorProps}} />
      </div>
    );

    const outputDataEditor = this.renderOutputData();

    if (this.showFullscreenButton) {
      return [
        inputDataEditor,
        outputDataEditor
      ];
    }

    return (
      <div class="display--flex flex-direction--row">
        {inputDataEditor}
        {outputDataEditor}
      </div>
    );
  }

  public render(h: CreateElement): VNode {

    const containerClasses = {
      'run-lambda-container display--flex flex-direction--column': true,
      'whirl standard': !this.showFullscreenButton && this.isCurrentlyRunning
    };

    return (
      <div class={containerClasses}>
        {this.renderEditors()}
        <div class="run-lambda-container__buttons">
          <b-button-group class="width--100percent">
            {/*<b-button variant="info" disabled on={{click: () => this.onRunLambda()}}>*/}
            {/*  View Last Execution*/}
            {/*</b-button>*/}
            <b-button variant="primary" on={{click: () => this.onRunLambda()}}>
              Execute With Data
            </b-button>
          </b-button-group>
        </div>
      </div>
    );
  }
}
