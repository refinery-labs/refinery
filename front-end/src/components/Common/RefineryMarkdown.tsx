import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { MarkdownProps } from '@/types/component-types';
import stripMarkdown from '@/lib/strip-markdown';

@Component
export default class RefineryMarkdown extends Vue implements MarkdownProps {
  @Prop({ required: true }) content!: string;
  @Prop({ default: false }) stripMarkup!: boolean;
  private VueMarkdown: Function | null = null;

  async mounted() {
    // Lazy load this library since it's only used here.
    const VueMarkdown = await import('vue-markdown');
    // @ts-ignore
    this.VueMarkdown = VueMarkdown.default;
  }

  public render(h: CreateElement) {
    if (this.VueMarkdown === null) {
      return 'Content loading...';
    }

    const content = this.stripMarkup ? stripMarkdown(this.content) : this.content;

    return <this.VueMarkdown html={false} emoji={false} source={content} />;
  }
}
