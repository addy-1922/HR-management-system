document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss flash messages after 5 seconds.
    window.setTimeout(function () {
        document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
            var instance = bootstrap.Alert.getOrCreateInstance(alert);
            if (instance) {
                instance.close();
            }
        });
    }, 5000);
});
