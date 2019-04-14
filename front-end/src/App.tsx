import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import '@/styles/app.scss';

// The @Component decorator indicates the class is a Vue component
@Component
export default class App extends Vue {
   public render(h: CreateElement): VNode {
       return (
           <div id="app">
               <div id="nav">
                   <router-link to="/">Home</router-link> |
                   <router-link to="/about">About</router-link>
               </div>
               <router-view />
           </div>
       );
   }
}