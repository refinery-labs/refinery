<template>
  <div ref="cardRef" class="card-tool float-right">
    <em v-if="refresh" @click="handleRefresh" class="fas fa-sync"></em>
    <em v-if="dismiss" @click="handleDismiss" class="fa fa-times"></em>
  </div>
</template>

<script>
import Vue from 'vue';
// Card Tools
// -----------------------------------

/**
 * Helper function to find the closest
 * ascending .card element
 */
function getCardParent(item) {
  var el = item.parentElement;
  while (el && !el.classList.contains('card')) el = el.parentElement;
  return el;
}

/**
 * Add action icons to card components to allow
 * refresh data or remove a card element
 */
export default Vue.extend({
  name: 'CardTool',
  props: {
    /** show the refreshe icon */
    refresh: Boolean,
    /** show the remove icon */
    dismiss: Boolean,
    /** triggers before card is removed */
    onRemove: {
      type: Function,
      default: () => {}
    },
    /** triggers after card was removed */
    onRemoved: {
      type: Function,
      default: () => {}
    },
    /** triggers when user click on refresh button */
    onRefresh: {
      type: Function,
      default: () => {}
    },
    /** name if the icon class to use as spinner */
    spinner: {
      type: String,
      default: 'standard'
    },
    forceSpin: Boolean
  },

  methods: {
    handleDismiss(e) {
      // find the first parent card
      const card = getCardParent(this.$refs.cardRef);

      const destroyCard = () => {
        // remove card
        card.parentNode.removeChild(card);
        // An event to catch when the card has been removed from DOM
        this.onRemoved();
      };

      const animate = function(item, cb) {
        if ('onanimationend' in window) {
          // animation supported
          item.addEventListener('animationend', cb.bind(this));
          item.class += ' animated bounceOut'; // requires animate.css
        } else cb.call(this); // no animation, just remove
      };

      const confirmRemove = function() {
        animate(card, function() {
          destroyCard();
        });
      };

      // Trigger the event and finally remove the element
      this.onRemove(card, confirmRemove);
    },
    handleRefresh(e) {
      const WHIRL_CLASS = 'whirl';
      const card = getCardParent(this.$refs.cardRef);

      function showSpinner(card, spinner) {
        card.classList.add(WHIRL_CLASS);
        spinner.forEach(function(s) {
          card.classList.add(s);
        });
      }

      // method to clear the spinner when done
      const done = () => {
        card.classList.remove(WHIRL_CLASS);
      };
      // start showing the spinner
      showSpinner(card, this.spinner.split(' '));
      // event to remove spinner when refres is done
      this.onRefresh(card, done);
    }
  }
});
</script>
