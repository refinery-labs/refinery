import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { availableBlocks, AddGraphElementConfig } from '@/constants/project-editor-constants';
import { blockTypeToImageLookup } from '@/constants/project-editor-img-constants';

const project = namespace('project');

@Component
export default class AddBlockPane extends Vue {
  @project.Action addBlock!: (key: string) => {};

  public renderBlockSelect(key: string, block: AddGraphElementConfig | null) {
    if (!block) {
      return null;
    }

    return (
      <b-list-group-item on={{ click: () => this.addBlock(key) }} class="display--flex" button>
        <img class="add-block__image" src={block.path} alt={block.name} />
        <div class="flex-column align-items-start add-block__content">
          <div class="d-flex w-100 justify-content-between">
            <h4 class="mb-1">{block.name}</h4>
          </div>

          <p class="mb-1">{block.description}</p>
        </div>
      </b-list-group-item>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <b-list-group class="add-block-container">
        {availableBlocks.map(key => this.renderBlockSelect(key, blockTypeToImageLookup[key]))}
      </b-list-group>
    );
  }
}
