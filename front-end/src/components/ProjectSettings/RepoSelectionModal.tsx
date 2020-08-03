import Component from 'vue-class-component';
import Vue from 'vue';
import { RepoSelectorStoreModule } from '@/store';
import RepoSelector, { RepoSelectorProps } from '@/components/ProjectSettings/RepoSelector';
import { Prop } from 'vue-property-decorator';

export interface RepoSelectionModalProps {
  visible: boolean;
  hidden: () => void;
}

@Component
export default class RepoSelectionModal extends Vue implements RepoSelectionModalProps {
  @Prop({ required: true }) visible!: boolean;
  @Prop({ required: true }) hidden!: () => void;

  private render() {
    const modalOnHandlers = {
      hidden: this.hidden
    };

    const repoSelectorProps: RepoSelectorProps = {
      selectedRepoCallback: this.hidden
    };

    return (
      <b-modal
        on={modalOnHandlers}
        ok-variant="danger"
        footer-class="p-2"
        ref="console-modal"
        hide-footer
        title="Select Project Repo"
        visible={this.visible}
      >
        <RepoSelector props={repoSelectorProps} />
      </b-modal>
    );
  }
}
