import Vue from 'vue';
import {Component} from 'vue-property-decorator';

@Component
export default class Footer extends Vue {
  render() {
    return (
      <footer class="footer-container">
        <span>&copy; 2019 - Refinery Labs, Inc</span>
      </footer>
    );
  }
}
