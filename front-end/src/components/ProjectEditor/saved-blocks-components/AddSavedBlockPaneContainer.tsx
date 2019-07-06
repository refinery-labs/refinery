import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { AddSavedBlockPaneStoreModule } from '@/store/modules/panes/add-saved-block-pane';
import AddSavedBlockPane, {
  AddSavedBlockPaneProps
} from '@/components/ProjectEditor/saved-blocks-components/AddSavedBlockPane';

@Component
export default class AddSavedBlockPaneContainer extends Vue {
  public render(h: CreateElement): VNode {
    const addSavedBlockPaneProps: AddSavedBlockPaneProps = {
      searchResultsPrivate: AddSavedBlockPaneStoreModule.searchResultsPrivate,
      searchResultsPublished: AddSavedBlockPaneStoreModule.searchResultsPublished,
      isBusySearching: AddSavedBlockPaneStoreModule.isBusySearching,
      searchInput: AddSavedBlockPaneStoreModule.searchInput,
      addChosenBlock: id => AddSavedBlockPaneStoreModule.addChosenBlock(id),
      goBackToAddBlockPane: () => AddSavedBlockPaneStoreModule.goBackToAddBlockPane(),
      searchSavedBlocks: () => AddSavedBlockPaneStoreModule.searchSavedBlocks(),
      setSearchInputValue: val => AddSavedBlockPaneStoreModule.setSearchInputValue(val)
    };

    return <AddSavedBlockPane props={addSavedBlockPaneProps} />;
  }
}
