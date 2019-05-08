<template>
    <div class="wrapper">

        <!-- top navbar-->
        <Header />

        <!-- sidebar-->
        <Sidebar />

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
    import Header from './Header'
    import Sidebar from './Sidebar'
    import Offsidebar from './Offsidebar'
    import Footer from './Footer'
    import ContentWrapper from './ContentWrapper'

    Vue.component('ContentWrapper', ContentWrapper);

    export default {
        name: 'Layout',
        components: {
            Header,
            Sidebar,
            Offsidebar,
            Footer
        }
    }
</script>