// Anonymous function to execute as part of a successful HTMX Swap response to close any open modal.
(function() {
    const modal = bootstrap.Modal.getInstance(document.querySelector('.modal.show'));
    if (modal) {
        modal.hide();

        // Hide any residual modal backdrops
        document.querySelectorAll('.modal-backdrop').forEach(function(backdrop) {
            backdrop.remove();
        });
    }
})();