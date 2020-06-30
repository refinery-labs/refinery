import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import AddSavedBlockPane, {
  AddSavedBlockPaneProps
} from '@/components/ProjectEditor/saved-blocks-components/AddSavedBlockPane';
import ViewChosenSavedBlockPane, {
  ViewChosenSavedBlockPaneProps
} from '@/components/ProjectEditor/saved-blocks-components/ViewChosenSavedBlockPane';
import { ChosenBlock } from '@/types/add-block-types';
import { AddSavedBlockPaneStoreModule } from '@/store';

@Component
export default class AddSavedBlockPaneContainer extends Vue {
  // First step of the process to "choose" a block
  public renderChooseBlockPane() {
    const addSavedBlockPaneProps: AddSavedBlockPaneProps = {
      searchResultsPrivate: AddSavedBlockPaneStoreModule.searchResultsPrivate,
      searchResultsPublished: AddSavedBlockPaneStoreModule.searchResultsPublished,
      isBusySearching: AddSavedBlockPaneStoreModule.isBusySearching,
      searchInput: AddSavedBlockPaneStoreModule.searchInput,
      languageInput: AddSavedBlockPaneStoreModule.languageInput,
      blockTypeInput: AddSavedBlockPaneStoreModule.blockTypeInput,
      addChosenBlock: id => AddSavedBlockPaneStoreModule.selectBlockToAdd(id),
      goBackToAddBlockPane: () => AddSavedBlockPaneStoreModule.goBackToAddBlockPane(),
      searchSavedBlocks: () => AddSavedBlockPaneStoreModule.searchSavedBlocks(),
      setSearchInputValue: val => AddSavedBlockPaneStoreModule.setSearchInputValue(val),
      setLanguageInputValue: val => AddSavedBlockPaneStoreModule.setLanguageInputValue(val),
      setBlockTypeInputValue: val => AddSavedBlockPaneStoreModule.setBlockTypeInputValue(val)
    };

    return <AddSavedBlockPane props={addSavedBlockPaneProps} />;
  }

  // Second step of the process to "add" the block
  public renderViewBlockPane(block: ChosenBlock) {
    const viewChosenSavedBlockPane: ViewChosenSavedBlockPaneProps = {
      addChosenBlock: () => AddSavedBlockPaneStoreModule.addChosenBlock(),
      chosenBlock: block,
      goBackToAddBlockPane: () => AddSavedBlockPaneStoreModule.clearChosenBlock(),

      environmentVariables: AddSavedBlockPaneStoreModule.environmentVariableEntries,
      setEnvironmentVariablesValue: (name: string, value: string) =>
        AddSavedBlockPaneStoreModule.setEnvironmentVariablesValue({ name, value })
    };

    return <ViewChosenSavedBlockPane props={viewChosenSavedBlockPane} />;
  }

  public render(h: CreateElement): VNode {
    // If we have chosen a block in the flow, render the second step of the flow
    if (AddSavedBlockPaneStoreModule.chosenBlock) {
      return this.renderViewBlockPane(AddSavedBlockPaneStoreModule.chosenBlock);
    }

    return this.renderChooseBlockPane();
  }
}
