import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { RefineryProject } from '@/types/graph';

const project = namespace('project');

@Component
export default class SharedFilesPane extends Vue {
  @project.State openedProject!: RefineryProject | null;

  public render(h: CreateElement): VNode {
    return (
      <b-list-group class="shared-files-pane">
        <b-list-group-item className="display--flex" button>
          <img class="add-block__image" />
          <i class="file-alt" />
          <div class="flex-column align-items-start add-block__content">
            <div class="d-flex w-100 justify-content-between">
              <h4 class="mb-1">utils.py</h4>
            </div>

            <p class="mb-1">Utils.py</p>
          </div>
        </b-list-group-item>
        <button class="mb-1 btn btn-success" type="button">
          Add New Shared File
        </button>
      </b-list-group>
    );
  }
}
