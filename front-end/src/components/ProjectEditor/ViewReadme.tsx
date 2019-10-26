import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { MarkdownProps } from '@/types/component-types';
import { RefineryProject } from '@/types/graph';
import RefineryMarkdown from '@/components/Common/RefineryMarkdown';

const project = namespace('project');

@Component
export default class ViewReadmePane extends Vue {
  @project.State openedProject!: RefineryProject | null;

  public render(h: CreateElement): VNode {
    if (!this.openedProject) {
      return <div>No project is opened!</div>;
    }

    const markdownProps: MarkdownProps = {
      content: this.openedProject.readme
    };

    return (
      <div class="mr-3 ml-3 mb-3 mt-3 readme-demo-view text-align--left force-visible-scrollbar">
        <RefineryMarkdown props={markdownProps} />
      </div>
    );
  }
}
