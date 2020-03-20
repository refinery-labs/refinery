import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import moment from 'moment';
import { blockTypeToImageLookup } from '@/constants/project-editor-img-constants';
import { debounce } from 'debounce';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { Prop } from 'vue-property-decorator';
import { SavedBlockSearchResult, SharedBlockPublishStatus } from '@/types/api-types';
import RefineryMarkdown from '@/components/Common/RefineryMarkdown';
import { MarkdownProps } from '@/types/component-types';
import { SupportedLanguage } from '@/types/graph';
import { toTitleCase } from '@/lib/general-utils';

export interface AddSavedBlockPaneProps {
  searchResultsPrivate: SavedBlockSearchResult[];
  searchResultsPublished: SavedBlockSearchResult[];
  searchResultsGit: SavedBlockSearchResult[];
  searchInput: string;
  languageInput: string;
  blockTypeInput: string;
  isBusySearching: boolean;

  addChosenBlock: (id: string) => void;
  goBackToAddBlockPane: () => void;
  searchSavedBlocks: () => void;
  importProjectGitBlocks: () => void;
  setSearchInputValue: (value: string) => void;
  setLanguageInputValue: (value: string) => void;
  setBlockTypeInputValue: (value: string) => void;
}

@Component
export default class AddSavedBlockPane extends Vue implements AddSavedBlockPaneProps {
  runSearchAutomatically: () => void = () => {};

  @Prop({ required: true }) searchResultsPrivate!: SavedBlockSearchResult[];
  @Prop({ required: true }) searchResultsPublished!: SavedBlockSearchResult[];
  @Prop({ required: true }) searchResultsGit!: SavedBlockSearchResult[];
  @Prop({ required: true }) searchInput!: string;
  @Prop({ required: true }) languageInput!: string;
  @Prop({ required: true }) blockTypeInput!: string;
  @Prop({ required: true }) isBusySearching!: boolean;

  @Prop({ required: true }) addChosenBlock!: (id: string) => void;
  @Prop({ required: true }) goBackToAddBlockPane!: () => void;
  @Prop({ required: true }) searchSavedBlocks!: () => void;
  @Prop({ required: true }) importProjectGitBlocks!: () => void;
  @Prop({ required: true }) setSearchInputValue!: (value: string) => void;
  @Prop({ required: true }) setLanguageInputValue!: (value: string) => void;
  @Prop({ required: true }) setBlockTypeInputValue!: (value: string) => void;

  mounted() {
    // We have to add this at run time or else it seems to get bjorked
    this.runSearchAutomatically = debounce(this.searchSavedBlocks, 200);

    this.searchSavedBlocks();
  }

  onSearchBoxInputChanged(value: string) {
    this.setSearchInputValue(value);
    this.runSearchAutomatically();
  }

  onLanguageBoxInputChanged(language: SupportedLanguage) {
    this.setLanguageInputValue(language);
    this.runSearchAutomatically();
  }

  onBlockTypeInputChanged(blockType: SharedBlockPublishStatus) {
    this.setBlockTypeInputValue(blockType);
    this.runSearchAutomatically();
  }

  public renderBlockSelect(showStatus: boolean, block: SavedBlockSearchResult) {
    const imagePath = blockTypeToImageLookup[block.type].path;
    const durationSinceUpdated = moment.duration(-moment().diff(block.timestamp * 1000)).humanize(true);
    const sharePillVariable = block.share_status === SharedBlockPublishStatus.PRIVATE ? 'success' : 'primary';
    const shareStatusText = showStatus && (
      <div class="text-muted text-align--center">
        <b-badge variant={sharePillVariable}>{block.share_status}</b-badge>
      </div>
    );

    const markdownProps: MarkdownProps = {
      content: block.description,
      stripMarkup: true
    };

    return (
      <b-list-group-item class="display--flex" button on={{ click: () => this.addChosenBlock(block.id) }}>
        <div>
          <img class="add-block__image" src={imagePath} alt={block.name} />
          {shareStatusText}
        </div>
        <div class="flex-column align-items-start add-block__content">
          <div class="d-flex w-100 justify-content-between">
            <b class="mb-1">{block.name}</b>
            <small>Published {durationSinceUpdated}</small>
          </div>
          <div class="add-saved-block-container__result mb-1">
            <RefineryMarkdown props={markdownProps} />
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
      <div class="flex-grow--1 padding-left--micro padding-right--micro">
        <h4 class="padding-top--normal padding-left--normal">{categoryHeaderText}:</h4>
        <b-list-group class="add-saved-block-container add-block-container">
          {searchResults.map(result => this.renderBlockSelect(privateBlocks, result))}
        </b-list-group>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const privateBlocks = this.searchResultsPrivate;
    const publishedBlocks = this.searchResultsPublished;
    const gitBlocks = this.searchResultsGit;
    const zeroResults = privateBlocks.length === 0 && publishedBlocks.length === 0 && gitBlocks.length === 0;

    const defaultLanguageOption = {
      value: '',
      text: 'All Languages'
    };

    const languageOptions = [
      defaultLanguageOption,
      ...Object.values(SupportedLanguage).map(v => ({
        value: v,
        text: v
      }))
    ];

    const defaultTypesOption = {
      value: '',
      text: 'All'
    };

    const typeOptions = [
      defaultTypesOption,
      ...Object.values(SharedBlockPublishStatus).map(v => ({
        value: v,
        text: toTitleCase(v)
      }))
    ];

    const buttonOnClicks = {
      click: () => {
        this.importProjectGitBlocks();
      }
    };

    return (
      <div class="add-saved-block-container__parent text-align--left mb-2 ml-2 mr-2 mt-0 display--flex flex-direction--column">
        <a
          href=""
          class="mb-2 padding-bottom--normal mt-2 d-block"
          style="border-bottom: 1px dashed #eee;"
          on={{ click: preventDefaultWrapper(this.goBackToAddBlockPane) }}
        >
          {'<< Go Back'}
        </a>
        <div class="display--flex flex-wrap">
          <div class="filter-pane-column width--100-percent">
            <b-form-group
              class="padding-bottom--normal-small margin-bottom--normal-small"
              description="Saved blocks are searched with the provided options."
            >
              <div class="padding-bottom--normal-small">
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
              </div>
              <div class="padding-bottom--normal-small">
                <div class="display--flex">
                  <label class="flex-grow--1">Search by Type:</label>
                </div>
                <b-form-select
                  on={{ input: this.onBlockTypeInputChanged }}
                  value={this.blockTypeInput}
                  options={typeOptions}
                />
              </div>
              <div class="padding-bottom--normal-small">
                <div class="display--flex">
                  <label class="flex-grow--1">Search by Language:</label>
                </div>
                <b-form-select
                  on={{ input: this.onLanguageBoxInputChanged }}
                  value={this.languageInput}
                  options={languageOptions}
                />
              </div>
            </b-form-group>
            <b-button on={buttonOnClicks} variant="primary">
              Load Git Blocks
            </b-button>
          </div>
          <div class="filter-pane-column width--100-percent scrollable-pane-container">
            {!zeroResults && (
              <div class="flex-grow--1">
                {this.renderResultsByCategory(true, privateBlocks)}
                {this.renderResultsByCategory(true, gitBlocks)}
                {this.renderResultsByCategory(false, publishedBlocks)}
              </div>
            )}
            {zeroResults && <h4 class="text-align--center">No saved blocks were found.</h4>}
          </div>
        </div>
      </div>
    );
  }
}
