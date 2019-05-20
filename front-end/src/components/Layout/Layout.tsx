import Vue from 'vue';
import Header from './Header.vue';
import Sidebar from './Sidebar.vue';
import Offsidebar from './Offsidebar.vue';
import Footer from './Footer';
import ContentWrapper from './ContentWrapper.vue';
import {Component} from 'vue-property-decorator';

Vue.component('ContentWrapper', ContentWrapper);

@Component({
  components: {
    Header,
    Sidebar,
    Offsidebar,
    Footer
  }
})
export default class Layout extends Vue {
  
  render() {
    
    return (
      <div class="wrapper">
    
        {/*top navbar*/}
        <Header/>
    
        <Sidebar/>
    
        <Offsidebar/>
    
        {/*Main section*/}
        <section className="section-container">
          {/*Page content*/}
          <router-view/>
        </section>
    
        <Footer/>
  
      </div>
    );
  }
}
