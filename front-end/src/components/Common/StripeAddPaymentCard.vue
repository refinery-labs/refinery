<template>
  <div ref="card"></div>
</template>

<script lang="ts">
/// <reference types="stripe-v3" />
import Vue from 'vue';
import { mapMutations, mapState } from 'vuex';
import { UserMutators } from '@/constants/store-constants';
import {addStripeTagToPage} from '@/lib/stripe-utils';

export default Vue.extend({

  name: 'StripeAddPaymentCard',

  async mounted() {
    await addStripeTagToPage();

    const stripe: stripe.Stripe = Stripe(`${process.env.VUE_APP_STRIPE_PUBLISHABLE_KEY}`);
    const elements = stripe.elements();
    const card = elements.create('card');

    card.on('change', async (event: any) => {
      // "complete" is true when the user has finished entering
      // their card information into the Stripe element.
      if (event.complete) {
        const { token, error } = await stripe.createToken(card, {
          name: this.registrationNameInput
        });

        if (error || !token) {
          console.error('An error occurred while generating Stripe token!:');
          console.error(error);
          return;
        }

        this.setRegistrationStripeTokenValue(token.id);
      }
    });

    this.card = card;

    card.mount(this.$refs.card);
  },
  beforeDestroy() {
    this.card && this.card.unmount();
  },
  methods: {
    ...mapMutations('user', [UserMutators.setRegistrationStripeTokenValue])
  },
  computed: mapState('user', ['registrationNameInput'])
});
</script>

<style scoped></style>
