import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import {languageToAceLangMap} from '@/types/project-editor-types';
import AceEditor from '@/components/Common/AceEditor.vue';
import {EditorProps} from '@/types/component-types';

@Component
export default class RefineryCodeEditor extends Vue {
  @Prop({ required: true }) private editorProps!: EditorProps | null;

  public renderEditor() {
    const props = this.editorProps;

    // If we don't have valid state, tell the user.
    if (!props) {
      return (
        <h3>Could not display code editor.</h3>
      );
    }

    // The "rest" is everything except id and lang. It's "the rest" of the object.
    const {id, lang, ...rest} = props;

    const editorProps = {
      'editor-id': `editor-run-lambda-input-${id}`,
      theme: 'monokai',
      lang: languageToAceLangMap[lang],
      ...rest
    };

    return (
      // @ts-ignore
      <AceEditor
        editor-id={editorProps['editor-id']}
        lang={editorProps.lang}
        theme={editorProps.theme}
        content={editorProps.content}
      />
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="refinery-code-editor-container width--100percent height--100percent display--flex">
        {this.renderEditor()}
      </div>
    );
  }
}
