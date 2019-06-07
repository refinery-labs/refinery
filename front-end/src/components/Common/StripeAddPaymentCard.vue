<template>
  <div ref="card"></div>
</template>

<script lang="ts">
  import Vue from 'vue';
  import {mapMutations, mapState} from "vuex";
  import {UserMutators} from "@/constants/store-constants";

  // @ts-ignore
  let stripe = Stripe(`${process.env.VUE_APP_STRIPE_PUBLISHABLE_KEY}`),
      elements = stripe.elements(),
      card: any = undefined;

  export default Vue.extend({
    name: "StripeAddPaymentCard",
    created: function () {
      card = elements.create('card');
      card.addEventListener('change', async (event: any) => {
        // "complete" is true when the user has finished entering
        // their card information into the Stripe element.
        if (event.complete) {
          const {token, error} = await stripe.createToken(
              card,
              {
                "name": this.registrationNameInput,
              }
          );

          if (error) {
            console.error("An error occurred while generating Stripe token!:");
            console.error(error);
          }

          this.setRegistrationStripeTokenValue(token.id);
        }
      });
    },
    mounted: function () {
      card.mount(this.$refs.card);
    },
    beforeDestroy: () => {
      card.unmount();
    },
    methods: {
      ...mapMutations('user', [
        UserMutators.setRegistrationStripeTokenValue,
      ]),
    },
    computed: mapState('user', [
      'registrationNameInput'
    ])
  });
</script>

<style scoped>

</style>