import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { AddSavedBlockPaneStoreModule } from '@/store/modules/panes/add-saved-block-pane';
import AddSavedBlockPane, {
  AddSavedBlockPaneProps
} from '@/components/ProjectEditor/saved-blocks-components/AddSavedBlockPane';
import ViewChosenSavedBlockPane, {
  ViewChosenSavedBlockPaneProps
} from '@/components/ProjectEditor/saved-blocks-components/ViewChosenSavedBlockPane';
import { ChosenBlock } from '@/types/add-block-types';

@Component
export default class AddSavedBlockPaneContainer extends Vue {
  // First step of the process to "choose" a block
  public renderChooseBlockPane() {
    const addSavedBlockPaneProps: AddSavedBlockPaneProps = {
      searchResultsPrivate: AddSavedBlockPaneStoreModule.searchResultsPrivate,
      searchResultsPublished: AddSavedBlockPaneStoreModule.searchResultsPublished,
      isBusySearching: AddSavedBlockPaneStoreModule.isBusySearching,
      searchInput: AddSavedBlockPaneStoreModule.searchInput,
      addChosenBlock: id => AddSavedBlockPaneStoreModule.selectBlockToAdd(id),
      goBackToAddBlockPane: () => AddSavedBlockPaneStoreModule.goBackToAddBlockPane(),
      searchSavedBlocks: () => AddSavedBlockPaneStoreModule.searchSavedBlocks(),
      setSearchInputValue: val => AddSavedBlockPaneStoreModule.setSearchInputValue(val)
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
