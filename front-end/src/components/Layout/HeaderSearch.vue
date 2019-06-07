<template>
  <!-- START Search form-->
  <form class="navbar-form" role="search" action="search.html">
    <div class="form-group">
      <input class="form-control" type="text" placeholder="Type and hit enter ..." />
      <div class="fas fa-times navbar-form-close" data-search-dismiss=""></div>
    </div>
    <button class="d-none" type="submit">Submit</button>
  </form>
  <!-- END Search form-->
</template>

<script>
import $ from '../Common/wrapper.js';

export default {
  name: 'HeaderSearch',
  mounted() {
    // NAVBAR SEARCH
    // -----------------------------------
    var navSearch = new navbarSearchInput();

    // Open search input
    var $searchOpen = $('[data-search-open]');

    $searchOpen
      .on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
      })
      .on('click', navSearch.toggle);

    // Close search input
    var $searchDismiss = $('[data-search-dismiss]');
    var inputSelector = '.navbar-form input[type="text"]';

    $(inputSelector)
      .on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
      })
      .on('keyup', function(e) {
        if (e.keyCode === 27)
          // ESC
          navSearch.dismiss();
      });

    // click anywhere closes the search
    $(document).on('click', navSearch.dismiss);
    // dismissable options
    $searchDismiss
      .on('click', function(e) {
        e.stopPropagation();
      })
      .on('click', navSearch.dismiss);

    function navbarSearchInput() {
      var navbarFormSelector = 'form.navbar-form';
      return {
        toggle: function() {
          var navbarForm = $(navbarFormSelector);

          navbarForm.toggleClass('open');

          var isOpen = navbarForm.hasClass('open');

          navbarForm.find('input')[isOpen ? 'focus' : 'blur']();
        },

        dismiss: function() {
          $(navbarFormSelector)
            .removeClass('open') // Close control
            .find('input[type="text"]')
            .blur(); // remove focus
          // .val('') // Empty input
        }
      };
    }
  }
};
</script>
