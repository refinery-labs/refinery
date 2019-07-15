import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { MarkdownProps } from '@/types/component-types';
import stripMarkdown from '@/lib/strip-markdown';
import VueMarkdown from 'vue-markdown';

@Component({
  components: {
    'vue-markdown': VueMarkdown
  }
})
export default class RefineryMarkdown extends Vue implements MarkdownProps {
  @Prop({ required: true }) content!: string;
  @Prop({ default: false }) stripMarkup!: boolean;

  public render(h: CreateElement): VNode {
    const content = this.stripMarkup ? stripMarkdown(this.content) : this.content;

    return <vue-markdown html={false} emoji={false} source={content} />;
  }
}
