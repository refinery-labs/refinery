import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { languageToAceLangMap } from '@/types/project-editor-types';
import AceEditor from '@/components/Common/AceEditor.vue';
import { EditorProps } from '@/types/component-types';
import uuid from 'uuid/v4';
import { SupportedLanguage } from '@/types/graph';

@Component
export default class RefineryCodeEditor extends Vue implements EditorProps {
  @Prop({ required: true }) name!: string;
  @Prop({ required: true }) lang!: SupportedLanguage | 'text';
  @Prop({ required: true }) content!: string;
  @Prop() theme?: string;
  @Prop() onChange?: (s: string) => void;
  @Prop() onChangeContext?: (c: { value: string; this: any }) => void;

  // Ace Props
  @Prop() readOnly?: boolean;
  @Prop() wrapText?: boolean;

  @Prop() extraClasses?: string;

  // Internal value used to prevent editors from colliding IDs. Colliding causes breaking + performance issues.
  randId: string = uuid();

  public getChangeHandlers() {
    const handlers: { [key: string]: Function } = {};

    if (this.onChange) {
      handlers['change-content'] = this.onChange;
    }

    if (this.onChangeContext) {
      handlers['change-content-context'] = this.onChangeContext;
    }

    return handlers;
  }

  public renderEditor() {
    // If we don't have valid state, tell the user.
    if (this.content === null) {
      return <h3>Could not display code editor.</h3>;
    }

    // This is super gross but gonna leave it for now. Eventually (if we add a 2nd) we will need to do an Enum lookup
    // Like "is this in the enum" in order for the mapping to work. Typescript will yell so not afraid :)
    const editorLanguage = this.lang === 'text' ? 'text' : languageToAceLangMap[this.lang];

    const aceProps = {
      editorId: `${this.name}-${this.randId}`,
      theme: this.theme || this.readOnly ? 'monokai-disabled' : 'monokai',
      lang: editorLanguage,
      disabled: this.readOnly,
      content: this.content,
      wrapText: this.wrapText
    };

    return (
      // @ts-ignore
      <AceEditor props={aceProps} on={this.getChangeHandlers()} />
    );
  }

  public render(h: CreateElement): VNode {
    const containerClasses = {
      'refinery-code-editor-container width--100percent flex-grow--1 display--flex': true,
      'refinery-code-editor-container--read-only': this.readOnly,
      [this.extraClasses || '']: Boolean(this.extraClasses)
    };

    return <div class={containerClasses}>{this.renderEditor()}</div>;
  }
}
