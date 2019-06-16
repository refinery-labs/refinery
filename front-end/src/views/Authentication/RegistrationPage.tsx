import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import StripeAddPaymentCard from '@/components/Common/StripeAddPaymentCard.vue';

const user = namespace('user');

@Component
export default class RegistrationPage extends Vue {
  @user.State registrationEmailInput!: string;
  @user.State registrationNameInput!: string;
  @user.State registrationPhoneInput!: string;
  @user.State registrationOrgNameInput!: string;
  @user.State registrationStripeToken!: string;
  @user.State termsAndConditionsAgreed!: boolean;

  @user.State registrationEmailInputValid!: boolean | null;
  @user.State registrationNameInputValid!: boolean | null;
  @user.State registrationPhoneInputValid!: boolean | null;
  @user.State registrationOrgNameInputValid!: boolean | null;
  @user.State termsAndConditionsAgreedValid!: boolean | null;

  @user.State isBusy!: boolean;
  @user.State registrationErrorMessage!: string | null;
  @user.State registrationSuccessMessage!: string | null;
  @user.State registrationEmailErrorMessage!: string | null;

  @user.Mutation setRegisterEmailInputValue!: (s: string) => void;
  @user.Mutation setRegistrationStripeToken!: (s: string) => void;
  @user.Mutation setRegisterNameInputValue!: (s: string) => void;
  @user.Mutation setRegisterPhoneInputValue!: (s: string) => void;
  @user.Mutation setRegisterOrgNameInputValue!: (s: string) => void;
  @user.Mutation setAgreeToTermsValue!: (s: boolean) => void;

  @user.Action registerUser!: () => void;
  @user.Action redirectIfAuthenticated!: () => void;

  onSubmit(evt: Event) {
    evt.preventDefault();
    // Disabled temporarily
    this.registerUser();
  }

  onReset(evt: Event) {
    evt.preventDefault();
    // Reset inputs
  }

  onTermsCheckboxUpdated(e: Event) {
    this.setAgreeToTermsValue(!this.termsAndConditionsAgreed);
  }

  mounted() {
    if (process.env.NODE_ENV === 'development') {
      console.log('Yo dev friend, use this card number to register: 5555555555554444');
    }

    this.redirectIfAuthenticated();
  }

  setStripeToken(stripeToken: string) {
    this.setRegistrationStripeToken(stripeToken);
  }

