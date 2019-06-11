<template>
  <div>
    <div class="content-heading display-flex billing-main-container">
      <div class="layout--constrain flex-grow--1">
        <div class="text-align--center">
          <!-- Main card-->
          <div class="card b">
            <div class="card-header">
              <h2 class="my-2">
                <span>Billing Information</span>
              </h2>
            </div>
            <div class="card-body text-align--left">
              <div class="col-xl-6">
                <div class="card card-default" v-bind:class="{ 'whirl standard': isLoading }">
                  <div class="card-header">
                    Payment Methods
                    <div class="card-tool float-right" v-on:click="getCards"><em class="fas fa-sync"></em></div>
                  </div>
                  <div class="table-responsive">
                    <table class="table table-striped table-bordered table-hover">
                      <tbody>
                      <tr v-for="paymentMethod in paymentMethods">
                        <td>
                          <div class="media align-items-center">
                            <div class="media-body d-flex">
                              <div class="media-body d-flex ml-auto">
                                <h4 class="m-0 p-2">
                                  <em v-if="paymentMethod.brand.toLowerCase() === 'mastercard'"
                                      class="fab fa-cc-mastercard"></em>
                                  <em v-if="paymentMethod.brand.toLowerCase() === 'amex'" class="fab fa-cc-amex"></em>
                                  <em v-if="paymentMethod.brand.toLowerCase() === 'diners'"
                                      class="fab fa-cc-diners-club"></em>
                                  <em v-if="paymentMethod.brand.toLowerCase() === 'discover'"
                                      class="fab fa-cc-discover"></em>
                                  <em v-if="paymentMethod.brand.toLowerCase() === 'jcb'" class="fab fa-cc-jcb"></em>
                                  <em v-if="paymentMethod.brand.toLowerCase() === 'unionpay'"
                                      class="fab fa-credit-card"></em>
                                  <em v-if="paymentMethod.brand.toLowerCase() === 'visa'" class="fab fa-cc-visa"></em>
                                  <em v-if="paymentMethod.brand.toLowerCase() === 'unknown'"
                                      class="fab fa-credit-card"></em>
                                  •••• •••• •••• {{paymentMethod.last4}} <i>{{paymentMethod.exp_month.toString()}}/{{paymentMethod.exp_year.toString()}}</i>
                                  <div class="px-2 mr-2 float-left badge badge-success" v-if="paymentMethod.is_primary">
                                    Primary
                                  </div>
                                  <div class="px-2 mr-2 float-left badge badge-secondary"
                                       v-if="!paymentMethod.is_primary">Secondary
                                  </div>
                                </h4>
                              </div>
                              <div class="billing-buttons-column align-items-right">
                                <button v-if="!paymentMethod.is_primary" type="button"
                                        class="btn btn-primary billing-button"
                                        v-on:click="makePrimaryCard(paymentMethod)">
                                  <span class="fas fa-check-circle"></span> Make Primary
                                </button>
                                <button v-if="!paymentMethod.is_primary" type="button"
                                        class="btn btn-danger billing-button" v-on:click="deleteCard(paymentMethod)">
                                  <span class="fas fa-trash"></span>
                                </button>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                      </tbody>
                    </table>
                  </div>
                  <div class="card-footer">
                    <label class="text-muted d-block" htmlFor="user-name-input">
                      Add New Payment Method
                    </label>
                    <StripeAddPaymentCard v-bind:setRegistrationStripeTokenValue="setStripeToken"/>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


<script lang="ts">
  import {Component, Vue} from 'vue-property-decorator';
  import {namespace} from "vuex-class";
  import {PaymentCardResult} from "@/types/api-types";
  import StripeAddPaymentCard from '@/components/Common/StripeAddPaymentCard.vue';

  const billing = namespace('billing');

  @Component({
    components: {
      StripeAddPaymentCard
    }
  })
  export default class Billing extends Vue {
    @billing.Action getPaymentMethods!: () => void;
    @billing.Action deletePaymentMethod!: (paymentMethodId: string) => void;
    @billing.Action makePrimaryPaymentMethod!: (paymentMethodId: string) => void;
    @billing.Action addPaymentMethod!: (paymentMethodId: string) => void;

    @billing.State paymentMethods!: () => PaymentCardResult[];
    @billing.State isLoading!: () => Boolean;

    async setStripeToken(paymentTokenId: string) {
      // Add this card to our payment methods
      await this.addPaymentMethod(paymentTokenId);

      // Update the payment methods
      await this.getPaymentMethods();
    }

    async makePrimaryCard(paymentMethod: PaymentCardResult) {
      // Make this our primary payment method
      await this.makePrimaryPaymentMethod(paymentMethod.id);

      // Update the payment methods
      await this.getPaymentMethods();
    }

    async deleteCard(paymentMethod: PaymentCardResult) {
      // Delete the card
      await this.deletePaymentMethod(paymentMethod.id);

      // Update the payment methods now that the card is deleted.
      await this.getPaymentMethods();
    }

    async getCards() {
      await this.getPaymentMethods();
    }

    async mounted() {
      this.getPaymentMethods();
    }
  }
</script>