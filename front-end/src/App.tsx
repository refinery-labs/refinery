import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import '@/styles/app.scss';
import SidebarNav, {NavItem} from '@/components/SidebarNav';

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
    SidebarNav
  }
})
export default class App extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div id="app" class="display--flex">
        {/*<div id="nav">*/}
        {/*<router-link to="/">Home</router-link> |*/}
        {/*<router-link to="/about">About</router-link>*/}
        {/*</div>*/}
        
        <SidebarNav props={{navItems}}/>
        <div class="flex-grow--3">
          <router-view />
        </div>
      </div>
    );
  }
}
