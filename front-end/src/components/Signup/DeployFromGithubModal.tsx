import Component from 'vue-class-component';
import Vue from 'vue';
import RepoSelector, { RepoSelectorProps } from '@/components/ProjectSettings/RepoSelector';
import { Prop } from 'vue-property-decorator';
import DeployFromGithub from '@/components/Signup/DeployFromGithub';

export interface DeployFromGithubModalProps {
  visible: boolean;
}

@Component
export default class DeployFromGithubModal extends Vue implements DeployFromGithubModalProps {
  @Prop({ required: true }) visible!: boolean;

  private render() {
    const modalOnHandlers = {
      hidden: (e: Event) => {}
    };

    return (
      <b-modal
        on={modalOnHandlers}
        ok-variant="danger"
        footer-class="p-2"
        ref="console-modal"
        hide-footer
        hide-header
        visible={this.visible}
        no-close-on-backdrop
        hide-header-close
      >
        <DeployFromGithub />
      </b-modal>
    );
  }
}
