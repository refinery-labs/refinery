import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component
export default class TopNavbar extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="top-navbar">
        <b-navbar
          toggleable="lg"
          type="dark"
          variant="info"
          fixed="top"
          sticky={true}
        >
          <b-navbar-brand to="/">
            <img src="https://placekitten.com/g/120/32" alt="Kitten" />
          </b-navbar-brand>

          <b-navbar-toggle target="nav-collapse" />

          <b-collapse id="nav-collapse" is-nav>
            <b-navbar-nav>
              <b-nav-item to="/projects">Projects</b-nav-item>
              <b-nav-item to="/marketplace">Marketplace</b-nav-item>
              <b-nav-item to="/settings">Settings</b-nav-item>
              <b-nav-item to="/admin">Admin</b-nav-item>
            </b-navbar-nav>

            <b-navbar-nav class="ml-auto">
              <b-nav-form>
                <b-form-input size="sm" class="mr-sm-2" placeholder="Search" />
                <b-button size="sm" class="my-2 my-sm-0" type="submit">
                  Search
                </b-button>
              </b-nav-form>

              <b-nav-item-dropdown right>
                <template slot="button-content">
                  <em>Account</em>
                </template>
                <b-dropdown-item to="/profile">Profile</b-dropdown-item>
                {/* TODO: Make these links trigger via POST to avoid CSRF */}
                <b-dropdown-item to="/switch-account">
                  Switch Account
                </b-dropdown-item>
                <b-dropdown-item to="/sign-out">Sign Out</b-dropdown-item>
              </b-nav-item-dropdown>
            </b-navbar-nav>
          </b-collapse>
        </b-navbar>
      </div>
    );
  }
}
