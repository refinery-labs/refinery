import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {Prop, Watch} from 'vue-property-decorator';

const WHIRL_CLASS = 'whirl';

@Component
export default class CardToolTsx extends Vue {
  @Prop() refresh!: Boolean;
  @Prop() dismiss!: Boolean;
  @Prop() forceSpin!: Boolean;
  @Prop() onRemove!: Function;
  @Prop() onRemoved!: Function;
  @Prop() onRefresh!: Function;
  @Prop({default: 'standard'}) spinner!: string;
  
  @Watch('forceSpin', {immediate: true})
  public forceSpinWatcher(val: Boolean, oldVal: Boolean) {
    // Skip if these conditions are met
    if (val === oldVal || !this.$refs.cardRef) {
      return;
    }
    
    if (this.refresh) {
      this.handleRefresh();
    }
    
    if (this.dismiss) {
      this.handleDismiss();
    }
  }
  
  public mounted() {
    // Skip if we aren't actually mounted for some reason
    if (!this.$refs.cardRef) {
      return;
    }
    
    this.forceSpinWatcher(this.forceSpin, false);
  }
  
  getCardParent(item: HTMLElement) {
    if (!item) {
      return null;
    }
    
    let el = item.parentElement;
    while (el && !el.classList.contains('card'))
      el = el.parentElement;
    return el
  }
  
  checkForDirtyState(card: HTMLElement) {
    return card.classList.contains(WHIRL_CLASS);
  }
  
  getExtraClasses() {
    return this.spinner.split(' ');
  }
  
  addWhirlClass(card: HTMLElement) {
    if (!this.checkForDirtyState(card)) {
      card.classList.add(WHIRL_CLASS);
      this.getExtraClasses().forEach((s) => card.classList.add(s));
    }
  }
  
  removeWhirlClass(card: HTMLElement) {
    if (this.checkForDirtyState(card)) {
      card.classList.remove(WHIRL_CLASS);
      this.getExtraClasses().forEach((s) => card.classList.remove(s));
    }
  }
  
  handleDismiss() {
    // find the first parent card
    const card = this.getCardParent(this.$refs.cardRef as HTMLElement);
    
    if (!card) {
      return;
    }
  
    // Remove the state if we are in a dirty state
    if (!this.forceSpin && this.checkForDirtyState(card)) {
      this.removeWhirlClass(card);
      return;
    }
    
    const destroyCard = () => {
      if (!card || !card.parentNode) {
        return;
      }
      
      // remove card
      card.parentNode.removeChild(card);
      if (this.onRemoved) {
        // An event to catch when the card has been removed from DOM
        this.onRemoved();
      }
    };
    
    const animate = (item: HTMLElement, cb: Function) => {
      if ('onanimationend' in window) { // animation supported
        item.addEventListener('animationend', cb.bind(this));
        item.className += ' animated bounceOut'; // requires animate.css
        return;
      }
      
      cb.call(this) // no animation, just remove
    };
    
    const confirmRemove = () => {
      animate(card, function() {
        destroyCard();
      })
    };
  
    if (this.onRemove) {
      // Trigger the event and finally remove the element
      this.onRemove(card, confirmRemove);
    }
    
  }
  
  handleRefresh() {
    const card = this.getCardParent(this.$refs.cardRef as HTMLElement);
    
    if (!card) {
      return;
    }
    
    // Remove the state if we are in a dirty state
    if (!this.forceSpin && this.checkForDirtyState(card)) {
      this.removeWhirlClass(card);
      return;
    }
    // start showing the spinner
    this.addWhirlClass(card);
    
    if (this.onRefresh) {
      // event to remove spinner when refresh is done
      this.onRefresh(card, this.removeWhirlClass);
    }
  }
  
  public renderRefresh() {
    if (!this.refresh || !this.onRefresh) {
      return null;
    }
    
    return (
      <em on={{click: this.handleRefresh}} class="fas fa-sync" />
    );
  }
  
  public renderDismiss() {
    if (!this.dismiss) {
      return;
    }
    
    return (
      <em on={{click: this.handleDismiss}} class="fa fa-times" />
    );
  }
  
  public render(h: CreateElement): VNode {
    
    return (
      <div ref="cardRef" class="card-tool float-right">
        {this.renderRefresh()}
        {this.renderDismiss()}
      </div>
    );
  }
}