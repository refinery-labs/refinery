<template>
    <div class="wrapper">

        <!-- top navbar-->
        <HeaderHorizontal />

        <!-- offsidebar-->
        <Offsidebar />

        <!-- Main section-->
        <section class="section-container">
            <!-- Page content-->
            <router-view/>
        </section>

        <!-- Page footer-->
        <Footer />

    </div>
</template>

<script>
    import Vue from 'vue';
    import { mapMutations } from 'vuex'

    import HeaderHorizontal from './HeaderHorizontal'
    import Offsidebar from './Offsidebar'
    import Footer from './Footer'
    import ContentWrapper from './ContentWrapper'

    Vue.component('ContentWrapper', ContentWrapper)

    export default {
        name: 'Layout',
        components: {
            HeaderHorizontal,
            Offsidebar,
            Footer
        },
        created() {
            this.changeSetting({name: 'horizontal', value: true})
        },
        destroyed() {
            this.changeSetting({name: 'horizontal', value: false})
        },
        methods: {
            ...mapMutations([
                'changeSetting'
            ])
        }
    }
</script>