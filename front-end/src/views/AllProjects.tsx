import Vue, { CreateElement, VNode } from "vue";
import Component from "vue-class-component";
import { namespace } from "vuex-class";
import { SearchSavedProjectsResult } from "@/types/api-types";
import Search from "@/components/AllProjects/Search";

const allProjects = namespace("allProjects");

@Component({
  components: { Search }
})
export default class AllProjects extends Vue {
  @allProjects.State availableProjects!: SearchSavedProjectsResult[];

  public render(h: CreateElement): VNode {
    if (!this.availableProjects) {
      return <h2>Please create a new project!</h2>;
    }

    return (
      <div class="all-projects-page text-align--left">
        <Search />
      </div>
    );
  }
}
