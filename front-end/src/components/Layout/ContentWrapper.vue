<template>
    <div class="content-wrapper">
        <div class="unwrap" v-if="unwrap">
            <slot></slot>
        </div>
        <slot v-else></slot>
    </div>
</template>

<script>
    export default {
        name: 'ContentWrapper',
        props: {
            unwrap: Boolean
        }
    }
</script>