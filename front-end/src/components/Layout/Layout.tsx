import Vue from 'vue';
import Header from './Header.vue';
import Sidebar from './Sidebar.vue';
import Offsidebar from './Offsidebar.vue';
import Footer from './Footer';
import ContentWrapper from './ContentWrapper.vue';
import {Component} from 'vue-property-decorator';
import GlobalNavSidebar from '@/components/Layout/GlobalNavSidebar';

Vue.component('ContentWrapper', ContentWrapper);

@Component({
  components: {
    GlobalNavSidebar,
    Header,
    Sidebar,
    Offsidebar,
    Footer
  }
})
export default class Layout extends Vue {
  
  render() {
    
    return (
      <div class="app-content height--100percent">
        <GlobalNavSidebar />
    
        <div class="wrapper">
          {/*top navbar*/}
          <Header/>
      
          <Sidebar/>
      
          <Offsidebar/>
      
          {/*Main section*/}
          <section class="section-container">
            {/*Page content*/}
            <router-view/>
          </section>
      
          <Footer/>
          
        </div>
      </div>
    );
  }
}
