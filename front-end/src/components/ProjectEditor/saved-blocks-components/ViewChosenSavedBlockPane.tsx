import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import moment from 'moment';
import { blockTypeToImageLookup } from '@/constants/project-editor-constants';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { Prop } from 'vue-property-decorator';
import VueMarkdown from 'vue-markdown';
import { ChosenBlock } from '@/types/add-block-types';

export interface ViewChosenSavedBlockPaneProps {
  chosenBlock: ChosenBlock;

  addChosenBlock: () => void;
  goBackToAddBlockPane: () => void;
}

@Component({
  components: {
    'vue-markdown': VueMarkdown
  }
})
export default class ViewChosenSavedBlockPane extends Vue implements ViewChosenSavedBlockPaneProps {
  @Prop({ required: true }) chosenBlock!: ChosenBlock;

  @Prop({ required: true }) addChosenBlock!: () => void;
  @Prop({ required: true }) goBackToAddBlockPane!: () => void;

  public renderBlockSelect() {
    const block = this.chosenBlock.block;

    const imagePath = blockTypeToImageLookup[block.type].path;
    const durationSinceUpdated = moment.duration(-moment().diff(block.timestamp * 1000)).humanize(true);

    const isPrivateBlock = this.chosenBlock.blockSource === 'private';
    const shareStatusText = isPrivateBlock && <div class="text-muted text-align--center">{block.share_status}</div>;

    return (
      <div class="width--100percent">
        <div class="display--flex flex-grow--1 width--100percent" style={{ 'min-width': '320px' }}>
          <div>
            <img class="add-block__image" src={imagePath} alt={block.name} />
            {shareStatusText}
          </div>
          <div class="flex-column align-items-start add-block__content">
            <div class="d-flex w-100 justify-content-between">
              <b class="mb-1">{block.name}</b>
              <small>{durationSinceUpdated}</small>
            </div>
            <div class="add-saved-block-container__description mb-1">
              <vue-markdown html={false} source={block.description} />
            </div>
          </div>
        </div>
        <b-button class="mt-3 col-12" variant="primary" on={{ click: () => this.addChosenBlock() }}>
          Add Block
        </b-button>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="container text-align--left mb-3">
        <a
          href=""
          class="mb-2 padding-bottom--normal mt-2 d-block"
          style="border-bottom: 1px dashed #eee;"
          on={{ click: preventDefaultWrapper(this.goBackToAddBlockPane) }}
        >
          {'<< Go Back'}
        </a>
        {this.renderBlockSelect()}
      </div>
    );
  }
}
