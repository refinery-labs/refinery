import Component from 'vue-class-component';
import Vue, { CreateElement, VNode } from 'vue';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import { EditSharedFileLinksPaneModule } from '@/store/modules/panes/edit-shared-file-links';

@Component
export default class EditSharedFileLinksPane extends Vue {
  getBlockFileSystemTree() {
    return [
      {
        title: 'Base Folder',
        isExpanded: true,
        children: [
          {
            title: 'lambda.py',
            isLeaf: true,
            isSelectable: false
          },
          {
            title: 'libraries',
            isExpanded: false,
            children: []
          }
        ]
      }
    ];
  }

  selectedFolder(event: any) {
    console.log(event);
  }

  public render(h: CreateElement): VNode {
    const treeProps = {
      value: this.getBlockFileSystemTree()
    };
    return (
      <div class="text-align--left mb-2 ml-2 mr-2 mt-0 display--flex flex-direction--column shared-file-links-pane">
        <b-form-group>
          <a
            href=""
            class="mt-2 d-block"
            on={{ click: preventDefaultWrapper(EditSharedFileLinksPaneModule.navigateBackToEditSharedFile) }}
          >
            {'<< Go Back'}
          </a>
        </b-form-group>

        {/*<b-form-group*/}
        {/*  className="padding-bottom--normal-small margin-bottom--normal-small"*/}
        {/*  description="Select a folder to place this Shared File in the Code Block."*/}
        {/*>*/}
        {/*  <div class="display--flex flex-wrap mb-1">*/}
        {/*    <label class="d-block flex-grow--1 pt-1">Select a folder to save your Shared File to:</label>*/}
        {/*    <div class="flex-grow display--flex">*/}
        {/*      <b-button variant="outline-primary">*/}
        {/*        <span class="fa fa-folder-open" /> Add Folder*/}
        {/*      </b-button>*/}
        {/*    </div>*/}
        {/*  </div>*/}
        {/*  <sl-vue-tree props={treeProps} on={{ nodeclick: this.selectedFolder }}>*/}
        {/*    <div class="contextmenu" ref="contextmenu">*/}
        {/*      <div>Remove</div>*/}
        {/*    </div>*/}
        {/*  </sl-vue-tree>*/}
        {/*</b-form-group>*/}

        <div class="container">
          <div class="row">
            <b-button
              on={{ click: () => EditSharedFilePaneModule.selectCodeBlockToAddSharedFileTo() }}
              variant="info"
              class="w-100"
            >
              Add Shared File to Block
            </b-button>
          </div>
        </div>
      </div>
    );
  }
}
