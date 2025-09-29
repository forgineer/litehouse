// For capturing query text and copying to the clipboard
function copy_to_clipboard(Id) {
    // Get the text field
    var copyText = document.getElementById(Id);

    // Select the text field
    // This is an easy way to show the user that something happened
    // I thought about using a popover, but that would require more JS to initialize, no thanks!
    copyText.select();

    // Copy the text inside the text field
    navigator.clipboard.writeText(copyText.value);
}