import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import StripeAddPaymentCard from '@/components/Common/StripeAddPaymentCard.vue';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { Prop } from 'vue-property-decorator';

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
  @user.State registrationOrgNameInputValid!: boolean | null;
  @user.State termsAndConditionsAgreedValid!: boolean | null;

  @user.State registrationErrorMessage!: string | null;
  @user.State registrationSuccessMessage!: string | null;
  @user.State registrationEmailErrorMessage!: string | null;

  @user.State isBusy!: boolean;
  @user.State autoRefreshJobRunning!: boolean;

  @user.Mutation setRegisterEmailInputValue!: (s: string) => void;
  @user.Mutation setRegistrationStripeToken!: (s: string) => void;
  @user.Mutation setRegisterNameInputValue!: (s: string) => void;
  @user.Mutation setRegisterPhoneInputValue!: (s: string) => void;
  @user.Mutation setRegisterOrgNameInputValue!: (s: string) => void;
  @user.Mutation setAgreeToTermsValue!: (s: boolean) => void;

  @user.Action registerUser!: () => void;
  @user.Action redirectIfAuthenticated!: () => void;
  @user.Mutation cancelAutoRefreshJob!: () => void;

  @Prop() inDemoMode?: boolean;

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
  }

  setStripeToken(stripeToken: string) {
    this.setRegistrationStripeToken(stripeToken);
  }

  public renderAwaitingEmailContents() {
    const textContents = this.registrationSuccessMessage || 'Please check your email. Waiting for login status...';

    return (
      <div class="text-align--center">
        <h4>{textContents}</h4>
        <p>
          <b-spinner />
        </p>
        <div class="text-align--left">
          <a href="" on={{ click: preventDefaultWrapper(this.cancelAutoRefreshJob) }}>
            {'<< Go Back'}
          </a>
        </div>
      </div>
    );
  }

  renderCallToAction() {
    return (
      <div>
        <h3 class="text-center py-2">Thank you for trying Refinery!</h3>
        <h4 class="font-weight-normal">Free $5 credit when you signup today. :)</h4>
        <h4 class="font-weight-normal">With Refinery, you pay only for the compute you use (minimum $5 per month).</h4>
        <h4>
          For more information, review our{' '}
          <a href="https://www.refinery.io/pricing" target="_blank">
            full pricing details here
          </a>
          .
        </h4>
      </div>
    );
  }

  public renderRegistrationFormContents() {
    const stripeCardProps = {
      setRegistrationStripeTokenValue: this.setStripeToken
    };

    const callToAction = this.renderCallToAction();

    const invalidEmailAddressMessage = 'Your must register with a valid email address.';
    const emailInputErrorMessage = this.registrationEmailErrorMessage || invalidEmailAddressMessage;

    return (
      <div>
        {callToAction}
        <b-form on={{ submit: this.onSubmit, reset: this.onReset }} class="mb-3 text-align--left">
          <b-form-group id="user-email-group">
            <b-form-invalid-feedback state={this.registrationErrorMessage === null}>
              {this.registrationErrorMessage}
            </b-form-invalid-feedback>
            <label class="text-muted d-block" htmlFor="user-email-input">
              Email address <span style="color: red;">*</span>
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
            <label class="form-text text-muted">
              You must provide a valid email address in order to log in to your account. No password required!
            </label>
            <b-form-invalid-feedback state={this.registrationEmailInputValid}>
              {emailInputErrorMessage}
            </b-form-invalid-feedback>
          </b-form-group>
          <b-form-group id="user-name-group">
            <label class="text-muted d-block" htmlFor="user-name-input" id="user-name-group">
              Billing Name <span style="color: red;">*</span>
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
              />
              <div class="input-group-append">
                <span class="input-group-text text-muted bg-transparent border-left-0">
                  <em class="fa fa-file-signature" />
                </span>
              </div>
            </div>
            <label class="form-text text-muted">
              Please use the same name as the one that appears on your credit card.
            </label>
            <b-form-invalid-feedback state={this.registrationNameInputValid}>
              Your name must contain First + Last name and not contain numbers.
            </b-form-invalid-feedback>
          </b-form-group>
          <b-form-group id="stripe-payment">
            <label class="text-muted d-block" htmlFor="user-name-input" id="user-name-group">
              Payment Information <span style="color: red;">*</span>
            </label>
            {/* TypeScript can fuck right off, this works fine.
            // @ts-ignore */}
            <StripeAddPaymentCard props={stripeCardProps} />
            {/*TODO: Replace Pricing page with actual link.*/}
            <label class="text-muted d-block">
              Free $5 credit on signup. Service is usage based (code block executions, log storage, etc) and billed on
              the 1st of every month.
              <br />
              Minimum $5 per month for compute used.
              <br />
              For more information about our pricing, see our{' '}
              <a href="https://www.refinery.io/pricing" target="_blank">
                Pricing page
              </a>
              .
            </label>
          </b-form-group>
          <b-form-group id="user-phone-group">
            <label class="text-muted d-block" htmlFor="user-phone-input" id="user-phone-group">
              Phone Number (optional)
            </label>
            <div class="input-group with-focus">
              <b-form-input
                id="user-phone-input"
                class="form-control border-right-0"
                value={this.registrationPhoneInput}
                on={{ change: this.setRegisterPhoneInputValue }}
                type="tel"
                placeholder="+1 (555) 555-5555"
                required={false}
              />
              <div class="input-group-append">
                <span class="input-group-text text-muted bg-transparent border-left-0">
                  <em class="fa fa-phone" />
                </span>
              </div>
            </div>
            <label class="form-text text-muted">
              Please provide a real phone number. This helps us prevent abuse of our service and helps us improve our
              customer experience.
            </label>
          </b-form-group>
          <b-form-group id="org-name-group">
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
              />
              <div class="input-group-append">
                <span class="input-group-text text-muted bg-transparent border-left-0">
                  <em class="fa fa-users" />
                </span>
              </div>
            </div>
            <label class="form-text text-muted">
              If you are not part of an organization, you can just leave this blank.
            </label>
            <b-form-invalid-feedback state={this.registrationOrgNameInputValid}>
              Your must provide a valid Organization name.
            </b-form-invalid-feedback>
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
              <a class="ml-1" href="/terms-of-service" target="_blank">
                terms and conditions
              </a>
              . <span style="color: red;">*</span>
            </b-form-checkbox>

            <b-form-invalid-feedback state={this.termsAndConditionsAgreedValid}>
              Your must agree to the terms and conditions.
            </b-form-invalid-feedback>
          </b-form-group>
          <b-form-invalid-feedback state={this.registrationErrorMessage === null}>
            {this.registrationErrorMessage}
          </b-form-invalid-feedback>
          <span style="color: red;">*</span> = Required Field
          <button class="btn btn-block btn-primary mt-3" type="submit">
            Create account
          </button>
          <b-form-valid-feedback state={this.registrationSuccessMessage !== null}>
            {this.registrationSuccessMessage}
          </b-form-valid-feedback>
        </b-form>
        <p class="pt-3 text-center">Already have an account?</p>
        <a class="btn btn-block btn-secondary" href="/login" target="_blank">
          Login
        </a>
      </div>
    );
  }

  public renderRegistrationForm() {
    const classes = {
      'block-center': true,
      'whirl standard': this.isBusy
    };

    const header = (
      <a slot="header" class="mb-0 text-center" href="/">
        <img
          class="block-center rounded logo-fit"
          src={require('../../../public/img/logo.png')}
          alt="The World's First Drag-and-Drop Serverless IDE!"
        />
      </a>
    );

    const contents = this.autoRefreshJobRunning
      ? this.renderAwaitingEmailContents()
      : this.renderRegistrationFormContents();

    // Modified Designer code... Hence not being Vue-Bootstrap entirely.
    return (
      <div class={classes}>
        <b-card border-variant="dark" header-bg-variant="dark">
          {!this.inDemoMode && header}
          {contents}
        </b-card>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    const classes = {
      'register-page': true,
      'block-center mt-4 wd-xxl': !this.inDemoMode,
      'mt-2': this.inDemoMode
    };

    const footer = (
      <div class="p-3 text-center">
        <span>&copy; 2020 - Refinery Labs, Inc.</span>
      </div>
    );

    return (
      <div class={classes}>
        {this.renderRegistrationForm()}
        {!this.inDemoMode && footer}
      </div>
    );
  }
}
