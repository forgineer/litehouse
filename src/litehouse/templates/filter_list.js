// For Entity and Entity Fields Search Filter
function filter_list() {
    var input, filter, ul, li, a, i, txtValue;
    input = document.getElementById('list_search');
    filter = input.value.toUpperCase();
    ul = document.getElementById("list_items");
    li = ul.getElementsByTagName('li');

    // Loop through all list items, and hide those who don't match the search query
    for (i = 0; i < li.length; i++) {
        a = li[i].getElementsByTagName("span")[0];
        txtValue = a.textContent || a.innerText;

        if (txtValue.toUpperCase().indexOf(filter) > -1) {
            li[i].style.display = "";
        } else {
            li[i].style.display = "none";
        }
    }
}