import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import moment from 'moment';
import {blockTypeToImageLookup} from '@/constants/project-editor-constants';
import {debounce} from 'debounce';
import {preventDefaultWrapper} from '@/utils/dom-utils';
import {Prop} from 'vue-property-decorator';
import {SavedBlockSearchResult, SharedBlockPublishStatus} from '@/types/api-types';
import VueMarkdown from 'vue-markdown';

export interface AddSavedBlockPaneProps {
  searchResultsPrivate: SavedBlockSearchResult[];
  searchResultsPublished: SavedBlockSearchResult[];
  searchInput: string;
  isBusySearching: boolean;

  addChosenBlock: (id: string) => void;
  goBackToAddBlockPane: () => void;
  searchSavedBlocks: () => void;
  setSearchInputValue: (value: string) => void;
}

@Component({
  components: {
    'vue-markdown': VueMarkdown
  }
})
export default class AddSavedBlockPane extends Vue implements AddSavedBlockPaneProps {
  runSearchAutomatically: () => void = () => {};

  @Prop({ required: true }) searchResultsPrivate!: SavedBlockSearchResult[];
  @Prop({ required: true }) searchResultsPublished!: SavedBlockSearchResult[];
  @Prop({ required: true }) searchInput!: string;
  @Prop({ required: true }) isBusySearching!: boolean;

  @Prop({ required: true }) addChosenBlock!: (id: string) => void;
  @Prop({ required: true }) goBackToAddBlockPane!: () => void;
  @Prop({ required: true }) searchSavedBlocks!: () => void;
  @Prop({ required: true }) setSearchInputValue!: (value: string) => void;

  mounted() {
    // We have to add this at run time or else it seems to get bjorked
    this.runSearchAutomatically = debounce(this.searchSavedBlocks, 200);

    this.searchSavedBlocks();
  }

  onSearchBoxInputChanged(value: string) {
    this.setSearchInputValue(value);
    this.runSearchAutomatically();
  }

  public renderBlockSelect(showStatus: boolean, block: SavedBlockSearchResult) {
    const imagePath = blockTypeToImageLookup[block.type].path;
    const durationSinceUpdated = moment.duration(-moment().diff(block.timestamp * 1000)).humanize(true);
    const sharePillVariable = block.share_status === SharedBlockPublishStatus.PRIVATE ? "success" : "primary";
    const shareStatusText = showStatus && <div class="text-muted text-align--center"><b-badge variant={sharePillVariable}>{block.share_status}</b-badge></div>;

    return (
      <b-list-group-item class="display--flex" button on={{ click: () => this.addChosenBlock(block.id) }}>
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
      </b-list-group-item>
    );
  }

  public renderResultsByCategory(privateBlocks: boolean, searchResults: SavedBlockSearchResult[]) {
    // Only display the section if we have results.
    if (!searchResults || searchResults.length === 0) {
      return null;
    }

    const categoryHeaderText = privateBlocks ? 'Your Saved Blocks' : 'From Public Block Repository';

    return (
      <div>
        <h4>{categoryHeaderText}:</h4>
        <b-list-group class="add-saved-block-container add-block-container">
          {searchResults.map(result => this.renderBlockSelect(privateBlocks, result))}
        </b-list-group>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const privateBlocks = this.searchResultsPrivate;
    const publishedBlocks = this.searchResultsPublished;
    const zeroResults = privateBlocks.length === 0 && publishedBlocks.length === 0;

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
        <b-form-group
          class="padding-bottom--normal-small margin-bottom--normal-small"
          description="Please specify some text to search for saved blocks with."
        >
          <div class="display--flex">
            <label class="flex-grow--1">Search by Name:</label>
            {this.isBusySearching && <b-spinner class="ml-auto" small={true} />}
          </div>
          <b-form-input
            type="text"
            autofocus={true}
            required={true}
            value={this.searchInput}
            on={{ input: this.onSearchBoxInputChanged }}
            placeholder="eg, Daily Timer"
          />
        </b-form-group>
        {this.renderResultsByCategory(true, privateBlocks)}
        {this.renderResultsByCategory(false, publishedBlocks)}
        {zeroResults && <h4 class="text-align--center">No saved blocks were found.</h4>}
      </div>
    );
  }
}
