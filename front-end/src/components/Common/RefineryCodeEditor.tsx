import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { languageToAceLangMap } from '@/types/project-editor-types';
import AceEditor from '@/components/Common/AceEditor.vue';
import { EditorProps } from '@/types/component-types';

@Component
export default class RefineryCodeEditor extends Vue {
  @Prop({ required: true }) private editorProps!: EditorProps | null;

  public getChangeHandlers(props: EditorProps) {
    const handlers: { [key: string]: Function } = {};

    if (props.onChange) {
      handlers['change-content'] = props.onChange;
    }

    if (props.onChangeContext) {
      handlers['change-content-context'] = props.onChangeContext;
    }

    return handlers;
  }

  public renderEditor() {
    const props = this.editorProps;

    // If we don't have valid state, tell the user.
    if (!props) {
      return <h3>Could not display code editor.</h3>;
    }

    // The "rest" is everything except id and lang. It's "the rest" of the object.
    const { id, lang, readOnly, ...rest } = props;

    // This is super gross but gonna leave it for now. Eventually (if we add a 2nd) we will need to do an Enum lookup
    // Like "is this in the enum" in order for the mapping to work. Typescript will yell so not afraid :)
    const editorLanguage = lang === 'text' ? 'text' : languageToAceLangMap[lang];

    const aceProps = {
      editorId: `editor-run-lambda-input-${id}`,
      theme: 'monokai',
      lang: editorLanguage,
      disabled: readOnly,
      ...rest
    };

    return (
      // @ts-ignore
      <AceEditor props={aceProps} on={this.getChangeHandlers(props)} />
    );
  }

  public render(h: CreateElement): VNode {
    return <div class="refinery-code-editor-container width--100percent">{this.renderEditor()}</div>;
  }
}
