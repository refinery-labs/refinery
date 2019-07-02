import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import moment from 'moment';
import { availableBlocks, AddGraphElementConfig, blockTypeToImageLookup } from '@/constants/project-editor-constants';
import { debounce } from 'debounce';
import { AddSavedBlockPaneStoreModule, SavedBlockSearchResult } from '@/store/modules/panes/add-saved-block-pane';
import { preventDefaultWrapper } from '@/utils/dom-utils';

@Component
export default class AddSavedBlockPane extends Vue {
  runSearchAutomatically: () => void = debounce(function() {
    AddSavedBlockPaneStoreModule.searchSavedBlocks();
  }, 200);

  mounted() {
    AddSavedBlockPaneStoreModule.searchSavedBlocks();
  }

  onSearchBoxInputChanged(value: string) {
    AddSavedBlockPaneStoreModule.setSearchInputValue(value);
    // AddSavedBlockPaneStoreModule.searchSavedBlocks();
    this.runSearchAutomatically();
  }

  public renderBlockSelect(block: SavedBlockSearchResult) {
    const imagePath = blockTypeToImageLookup[block.type].path;
    const durationSinceUpdated = moment.duration(-moment().diff(block.timestamp * 1000)).humanize(true);

    return (
      <b-list-group-item class="display--flex" button>
        <img class="add-block__image" src={imagePath} alt={block.name} />
        <div class="flex-column align-items-start add-block__content">
          <div class="d-flex w-100 justify-content-between">
            <h5 class="mb-1">{block.name}</h5>
            <small>{durationSinceUpdated}</small>
          </div>

          <p class="mb-1">{block.description}</p>
        </div>
      </b-list-group-item>
    );
  }

  public renderResultsByCategory(category: string, searchResults: SavedBlockSearchResult[]) {
    // Only display the section if we have results.
    if (!searchResults || searchResults.length === 0) {
      return null;
    }

    return (
      <div>
        <h4>{category}:</h4>
        <b-list-group class="add-saved-block-container add-block-container">
          {searchResults.map(this.renderBlockSelect)}
        </b-list-group>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const privateBlocks = AddSavedBlockPaneStoreModule.searchResultsPrivate;
    const publishedBlocks = AddSavedBlockPaneStoreModule.searchResultsPublished;
    const zeroResults = privateBlocks.length === 0 && publishedBlocks.length === 0;

    return (
      <div class="container text-align--left mb-3">
        <a
          href=""
          class="mb-2 padding-bottom--normal mt-2 d-block"
          style="border-bottom: 1px dashed #eee;"
          on={{ click: preventDefaultWrapper(AddSavedBlockPaneStoreModule.goBackToAddBlockPane) }}
        >
          {'<< Go Back'}
        </a>
        <b-form-group
          class="padding-bottom--normal-small margin-bottom--normal-small"
          description="Please specify some text to search for saved blocks with."
        >
          <label class="d-block">Search by Name:</label>
          <b-form-input
            type="text"
            autofocus={true}
            required={true}
            value={AddSavedBlockPaneStoreModule.searchInput}
            on={{ input: this.onSearchBoxInputChanged }}
            placeholder="eg, Daily Timer"
          />
        </b-form-group>
        {this.renderResultsByCategory('Private', privateBlocks)}
        {this.renderResultsByCategory('Published', publishedBlocks)}
        {zeroResults && <h4 class="text-align--center">No saved blocks were found.</h4>}
      </div>
    );
  }
}
