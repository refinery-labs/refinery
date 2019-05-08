<template>
    <div v-bind="$props">
        {{currentTime}}
    </div>
</template>

<script>

    import moment from 'moment';

    /**
     * Updates every second the content of the element
     * with the current time formated
     */
    export default {
        name: 'Now',
        props: {
            /** string to format current date */
            format: String
        },
        data() {
            return {
                currentTime: null,
                interval: ''
            }
        },
        mounted() {
            this.updateTime();
            this.interval = setInterval(this.updateTime, 1000);
        },
        destroyed() {
            if(this.interval)
                clearInterval(this.interval);
        },
        methods: {
            updateTime: function(){
                this.currentTime = moment(new Date()).format(this.format)
            }
        }

    }
</script>

<style scoped>
    div { display: inline-block; }
</style>
