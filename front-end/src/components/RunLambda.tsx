import {CreateElement, VNode} from 'vue';
import {Component, Prop, Vue} from 'vue-property-decorator';
import {SupportedLanguage} from '@/types/graph';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import {EditorProps} from '@/types/component-types';

@Component
export default class RunLambda extends Vue {
  @Prop({ required: true }) private onRunLambda!: () => void;
  @Prop({ required: true }) private onUpdateInputData!: (s: string) => void;

  @Prop({ required: true }) private lambdaId!: string;
  @Prop({ required: true }) private runResultOuput!: string;
  @Prop({ required: true }) private inputData!: string;
  @Prop({ required: true }) private isCurrentlyRunning!: boolean;

  public render(h: CreateElement): VNode {

    const inputDataEditorProps: EditorProps = {
      id: `input-${this.lambdaId}`,
      // Using NodeJS for JSON support
      lang: SupportedLanguage.NODEJS_8,
      content: this.inputData,
    };

    const resultOutputEditorProps: EditorProps = {
      id: `result-${this.lambdaId}`,
      // Using NodeJS for JSON support
      lang: SupportedLanguage.NODEJS_8,
      content: this.runResultOuput
    };

    return (
      <div class="run-lambda-container display--flex">
        <div class="col-md-6 run-lambda-container__col">
          <RefineryCodeEditor props={{editorProps: inputDataEditorProps}} />
        </div>
        <div class="col-md-6 run-lambda-container__col">
          <RefineryCodeEditor props={{editorProps: resultOutputEditorProps}} />
        </div>
      </div>
    );
  }
}
