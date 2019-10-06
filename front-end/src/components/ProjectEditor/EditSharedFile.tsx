import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';

const project = namespace('project');

@Component
export default class EditSharedFilePane extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="text-align--left mb-2 ml-2 mr-2 mt-0 display--flex flex-direction--column shared-files-pane">
        Nice
      </div>
    );
  }
}
