import {CreateElement, VNode} from 'vue';
import {Component, Prop, Vue} from 'vue-property-decorator';
import {SupportedLanguage} from '@/types/graph';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import {EditorProps} from '@/types/component-types';
import {RunLambdaResult} from '@/types/api-types';
import {PANE_POSITION} from '@/types/project-editor-types';

@Component
export default class RunLambda extends Vue {
  @Prop({ required: true }) private onRunLambda!: () => void;
  @Prop({ required: true }) private onUpdateInputData!: (s: string) => void;

  @Prop({ required: true }) private lambdaId!: string;
  @Prop({ required: true }) private runResultOutput!: RunLambdaResult | null;
  @Prop({ required: true }) private inputData!: string;
  @Prop({ required: true }) private isCurrentlyRunning!: boolean;

  public getRunLambdaOutput() {
    // Need to check this because Ace will shit the bed if given a *gasp* null value!
    if (!this.runResultOutput) {
      return '';
    }

    return this.runResultOutput.logs;
  }

  public renderOutputData() {
    if (!this.runResultOutput) {
      return null;
    }

    const resultOutputEditorProps: EditorProps = {
      id: `result-${this.lambdaId}`,
      // Using NodeJS for JSON support
      lang: 'text',
      content: this.getRunLambdaOutput()
    };

    return (
      <div class="run-lambda-container__col">
        <h4 class="text-muted">Output:</h4>
        <RefineryCodeEditor props={{editorProps: resultOutputEditorProps}} />
      </div>
    );
  }

  public render(h: CreateElement): VNode {

    const inputDataEditorProps: EditorProps = {
      id: `input-${this.lambdaId}`,
      // Using NodeJS for JSON support
      lang: SupportedLanguage.NODEJS_8,
      content: this.inputData,
    };

    return (
      <div class="run-lambda-container display--flex">
        <div class="run-lambda-container__col">
          <h4 class="text-muted">Input Data:</h4>
          <RefineryCodeEditor props={{editorProps: inputDataEditorProps}} />
        </div>
        {this.renderOutputData()}
        <div class="run-lambda-container__buttons">
          <b-button-group className="col-12">
            {/*This is hacky to make this close itself but meh we can fix it later*/}
            <b-button variant="secondary" on={{click: () => this.onRunLambda()}}>
              Execute With Data
            </b-button>
          </b-button-group>
        </div>
      </div>
    );
  }
}
