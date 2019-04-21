import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import SidebarNav, {NavItem} from '@/components/SidebarNav';
import TopNavbar from '@/components/TopNavbar';

const navItems: NavItem[] = [
  {
    link: '/',
    text: 'Home',
    color: 'blue'
  },
  {
    link: '/projects',
    text: 'Projects',
    color: 'red'
  }
];

@Component({
  components: {
    SidebarNav,
    TopNavbar
  }
})
export default class App extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div id="app">
        <TopNavbar />
        <div class="app-content display--flex">
          <SidebarNav props={{navItems}}/>
          <div class="flex-grow--3">
            <router-view />
          </div>
        </div>
      </div>
    );
  }
}
