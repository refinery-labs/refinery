import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';

const user = namespace('user');

@Component
export default class LoginPage extends Vue {
  @user.State rememberMeToggled!: boolean;
  @user.State loginEmailInput!: string;
  @user.State loginEmailInputValid!: boolean;
  @user.State isBusy!: boolean;
  @user.State loginAttemptMessage!: string | null;
  @user.State loginErrorMessage!: string | null;
  @user.State authenticated!: boolean;

  @user.Mutation setRememberMeState!: (s: boolean) => void;
  @user.Mutation setEmailInputValue!: (s: string) => void;

  @user.Action loginUser!: () => void;
  @user.Action redirectIfAuthenticated!: () => void;

  onSubmit(evt: Event) {
    evt.preventDefault();
    this.loginUser();
  }

  onReset(evt: Event) {
    evt.preventDefault();
    // Reset inputs
  }

  mounted() {
    this.redirectIfAuthenticated();

    if (this.rememberMeToggled) {
      this.setEmailInputValue(this.loginEmailInput);
    }
  }

  onRememberMeUpdated(e: Event) {
    this.setRememberMeState(!this.rememberMeToggled);
  }

  onEmailInputUpdated(val: string) {
    this.setEmailInputValue(val);
  }

  public renderLoginForm() {
    const classes = {
      'block-center mt-4 wd-xl': true,
      'whirl standard': this.isBusy
    };

    // Modified Designer code... Hence not being Vue-Bootstrap entirely.
    return (
      <div class={classes}>
        <b-card border-variant="dark" header-bg-variant="dark">
          <a slot="header" class="mb-0 text-center" href="/">
            <img class="block-center rounded" src="img/logo.png" alt="Image" />
          </a>
          <p class="text-center py-2">
            Welcome to Refinery! <br />
            Please sign in to continue.
          </p>
          <b-form
            on={{ submit: this.onSubmit, reset: this.onReset }}
            class="mb-3 text-align--left"
          >
            <b-form-group
              id="user-email-group"
              description="You will receive an email with a magical link to log in."
            >
              <label
                class="text-muted d-block"
                for="user-email-input"
                id="user-email-group"
              >
                Email address:
              </label>
              <div class="input-group with-focus">
                <b-form-input
                  id="user-email-input"
                  class="form-control border-right-0"
                  value={this.loginEmailInput}
                  on={{ input: this.onEmailInputUpdated }}
                  type="email"
                  required
                  placeholder="user@example.com"
                  state={this.loginEmailInputValid}
                  autofocus={true}
                />
                <div class="input-group-append">
                  <span class="input-group-text text-muted bg-transparent border-left-0">
                    <em class="fa fa-envelope" />
                  </span>
                </div>
              </div>
              <b-form-invalid-feedback state={this.loginEmailInputValid}>
                Your name must contain First + Last name and not contain
                numbers.
              </b-form-invalid-feedback>
            </b-form-group>
            <div class="text-align--left">
              <b-form-checkbox
                id="checkbox-1"
                name="checkbox-1"
                on={{ change: this.onRememberMeUpdated }}
                checked={this.rememberMeToggled}
              >
                Remember Me
              </b-form-checkbox>
            </div>
            <button class="btn btn-block btn-primary mt-3" type="submit">
              Login
            </button>
            <b-form-invalid-feedback state={this.loginErrorMessage === null}>
              {this.loginErrorMessage}
            </b-form-invalid-feedback>
            <b-form-valid-feedback state={this.loginAttemptMessage !== null}>
              {this.loginAttemptMessage}
            </b-form-valid-feedback>
          </b-form>
          <p class="pt-3 text-center">Need to Signup?</p>
          <router-link class="btn btn-block btn-secondary" to="/register">
            Register Now
          </router-link>
        </b-card>
        <div class="p-3 text-center">
          <span class="mr-2">&copy;</span>
          <span>2019</span>
          <span class="mr-2">-</span>
          <span>Refinery Labs, Inc.</span>
        </div>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="login-page">
        <h2>Login To Refinery</h2>
        {this.renderLoginForm()}
        <router-view />
      </div>
    );
  }
}
