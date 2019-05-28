import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';

@Component
export default class PageNotFound extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="page-not-found-page">
        <h2>Page Not Found, sorry about that!</h2>
        <router-view />
      </div>
    );
  }
}