  public renderLoginForm() {
    const classes = {
      'block-center mt-4 wd-xl': true,
      'whirl standard': this.isBusy
    };

    const stripeCardProps = {
      setRegistrationStripeTokenValue: this.setStripeToken
    };

    const emailInputErrorMessage =
      this.registrationEmailErrorMessage || 'Your must register with a valid email address.';

    // Modified Designer code... Hence not being Vue-Bootstrap entirely.
    return (
      <div class={classes}>
        <b-card border-variant="dark" header-bg-variant="dark">
          <a slot="header" class="mb-0 text-center" href="/">
            <img
              class="block-center rounded logo-fit"
              src="/img/logo.png"
              alt="The World's First Drag-and-Drop Serverless IDE!"
            />
          </a>
          <p class="text-center py-2">Register and receive free, instant access!</p>
          <b-form on={{ submit: this.onSubmit, reset: this.onReset }} class="mb-3 text-align--left">
            <b-form-group
              id="user-email-group"
              description="You must provide a valid email address in order to log in to your account. No password required!"
            >
              <label class="text-muted d-block" htmlFor="user-email-input">
                Email address:
              </label>

              <div class="input-group with-focus">
                <b-form-input
                  id="user-email-input"
                  class="form-control border-right-0"
                  value={this.registrationEmailInput}
                  on={{ change: this.setRegisterEmailInputValue }}
                  type="email"
                  required
                  placeholder="user@example.com"
                  state={this.registrationEmailInputValid}
                  autofocus={true}
                />
                <div class="input-group-append">
                  <span class="input-group-text text-muted bg-transparent border-left-0">
                    <em class="fa fa-envelope" />
                  </span>
                </div>
              </div>
              <b-form-invalid-feedback state={this.registrationEmailInputValid}>
                {emailInputErrorMessage}
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="user-name-group"
              description="Please use the same name as the one that appears on your credit card."
            >
              <label class="text-muted d-block" htmlFor="user-name-input" id="user-name-group">
                Full Name:
              </label>

              <div class="input-group with-focus">
                <b-form-input
                  id="user-name-input"
                  class="form-control border-right-0"
                  value={this.registrationNameInput}
                  on={{ change: this.setRegisterNameInputValue }}
                  type="text"
                  required
                  placeholder="John Doe"
                  state={this.registrationNameInputValid}
                  autofocus={true}
                />
                <div class="input-group-append">
                  <span class="input-group-text text-muted bg-transparent border-left-0">
                    <em class="fa fa-file-signature" />
                  </span>
                </div>
              </div>
              <b-form-invalid-feedback state={this.registrationNameInputValid}>
                Your name must contain First + Last name and not contain numbers.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="user-phone-group"
              description="Please provide a real phone number. This helps us prevent abuse of our service and helps us improve our customer experience."
            >
              <label class="text-muted d-block" htmlFor="user-phone-input" id="user-phone-group">
                Phone Number:
              </label>
              <div class="input-group with-focus">
                <b-form-input
                  id="user-phone-input"
                  class="form-control border-right-0"
                  value={this.registrationPhoneInput}
                  on={{ change: this.setRegisterPhoneInputValue }}
                  type="tel"
                  placeholder="+1 (555) 555-5555"
                  required
                  state={this.registrationPhoneInputValid}
                  autofocus={true}
                />
                <div class="input-group-append">
                  <span class="input-group-text text-muted bg-transparent border-left-0">
                    <em class="fa fa-phone" />
                  </span>
                </div>
              </div>
              <b-form-invalid-feedback state={this.registrationPhoneInputValid}>
                You must provide a valid phone number.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="org-name-group"
              description="If you are not part of an organization, you can just leave this blank."
            >
              <label class="text-muted d-block" htmlFor="org-name-input" id="org-name-group">
                Organization Name (optional):
              </label>
              <div class="input-group with-focus">
                <b-form-input
                  id="org-name-input"
                  class="form-control border-right-0"
                  value={this.registrationOrgNameInput}
                  on={{ change: this.setRegisterOrgNameInputValue }}
                  type="text"
                  placeholder="Startup Company Inc."
                  state={this.registrationOrgNameInputValid}
                  autofocus={true}
                />
                <div class="input-group-append">
                  <span class="input-group-text text-muted bg-transparent border-left-0">
                    <em class="fa fa-users" />
                  </span>
                </div>
              </div>
              <b-form-invalid-feedback state={this.registrationOrgNameInputValid}>
                Your must provide a valid Organization name.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group id="stripe-payment">
              <label class="text-muted d-block" htmlFor="user-name-input" id="user-name-group">
                Payment Information
              </label>
              {/* TypeScript can fuck right off, this works fine.
              // @ts-ignore */}
              <StripeAddPaymentCard props={stripeCardProps} />
              <br />
              {/*TODO: Replace Pricing page with actual link.*/}
              <small class="text-muted d-block">
                For more information about our pricing, see our{' '}
                <a href="#" target="_blank">
                  Pricing page
                </a>
                .
              </small>
            </b-form-group>
            <b-form-group id="terms-agree-group" class="text-align--left">
              <b-form-checkbox
                id="checkbox-1"
                name="checkbox-1"
                required
                on={{ change: this.onTermsCheckboxUpdated }}
                state={this.termsAndConditionsAgreedValid}
                checked={this.termsAndConditionsAgreed}
              >
                I have read and agree with the
                <a class="ml-1" href="#">
                  terms and conditions
                </a>
                .
              </b-form-checkbox>

              <b-form-invalid-feedback state={this.termsAndConditionsAgreedValid}>
                Your must agree to the terms and conditions.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-invalid-feedback state={this.registrationErrorMessage === null}>
              {this.registrationErrorMessage}
            </b-form-invalid-feedback>
            <button class="btn btn-block btn-primary mt-3" type="submit">
              Create account
            </button>
            <b-form-valid-feedback state={this.registrationSuccessMessage !== null}>
              {this.registrationSuccessMessage}
            </b-form-valid-feedback>
          </b-form>
          <p class="pt-3 text-center">Already have an account?</p>
          <router-link class="btn btn-block btn-secondary" to="/login">
            Login
          </router-link>
        </b-card>
        <div class="p-3 text-center">
          <span>&copy; 2019 - Refinery Labs, Inc.</span>
        </div>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="register-page">
        {this.renderLoginForm()}
        <router-view />
      </div>
    );
  }
}
