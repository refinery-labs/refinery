import Vue from 'vue';
import { Component } from 'vue-property-decorator';

@Component
export default class Footer extends Vue {
  render() {
    return (
      <footer class="footer-container">
        <span>&copy; 2020 - Refinery Labs, Inc</span>
      </footer>
    );
  }
}
