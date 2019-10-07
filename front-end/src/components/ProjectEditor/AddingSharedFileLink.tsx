import Component from 'vue-class-component';
import Vue, { CreateElement, VNode } from 'vue';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import { EditSharedFileLinksPaneModule } from '@/store/modules/panes/edit-shared-file-links';

@Component
export default class AddingSharedFileLinkPane extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="text-align--center display--flex flex-direction--column adding-shared-file-link-pane">
        <h2 class="mb-3 ml-3 mr-3 mt-2">
          <i>Click on one of the flashing Code Blocks to add the Shared File to it.</i>
        </h2>
        <div class="container">
          <div class="row">
            <b-button
              on={{ click: () => EditSharedFilePaneModule.cancelSelectingCodeBlockToAddSharedFileTo() }}
              variant="danger"
              class="w-100 mb-1 ml-1 mr-1 mt-2"
            >
              Cancel Adding Shared File to Block
            </b-button>
          </div>
        </div>
      </div>
    );
  }
}
