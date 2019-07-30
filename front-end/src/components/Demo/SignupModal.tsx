import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import RegistrationPage from '@/views/Authentication/RegistrationPage';
import { UnauthViewProjectStoreModule } from '@/store/modules/unauth-view-project';

export interface SignupModalProps {
  isModal?: boolean;
  showModal: boolean;
  closeModal: () => void;
}

@Component
export default class SignupModal extends Vue implements SignupModalProps {
  @Prop({ default: true }) isModal?: boolean;
  @Prop({ required: true }) showModal!: boolean;
  @Prop({ required: true }) closeModal!: () => void;

  renderContents() {
    return (
      <div class="signup-modal-container mt-0">
        <RegistrationPage props={{ inDemoMode: true }} />
      </div>
    );
  }

  renderModal() {
    const modalOnHandlers = {
      hidden: () => this.closeModal()
    };

    return (
      <b-modal
        on={modalOnHandlers}
        size=" mt-2 no-modal-body-padding"
        hide-footer={true}
        no-close-on-esc={true}
        title="Signup for Refinery to complete this action"
        visible={this.showModal}
      >
        {this.renderContents()}
      </b-modal>
    );
  }

  render() {
    if (this.isModal) {
      return this.renderModal();
    }

    return this.renderContents();
  }
}
